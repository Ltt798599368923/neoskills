"""Skill composition and decomposition.

Compose: Combine multiple skills into a pipeline/ensemble/selector.
Decompose: Split a monolithic skill into focused sub-skills.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from neoskills.ontology.models import (
    CompositionMode,
    CompositionSpec,
    EdgeType,
    LifecycleState,
    OntologyEdge,
    SkillNode,
    SkillSubstrate,
    SkillType,
)
from neoskills.ontology.graph import SkillGraph

logger = logging.getLogger(__name__)


class CompositionError(Exception):
    """Raised for composition/decomposition errors."""


def compose(
    graph: SkillGraph,
    skill_ids: list[str],
    mode: str = "pipeline",
    name: str = "",
    description: str = "",
    output_dir: Path | None = None,
) -> SkillNode:
    """Create a composite skill from component skills.

    Args:
        graph: The skill graph.
        skill_ids: IDs of skills to compose.
        mode: Composition mode (pipeline, ensemble, selector).
        name: Name for the composite skill. Auto-generated if empty.
        description: Description. Auto-generated if empty.
        output_dir: Where to create the new skill directory.

    Returns:
        The new composite SkillNode (not yet persisted to disk).
    """
    if len(skill_ids) < 2:
        raise CompositionError("Need at least 2 skills to compose")

    # Validate all skills exist
    nodes: list[SkillNode] = []
    for sid in skill_ids:
        node = graph.get_node(sid)
        if node is None:
            raise CompositionError(f"Skill not found: {sid}")
        nodes.append(node)

    # Check for conflicts
    for i, n1 in enumerate(nodes):
        for n2 in nodes[i + 1 :]:
            conflicts = graph.get_edges(
                source=n1.qualified_id,
                target=n2.qualified_id,
                edge_type=EdgeType.CONFLICTS_WITH,
            )
            if conflicts:
                raise CompositionError(
                    f"Cannot compose: {n1.skill_id} conflicts with {n2.skill_id}"
                )

    # Resolve mode
    try:
        comp_mode = CompositionMode(mode)
    except ValueError:
        raise CompositionError(
            f"Unknown composition mode: '{mode}'. Use: pipeline, ensemble, selector"
        )

    # Generate name/description
    if not name:
        name = "-".join(sid.split("/")[-1] for sid in skill_ids[:3])
        if len(skill_ids) > 3:
            name += f"-plus-{len(skill_ids) - 3}"
        name += f"-{comp_mode.value}"

    if not description:
        component_names = [n.name or n.skill_id for n in nodes]
        description = (
            f"Composite {comp_mode.value} of: {', '.join(component_names)}"
        )

    # Build stages
    stages: list[dict[str, Any]] = []
    for i, node in enumerate(nodes):
        stage: dict[str, Any] = {
            "skill_id": node.skill_id,
            "order": i,
        }
        # Wire inputs/outputs for pipeline mode
        if comp_mode == CompositionMode.PIPELINE and i > 0:
            stage["inputs_from"] = f"stage_{i - 1}"
        stages.append(stage)

    # Merge domains and tags from components
    all_domains: list[str] = []
    all_tags: list[str] = []
    for n in nodes:
        all_domains.extend(n.domain)
        all_tags.extend(n.tags)
    domains = sorted(set(all_domains))
    tags = sorted(set(all_tags + [f"composite:{comp_mode.value}"]))

    # Create the composite node
    composite = SkillNode(
        skill_id=name,
        name=name,
        description=description,
        type=SkillType.COMPOSITE,
        domain=domains,
        substrate=SkillSubstrate.COMPOSITE,
        tags=tags,
        lifecycle_state=LifecycleState.CANDIDATE,
        version="0.1.0",
        composition=CompositionSpec(
            mode=comp_mode,
            stages=stages,
        ),
        path=output_dir / name if output_dir else None,
    )

    return composite


def compose_edges(composite_id: str, component_ids: list[str]) -> list[OntologyEdge]:
    """Generate the edges for a composition.

    The composite skill COMPOSES_WITH each component, and
    REQUIRES all components.
    """
    edges: list[OntologyEdge] = []
    for cid in component_ids:
        edges.append(
            OntologyEdge(
                source=composite_id,
                target=cid,
                edge_type=EdgeType.COMPOSES_WITH,
            )
        )
        edges.append(
            OntologyEdge(
                source=composite_id,
                target=cid,
                edge_type=EdgeType.REQUIRES,
            )
        )
    return edges


def decompose_plan(
    graph: SkillGraph,
    skill_id: str,
    sub_skill_names: list[str],
) -> dict[str, Any]:
    """Create a decomposition plan for a monolithic skill.

    Returns a plan dict describing:
    - The sub-skills to create
    - DERIVED_FROM edges from each to the parent
    - Optional composite wrapper
    - Deprecation of the parent

    The caller is responsible for executing the plan
    (creating directories, writing files, etc.).
    """
    node = graph.get_node(skill_id)
    if node is None:
        raise CompositionError(f"Skill not found: {skill_id}")

    if len(sub_skill_names) < 2:
        raise CompositionError("Need at least 2 sub-skill names to decompose")

    plan: dict[str, Any] = {
        "parent_skill": skill_id,
        "sub_skills": [],
        "edges": [],
        "deprecate_parent": True,
        "create_wrapper": True,
        "wrapper_name": f"{skill_id}-composed",
    }

    for sub_name in sub_skill_names:
        plan["sub_skills"].append({
            "skill_id": sub_name,
            "derived_from": skill_id,
            "domain": node.domain,
            "tags": node.tags,
            "lifecycle_state": "candidate",
        })
        plan["edges"].append({
            "source": sub_name,
            "target": skill_id,
            "edge_type": "derived_from",
        })

    return plan
