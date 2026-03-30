"""SkillGraph → filesystem writer.

Persists ontology mutations back to ontology.yaml sidecar files.
This is the write-half of the file-system-as-database contract.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from neoskills.ontology.models import (
    EdgeType,
    OntologyEdge,
    SkillNode,
)

logger = logging.getLogger(__name__)


# Edge types that are stored in ontology.yaml edges block
_STORABLE_EDGE_TYPES = {
    EdgeType.REQUIRES: "requires",
    EdgeType.EXTENDS: "extends",
    EdgeType.COMPOSES_WITH: "composes_with",
    EdgeType.CONFLICTS_WITH: "conflicts_with",
    EdgeType.SUPERSEDES: "supersedes",
    EdgeType.DERIVED_FROM: "derived_from",
}


class OntologyWriter:
    """Writes ontology metadata back to skill directories."""

    def write_node(self, node: SkillNode, edges: list[OntologyEdge] | None = None) -> Path:
        """Write or update ontology.yaml for a skill node.

        If the file already exists, it is overwritten with the current
        node state. If edges are provided, they are included in the
        edges block.

        Returns the path to the written ontology.yaml.
        """
        if node.path is None:
            raise ValueError(f"Skill '{node.skill_id}' has no filesystem path")

        ontology_path = node.path / "ontology.yaml"
        data = self._node_to_dict(node, edges or [])

        ontology_path.write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

        logger.info(f"Wrote {ontology_path}")
        return ontology_path

    def add_edge_to_file(self, source_node: SkillNode, edge: OntologyEdge) -> None:
        """Add a single edge to an existing ontology.yaml.

        If ontology.yaml doesn't exist, creates a minimal one.
        """
        if source_node.path is None:
            raise ValueError(f"Skill '{source_node.skill_id}' has no filesystem path")

        ontology_path = source_node.path / "ontology.yaml"

        # Load existing or start fresh
        if ontology_path.exists():
            try:
                data = yaml.safe_load(ontology_path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError:
                data = {}
        else:
            data = {"schema_version": "1.0"}

        # Ensure edges block exists
        edges_block = data.setdefault("edges", {})
        yaml_key = _STORABLE_EDGE_TYPES.get(edge.edge_type)
        if yaml_key is None:
            logger.warning(f"Edge type {edge.edge_type} not storable in ontology.yaml")
            return

        targets = edges_block.setdefault(yaml_key, [])
        if edge.target not in targets:
            targets.append(edge.target)

        ontology_path.write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

        logger.info(f"Added edge {edge.source} --{yaml_key}--> {edge.target} to {ontology_path}")

    def remove_edge_from_file(self, source_node: SkillNode, edge: OntologyEdge) -> bool:
        """Remove a single edge from ontology.yaml. Returns True if found."""
        if source_node.path is None:
            return False

        ontology_path = source_node.path / "ontology.yaml"
        if not ontology_path.exists():
            return False

        try:
            data = yaml.safe_load(ontology_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            return False

        yaml_key = _STORABLE_EDGE_TYPES.get(edge.edge_type)
        if yaml_key is None:
            return False

        edges_block = data.get("edges", {})
        targets = edges_block.get(yaml_key, [])
        if edge.target in targets:
            targets.remove(edge.target)
            ontology_path.write_text(
                yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            return True
        return False

    def _node_to_dict(self, node: SkillNode, edges: list[OntologyEdge]) -> dict[str, Any]:
        """Serialize a SkillNode + its edges to the ontology.yaml format."""
        data: dict[str, Any] = {
            "schema_version": node.schema_version,
        }

        # Classification
        data["type"] = node.type.value
        if node.domain:
            data["domain"] = node.domain
        if node.layer:
            data["layer"] = node.layer
        if node.substrate.value != "pure-prompt":
            data["substrate"] = node.substrate.value

        # Lifecycle
        lc: dict[str, Any] = {
            "state": node.lifecycle_state.value,
            "maturity": node.maturity,
        }
        if node.confidence > 0:
            lc["confidence"] = node.confidence
        if node.lifecycle_history:
            lc["history"] = [
                {
                    "from": ev.from_state,
                    "to": ev.to_state,
                    "at": ev.timestamp,
                    "reason": ev.reason,
                }
                for ev in node.lifecycle_history
            ]
        data["lifecycle"] = lc

        # Versioning
        if node.version:
            data["version"] = node.version
        if node.lineage:
            data["lineage"] = node.lineage

        # Edges
        edges_block: dict[str, list[str]] = {}
        for edge in edges:
            yaml_key = _STORABLE_EDGE_TYPES.get(edge.edge_type)
            if yaml_key and edge.source == node.qualified_id:
                edges_block.setdefault(yaml_key, []).append(edge.target)
        if edges_block:
            data["edges"] = edges_block

        # Capability
        cap = node.capability
        if cap.inputs or cap.outputs or cap.tools_required:
            cap_data: dict[str, Any] = {}
            if cap.inputs:
                cap_data["inputs"] = cap.inputs
            if cap.outputs:
                cap_data["outputs"] = cap.outputs
            if cap.tools_required:
                cap_data["tools_required"] = cap.tools_required
            if cap.pre_flight:
                cap_data["pre_flight"] = cap.pre_flight
            if cap.model_preference:
                cap_data["model_preference"] = cap.model_preference
            data["capability"] = cap_data

        # Composition
        if node.composition:
            data["composition"] = {
                "mode": node.composition.mode.value,
                "stages": node.composition.stages,
            }
            if node.composition.fallback:
                data["composition"]["fallback"] = node.composition.fallback

        # Instance params
        if node.instance_params:
            data["instance_params"] = node.instance_params

        # Tags
        if node.tags:
            data["tags"] = node.tags

        return data
