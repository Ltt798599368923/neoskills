"""Filesystem → SkillGraph loader.

Walks skill directories across all source trees (taps, local agent skills,
installed plugins, remote plugins), parses SKILL.md + ontology.yaml, and
builds the in-memory property graph.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from neoskills.ontology.models import (
    CapabilityManifest,
    CompositionMode,
    CompositionSpec,
    EdgeType,
    EnrichmentLevel,
    LifecycleEvent,
    LifecycleState,
    OntologyEdge,
    SkillNode,
    SkillSubstrate,
    SkillType,
)
from neoskills.ontology.graph import SkillGraph
from neoskills.ontology.taxonomy import (
    build_domain_nodes,
    infer_domain_from_namespace,
    infer_domain_from_skill_id,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Source tree definitions
# ──────────────────────────────────────────────


def default_source_trees() -> list[dict[str, Any]]:
    """Return the standard source trees to scan.

    Each entry specifies a root path, a glob pattern to find skill
    directories (containing SKILL.md), and a namespace function.
    """
    home = Path.home()
    return [
        {
            "root": home / ".neoskills" / "taps",
            "pattern": "*/skills/*",
            "namespace": "",
            "source_type": "tap",
        },
        {
            "root": home / ".claude" / "skills",
            "pattern": "*",
            "namespace": "",
            "source_type": "local",
        },
    ]


def discover_plugin_trees(
    local_plugins_root: Path | None = None,
    remote_plugins_root: Path | None = None,
) -> list[dict[str, Any]]:
    """Discover plugin source trees dynamically."""
    trees: list[dict[str, Any]] = []

    # Local plugins (e.g., .local-plugins/cache/knowledge-work-plugins/finance/1.0.0/skills/*)
    if local_plugins_root and local_plugins_root.exists():
        for marketplace_dir in local_plugins_root.iterdir():
            if not marketplace_dir.is_dir():
                continue
            for domain_dir in marketplace_dir.iterdir():
                if not domain_dir.is_dir():
                    continue
                # Find version dirs
                for version_dir in domain_dir.iterdir():
                    if not version_dir.is_dir():
                        continue
                    skills_dir = version_dir / "skills"
                    if skills_dir.exists():
                        trees.append(
                            {
                                "root": skills_dir,
                                "pattern": "*",
                                "namespace": f"plugin/{domain_dir.name}",
                                "source_type": "plugin",
                            }
                        )

    # Remote plugins
    if remote_plugins_root and remote_plugins_root.exists():
        for plugin_dir in remote_plugins_root.iterdir():
            if not plugin_dir.is_dir():
                continue
            skills_dir = plugin_dir / "skills"
            if skills_dir.exists():
                trees.append(
                    {
                        "root": skills_dir,
                        "pattern": "*",
                        "namespace": f"remote/{plugin_dir.name}",
                        "source_type": "remote",
                    }
                )

    return trees


# ──────────────────────────────────────────────
# SKILL.md parsing (reuse existing frontmatter parser)
# ──────────────────────────────────────────────


def _parse_skill_md(skill_dir: Path) -> dict[str, Any]:
    """Parse SKILL.md frontmatter from a skill directory."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return {}

    content = skill_md.read_text(encoding="utf-8", errors="replace")

    # Simple frontmatter parser (--- delimited YAML)
    if not content.startswith("---"):
        return {"name": skill_dir.name, "description": content[:200].strip()}

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {"name": skill_dir.name}

    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        fm = {}

    if "name" not in fm:
        fm["name"] = skill_dir.name

    return fm


# ──────────────────────────────────────────────
# ontology.yaml parsing
# ──────────────────────────────────────────────


def _parse_ontology_yaml(skill_dir: Path) -> dict[str, Any] | None:
    """Parse ontology.yaml sidecar if present."""
    ontology_file = skill_dir / "ontology.yaml"
    if not ontology_file.exists():
        return None

    try:
        data = yaml.safe_load(ontology_file.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (yaml.YAMLError, OSError) as e:
        logger.warning(f"Failed to parse {ontology_file}: {e}")
        return None


# ──────────────────────────────────────────────
# Node construction
# ──────────────────────────────────────────────


def _build_node(
    skill_dir: Path,
    frontmatter: dict[str, Any],
    ontology: dict[str, Any] | None,
    namespace: str,
    source_type: str,
) -> SkillNode:
    """Build a SkillNode from parsed frontmatter + ontology data."""

    skill_id = skill_dir.name
    has_scripts = (skill_dir / "scripts").is_dir()
    has_ontology = ontology is not None

    # Determine enrichment level
    if has_ontology:
        edges = ontology.get("edges", {})
        lifecycle = ontology.get("lifecycle", {})
        has_edges = any(v for v in edges.values() if v)
        has_lifecycle = bool(lifecycle.get("state"))
        if has_lifecycle and has_edges:
            level = EnrichmentLevel.L3_GOVERNED
        elif has_edges:
            level = EnrichmentLevel.L2_CONNECTED
        else:
            level = EnrichmentLevel.L1_TAGGED
    else:
        level = EnrichmentLevel.L0_BARE

    # Merge ontology data over frontmatter defaults
    o = ontology or {}

    # Resolve type
    raw_type = o.get("type", frontmatter.get("type", "task"))
    try:
        skill_type = SkillType(raw_type)
    except ValueError:
        skill_type = SkillType.TASK

    # Resolve substrate
    raw_substrate = o.get("substrate", "")
    if raw_substrate:
        try:
            substrate = SkillSubstrate(raw_substrate)
        except ValueError:
            substrate = SkillSubstrate.COMPOSITE if has_scripts else SkillSubstrate.PURE_PROMPT
    else:
        substrate = SkillSubstrate.COMPOSITE if has_scripts else SkillSubstrate.PURE_PROMPT

    # Resolve domain
    domain = o.get("domain", [])
    if not domain:
        # Try inference
        ns_domain = infer_domain_from_namespace(namespace)
        if ns_domain:
            domain = ns_domain
        else:
            domain = infer_domain_from_skill_id(skill_id)

    # Resolve lifecycle
    lc = o.get("lifecycle", {})
    try:
        lc_state = LifecycleState(lc.get("state", "candidate"))
    except ValueError:
        lc_state = LifecycleState.CANDIDATE

    history = [
        LifecycleEvent(
            from_state=ev.get("from", ""),
            to_state=ev.get("to", ""),
            timestamp=str(ev.get("at", ev.get("timestamp", ""))),
            reason=ev.get("reason", ""),
        )
        for ev in lc.get("history", [])
    ]

    # Resolve capability
    cap_data = o.get("capability", {})
    capability = CapabilityManifest(
        inputs=cap_data.get("inputs", []),
        outputs=cap_data.get("outputs", []),
        tools_required=cap_data.get("tools_required", frontmatter.get("tools", [])),
        pre_flight=cap_data.get("pre_flight", []),
        model_preference=cap_data.get("model_preference", frontmatter.get("model", "")),
    )

    # Resolve composition
    comp_data = o.get("composition")
    composition = None
    if comp_data:
        try:
            mode = CompositionMode(comp_data.get("mode", "pipeline"))
        except ValueError:
            mode = CompositionMode.PIPELINE
        composition = CompositionSpec(
            mode=mode,
            stages=comp_data.get("stages", []),
            fallback=comp_data.get("fallback"),
        )

    # Tags: merge frontmatter + ontology
    fm_tags = frontmatter.get("tags", [])
    o_tags = o.get("tags", [])
    all_tags = sorted(set(fm_tags + o_tags))

    return SkillNode(
        skill_id=skill_id,
        name=frontmatter.get("name", skill_id),
        description=frontmatter.get("description", ""),
        namespace=namespace,
        path=skill_dir,
        type=skill_type,
        domain=domain if isinstance(domain, list) else [domain],
        layer=o.get("layer", ""),
        substrate=substrate,
        tags=all_tags,
        lifecycle_state=lc_state,
        maturity=lc.get("maturity", "created"),
        confidence=float(lc.get("confidence", 0.0)),
        lifecycle_history=history,
        version=o.get("version", frontmatter.get("version", "0.1.0")),
        lineage=o.get("lineage", []),
        capability=capability,
        composition=composition,
        instance_params=o.get("instance_params", {}),
        source_type=source_type,
        source_location=str(skill_dir),
        tap=frontmatter.get("source", frontmatter.get("tap", "")),
        enrichment_level=level,
        schema_version=o.get("schema_version", "1.0"),
    )


def _extract_edges(skill_id: str, ontology: dict[str, Any] | None) -> list[OntologyEdge]:
    """Extract edges from ontology.yaml edges block."""
    if not ontology:
        return []

    edges_block = ontology.get("edges", {})
    result: list[OntologyEdge] = []

    edge_type_map = {
        "requires": EdgeType.REQUIRES,
        "extends": EdgeType.EXTENDS,
        "composes_with": EdgeType.COMPOSES_WITH,
        "conflicts_with": EdgeType.CONFLICTS_WITH,
        "supersedes": EdgeType.SUPERSEDES,
        "derived_from": EdgeType.DERIVED_FROM,
    }

    for key, targets in edges_block.items():
        et = edge_type_map.get(key)
        if et is None:
            continue
        if not isinstance(targets, list):
            targets = [targets]
        for target in targets:
            if target:
                result.append(OntologyEdge(source=skill_id, target=target, edge_type=et))

    return result


# ──────────────────────────────────────────────
# Main loader
# ──────────────────────────────────────────────


class OntologyLoader:
    """Loads the skill ontology graph from the filesystem."""

    def __init__(
        self,
        extra_source_trees: list[dict[str, Any]] | None = None,
        local_plugins_root: Path | None = None,
        remote_plugins_root: Path | None = None,
        skip_defaults: bool = False,
    ) -> None:
        self.source_trees = [] if skip_defaults else default_source_trees()
        if local_plugins_root or remote_plugins_root:
            self.source_trees.extend(discover_plugin_trees(local_plugins_root, remote_plugins_root))
        if extra_source_trees:
            self.source_trees.extend(extra_source_trees)

    def load(self) -> SkillGraph:
        """Walk all source trees and build the graph."""
        graph = SkillGraph()

        # Load domain taxonomy
        for domain_node in build_domain_nodes().values():
            graph.add_domain(domain_node)

        # Walk source trees
        seen_ids: set[str] = set()
        for tree in self.source_trees:
            root = Path(tree["root"])
            if not root.exists():
                logger.debug(f"Source tree not found: {root}")
                continue

            pattern = tree["pattern"]
            namespace = tree["namespace"]
            source_type = tree["source_type"]

            for skill_dir in sorted(root.glob(pattern)):
                if not skill_dir.is_dir():
                    continue
                if not (skill_dir / "SKILL.md").exists():
                    continue

                # Build qualified ID for dedup
                qid = f"{namespace}/{skill_dir.name}" if namespace else skill_dir.name
                if qid in seen_ids:
                    logger.debug(f"Skipping duplicate: {qid}")
                    continue
                seen_ids.add(qid)

                try:
                    fm = _parse_skill_md(skill_dir)
                    onto = _parse_ontology_yaml(skill_dir)
                    node = _build_node(skill_dir, fm, onto, namespace, source_type)
                    graph.add_node(node)

                    # Extract and add edges
                    for edge in _extract_edges(node.qualified_id, onto):
                        graph.add_edge(edge)

                    # Add domain edges
                    for d in node.domain:
                        graph.add_edge(
                            OntologyEdge(
                                source=node.qualified_id,
                                target=d,
                                edge_type=EdgeType.BELONGS_TO,
                            )
                        )

                except Exception as e:
                    logger.warning(f"Failed to load skill {skill_dir}: {e}")

        logger.info(
            f"Loaded {len(graph)} skills, {len(graph.edges)} edges, {len(graph.domains)} domains"
        )
        return graph
