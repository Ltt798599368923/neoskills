"""OntologyEngine — high-level API over the SkillGraph.

This is the primary interface for CLI and plugin consumers.
Wraps the graph, loader, writer, lifecycle, versioning, and
composition modules into a unified API.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from neoskills.ontology.graph import SkillGraph
from neoskills.ontology.loader import OntologyLoader
from neoskills.ontology.writer import OntologyWriter
from neoskills.ontology.lifecycle import (
    LifecycleError,
    lifecycle_summary,
    transition as lifecycle_transition,
)
from neoskills.ontology.versioning import VersionError, bump_version
from neoskills.ontology.composition import (
    CompositionError,
    compose,
    compose_edges,
    decompose_plan,
)
from neoskills.ontology.export import to_ascii_tree, to_dot, to_json, to_mermaid
from neoskills.ontology.models import (
    EdgeType,
    EnrichmentLevel,
    LifecycleState,
    OntologyEdge,
    SkillNode,
    SkillType,
    SubGraph,
    ValidationResult,
)

logger = logging.getLogger(__name__)


class OntologyEngine:
    """Unified query and mutation API for the skill ontology.

    Usage:
        engine = OntologyEngine.from_cellar()
        skills = engine.discover(domain="agent-architecture")
        engine.add_edge("kstar-loop", "kstar-planner", "requires")
        engine.transition("my-skill", "validated", reason="tested 5 times")
    """

    def __init__(self, graph: SkillGraph) -> None:
        self.graph = graph
        self._writer = OntologyWriter()

    # ──────────────────────────────────────────────
    # Factory methods
    # ──────────────────────────────────────────────

    @classmethod
    def from_cellar(
        cls,
        extra_source_trees: list[dict[str, Any]] | None = None,
        local_plugins_root: Path | None = None,
        remote_plugins_root: Path | None = None,
    ) -> OntologyEngine:
        """Load the ontology from the standard filesystem locations."""
        loader = OntologyLoader(
            extra_source_trees=extra_source_trees,
            local_plugins_root=local_plugins_root,
            remote_plugins_root=remote_plugins_root,
        )
        graph = loader.load()
        return cls(graph)

    @classmethod
    def from_paths(cls, skill_dirs: list[Path]) -> OntologyEngine:
        """Load from explicit skill directory paths (for testing)."""
        trees = [
            {"root": d.parent, "pattern": d.name, "namespace": "", "source_type": "local"}
            for d in skill_dirs
        ]
        loader = OntologyLoader(extra_source_trees=trees)
        graph = loader.load()
        return cls(graph)

    # ──────────────────────────────────────────────
    # Discovery
    # ──────────────────────────────────────────────

    def discover(
        self,
        domain: str | None = None,
        skill_type: str | None = None,
        state: str | None = None,
        tag: str | None = None,
        namespace: str | None = None,
        text: str | None = None,
    ) -> list[SkillNode]:
        """Faceted skill discovery."""
        return self.graph.discover(
            domain=domain,
            skill_type=skill_type,
            state=state,
            tag=tag,
            namespace=namespace,
            text=text,
        )

    def get(self, skill_id: str) -> SkillNode | None:
        """Get a single skill node by ID."""
        return self.graph.get_node(skill_id)

    def find_related(self, skill_id: str, depth: int = 1) -> SubGraph:
        """Return the N-hop neighborhood of a skill."""
        return self.graph.subgraph(skill_id, depth)

    def find_path(self, from_id: str, to_id: str) -> list[str] | None:
        """Shortest path between two skills."""
        return self.graph.find_path(from_id, to_id)

    # ──────────────────────────────────────────────
    # Dependencies
    # ──────────────────────────────────────────────

    def dependencies(self, skill_id: str, transitive: bool = False) -> list[str]:
        """What this skill requires."""
        return self.graph.dependencies(skill_id, transitive)

    def dependents(self, skill_id: str, transitive: bool = False) -> list[str]:
        """What depends on this skill."""
        return self.graph.dependents(skill_id, transitive)

    def check_conflicts(self, skill_ids: list[str]) -> list[tuple[str, str]]:
        """Check for conflicts among a set of skills."""
        conflicts: list[tuple[str, str]] = []
        for i, s1 in enumerate(skill_ids):
            for s2 in skill_ids[i + 1 :]:
                if self.graph.get_edges(
                    source=s1, target=s2, edge_type=EdgeType.CONFLICTS_WITH
                ) or self.graph.get_edges(
                    source=s2, target=s1, edge_type=EdgeType.CONFLICTS_WITH
                ):
                    conflicts.append((s1, s2))
        return conflicts

    # ──────────────────────────────────────────────
    # Edges
    # ──────────────────────────────────────────────

    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: str,
        persist: bool = True,
        **metadata: Any,
    ) -> OntologyEdge:
        """Add a relationship between two skills.

        Args:
            source: Source skill ID.
            target: Target skill ID.
            edge_type: One of: requires, extends, composes_with, conflicts_with,
                        supersedes, derived_from.
            persist: Whether to write to ontology.yaml.

        Returns:
            The created edge.
        """
        try:
            et = EdgeType(edge_type)
        except ValueError:
            valid = [e.value for e in EdgeType]
            raise ValueError(f"Unknown edge type '{edge_type}'. Valid: {valid}")

        edge = OntologyEdge(source=source, target=target, edge_type=et, metadata=metadata)
        self.graph.add_edge(edge)

        if persist:
            source_node = self.graph.get_node(source)
            if source_node:
                self._writer.add_edge_to_file(source_node, edge)
                # Upgrade enrichment level if needed
                if source_node.enrichment_level == EnrichmentLevel.L0_BARE:
                    source_node.enrichment_level = EnrichmentLevel.L1_TAGGED
                elif source_node.enrichment_level == EnrichmentLevel.L1_TAGGED:
                    source_node.enrichment_level = EnrichmentLevel.L2_CONNECTED

        return edge

    def remove_edge(
        self, source: str, target: str, edge_type: str, persist: bool = True
    ) -> bool:
        """Remove a relationship."""
        try:
            et = EdgeType(edge_type)
        except ValueError:
            return False

        removed = self.graph.remove_edge(source, target, et)
        if removed and persist:
            source_node = self.graph.get_node(source)
            if source_node:
                edge = OntologyEdge(source=source, target=target, edge_type=et)
                self._writer.remove_edge_from_file(source_node, edge)
        return removed

    # ──────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────

    def transition(
        self, skill_id: str, to_state: str, reason: str = "", persist: bool = True
    ) -> dict[str, str]:
        """Transition a skill through the lifecycle state machine."""
        node = self.graph.get_node(skill_id)
        if node is None:
            raise LifecycleError(f"Skill not found: {skill_id}")

        event = lifecycle_transition(node, to_state, reason)

        if persist:
            edges = self.graph.get_edges(source=node.qualified_id)
            self._writer.write_node(node, edges)

        return {
            "skill_id": skill_id,
            "from": event.from_state,
            "to": event.to_state,
            "reason": event.reason,
        }

    def lifecycle_report(self) -> dict[str, list[str]]:
        """Group all skills by lifecycle state."""
        return lifecycle_summary(list(self.graph))

    # ──────────────────────────────────────────────
    # Versioning
    # ──────────────────────────────────────────────

    def version_bump(
        self, skill_id: str, bump: str = "patch", persist: bool = True
    ) -> str:
        """Bump version and record lineage."""
        node = self.graph.get_node(skill_id)
        if node is None:
            raise VersionError(f"Skill not found: {skill_id}")

        new_version = bump_version(node, bump)

        if persist:
            edges = self.graph.get_edges(source=node.qualified_id)
            self._writer.write_node(node, edges)

        return new_version

    # ──────────────────────────────────────────────
    # Composition / Decomposition
    # ──────────────────────────────────────────────

    def compose(
        self,
        skill_ids: list[str],
        mode: str = "pipeline",
        name: str = "",
        description: str = "",
        output_dir: Path | None = None,
        persist: bool = True,
    ) -> SkillNode:
        """Create a composite skill from components."""
        composite = compose(
            self.graph, skill_ids, mode, name, description, output_dir
        )

        # Add to graph
        self.graph.add_node(composite)
        for edge in compose_edges(composite.qualified_id, skill_ids):
            self.graph.add_edge(edge)

        if persist and composite.path:
            composite.path.mkdir(parents=True, exist_ok=True)
            edges = self.graph.get_edges(source=composite.qualified_id)
            self._writer.write_node(composite, edges)

            # Write a minimal SKILL.md
            skill_md = composite.path / "SKILL.md"
            skill_md.write_text(
                f"---\nname: {composite.name}\n"
                f"description: \"{composite.description}\"\n---\n\n"
                f"# {composite.name}\n\n{composite.description}\n",
                encoding="utf-8",
            )

        return composite

    def decompose(self, skill_id: str, sub_skill_names: list[str]) -> dict[str, Any]:
        """Create a decomposition plan for a monolithic skill."""
        return decompose_plan(self.graph, skill_id, sub_skill_names)

    # ──────────────────────────────────────────────
    # Validation
    # ──────────────────────────────────────────────

    def validate(self) -> ValidationResult:
        """Check graph integrity."""
        return self.graph.validate()

    # ──────────────────────────────────────────────
    # Statistics
    # ──────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Graph summary statistics."""
        return self.graph.stats()

    # ──────────────────────────────────────────────
    # Export
    # ──────────────────────────────────────────────

    def export_mermaid(self, skill_id: str | None = None, depth: int = 1) -> str:
        """Export as Mermaid flowchart."""
        if skill_id:
            sub = self.graph.subgraph(skill_id, depth)
            return to_mermaid(sub, title=f"Neighborhood of {skill_id}")
        return to_mermaid(self.graph)

    def export_dot(self, skill_id: str | None = None, depth: int = 1) -> str:
        """Export as Graphviz DOT."""
        if skill_id:
            sub = self.graph.subgraph(skill_id, depth)
            return to_dot(sub, title=f"Neighborhood of {skill_id}")
        return to_dot(self.graph)

    def export_json(self) -> str:
        """Export full graph as JSON."""
        return to_json(self.graph)

    def export_tree(
        self, skill_id: str, edge_type: str = "requires", direction: str = "forward", depth: int = 3
    ) -> str:
        """Export dependency tree as ASCII art."""
        return to_ascii_tree(self.graph, skill_id, edge_type, direction, depth)

    # ──────────────────────────────────────────────
    # Enrichment (placeholder for Phase 3 Claude integration)
    # ──────────────────────────────────────────────

    def enrich(
        self, skill_id: str, level: str = "L1", dry_run: bool = False
    ) -> dict[str, Any]:
        """Auto-enrich a skill's ontology metadata.

        For L0→L1: uses heuristic inference (taxonomy, substrate detection).
        For L1→L2+: future — uses Claude to analyze SKILL.md content.

        Returns a dict of what would be / was changed.
        """
        node = self.graph.get_node(skill_id)
        if node is None:
            return {"error": f"Skill not found: {skill_id}"}

        changes: dict[str, Any] = {"skill_id": skill_id, "changes": {}}

        if level == "L1" and node.enrichment_level == EnrichmentLevel.L0_BARE:
            # Heuristic enrichment: infer type, domain, substrate
            from neoskills.ontology.taxonomy import infer_domain_from_skill_id

            inferred_domain = infer_domain_from_skill_id(node.skill_id)
            if inferred_domain != node.domain:
                changes["changes"]["domain"] = {"from": node.domain, "to": inferred_domain}
                if not dry_run:
                    node.domain = inferred_domain

            # Detect substrate from filesystem
            has_scripts = node.path and (node.path / "scripts").is_dir()
            new_substrate = SkillSubstrate.COMPOSITE if has_scripts else SkillSubstrate.PURE_PROMPT
            if new_substrate != node.substrate:
                changes["changes"]["substrate"] = {
                    "from": node.substrate.value,
                    "to": new_substrate.value,
                }
                if not dry_run:
                    node.substrate = new_substrate

            if not dry_run and changes["changes"]:
                node.enrichment_level = EnrichmentLevel.L1_TAGGED
                edges = self.graph.get_edges(source=node.qualified_id)
                self._writer.write_node(node, edges)

        changes["enrichment_level"] = node.enrichment_level.value
        changes["dry_run"] = dry_run
        return changes

    def enrich_all(self, level: str = "L1", dry_run: bool = True) -> list[dict[str, Any]]:
        """Batch-enrich all skills below target level."""
        results: list[dict[str, Any]] = []
        target_level = EnrichmentLevel(level) if level in [e.value for e in EnrichmentLevel] else EnrichmentLevel.L1_TAGGED

        for node in self.graph:
            # Only enrich if below target
            level_order = [EnrichmentLevel.L0_BARE, EnrichmentLevel.L1_TAGGED,
                          EnrichmentLevel.L2_CONNECTED, EnrichmentLevel.L3_GOVERNED]
            if level_order.index(node.enrichment_level) < level_order.index(target_level):
                result = self.enrich(node.qualified_id, level, dry_run)
                if result.get("changes"):
                    results.append(result)

        return results

    # ──────────────────────────────────────────────
    # Persistence helpers
    # ──────────────────────────────────────────────

    def save_node(self, skill_id: str) -> Path | None:
        """Persist a node's current state to ontology.yaml."""
        node = self.graph.get_node(skill_id)
        if node is None:
            return None
        edges = self.graph.get_edges(source=node.qualified_id)
        return self._writer.write_node(node, edges)
