"""In-memory property graph of skills and their relationships.

The SkillGraph is the core data structure of the ontology layer.
It stores nodes (skills, domains) and typed directed edges, with
inverted indexes for fast faceted lookup.

Think of it as a lightweight Neo4j that lives entirely in memory,
materialized from YAML sidecar files at startup.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterator

from neoskills.ontology.models import (
    DomainNode,
    EdgeType,
    EnrichmentLevel,
    LifecycleState,
    OntologyEdge,
    SkillNode,
    SkillType,
    SubGraph,
    ValidationResult,
)


class SkillGraph:
    """In-memory property graph over skills.

    Provides O(1) node lookup, O(1) faceted index access,
    and O(E) edge traversal. Designed for ~100-500 skills.
    """

    def __init__(self) -> None:
        # Primary storage
        self.nodes: dict[str, SkillNode] = {}
        self.edges: list[OntologyEdge] = []
        self.domains: dict[str, DomainNode] = {}

        # Inverted indexes — keys are facet values, values are sets of skill_ids
        self._by_domain: dict[str, set[str]] = defaultdict(set)
        self._by_type: dict[str, set[str]] = defaultdict(set)
        self._by_state: dict[str, set[str]] = defaultdict(set)
        self._by_tag: dict[str, set[str]] = defaultdict(set)
        self._by_namespace: dict[str, set[str]] = defaultdict(set)
        self._by_enrichment: dict[str, set[str]] = defaultdict(set)

        # Adjacency lists — skill_id → {edge_type → set of target_ids}
        self._forward: dict[str, dict[EdgeType, set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )
        self._reverse: dict[str, dict[EdgeType, set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )

    # ──────────────────────────────────────────────
    # Node operations
    # ──────────────────────────────────────────────

    def add_node(self, node: SkillNode) -> None:
        """Add or update a skill node and refresh indexes."""
        key = node.qualified_id
        # Remove old indexes if updating
        if key in self.nodes:
            self._unindex_node(key)
        self.nodes[key] = node
        self._index_node(node)

    def remove_node(self, skill_id: str) -> SkillNode | None:
        """Remove a node and all its edges. Returns the removed node."""
        if skill_id not in self.nodes:
            return None
        node = self.nodes.pop(skill_id)
        self._unindex_node(skill_id)
        # Remove all edges involving this node
        self.edges = [
            e for e in self.edges if e.source != skill_id and e.target != skill_id
        ]
        # Clean adjacency
        if skill_id in self._forward:
            del self._forward[skill_id]
        if skill_id in self._reverse:
            del self._reverse[skill_id]
        # Clean references from other nodes' adjacency
        for adj in self._forward.values():
            for targets in adj.values():
                targets.discard(skill_id)
        for adj in self._reverse.values():
            for sources in adj.values():
                sources.discard(skill_id)
        return node

    def get_node(self, skill_id: str) -> SkillNode | None:
        """Get a node by ID (supports both bare and qualified IDs)."""
        if skill_id in self.nodes:
            return self.nodes[skill_id]
        # Try matching by bare skill_id across namespaces
        for qid, node in self.nodes.items():
            if node.skill_id == skill_id:
                return node
        return None

    def has_node(self, skill_id: str) -> bool:
        return self.get_node(skill_id) is not None

    # ──────────────────────────────────────────────
    # Edge operations
    # ──────────────────────────────────────────────

    def add_edge(self, edge: OntologyEdge) -> None:
        """Add a directed edge. Idempotent — won't add duplicates."""
        if edge in self.edges:
            return
        self.edges.append(edge)
        self._forward[edge.source][edge.edge_type].add(edge.target)
        self._reverse[edge.target][edge.edge_type].add(edge.source)

    def remove_edge(
        self, source: str, target: str, edge_type: EdgeType
    ) -> bool:
        """Remove an edge. Returns True if found and removed."""
        sentinel = OntologyEdge(source=source, target=target, edge_type=edge_type)
        if sentinel not in self.edges:
            return False
        self.edges = [e for e in self.edges if e != sentinel]
        self._forward[source][edge_type].discard(target)
        self._reverse[target][edge_type].discard(source)
        return True

    def get_edges(
        self,
        source: str | None = None,
        target: str | None = None,
        edge_type: EdgeType | None = None,
    ) -> list[OntologyEdge]:
        """Query edges with optional filters."""
        results = self.edges
        if source is not None:
            results = [e for e in results if e.source == source]
        if target is not None:
            results = [e for e in results if e.target == target]
        if edge_type is not None:
            results = [e for e in results if e.edge_type == edge_type]
        return results

    # ──────────────────────────────────────────────
    # Faceted queries (use inverted indexes)
    # ──────────────────────────────────────────────

    def by_domain(self, domain: str) -> list[SkillNode]:
        """All skills in a given domain."""
        return [self.nodes[sid] for sid in self._by_domain.get(domain, set()) if sid in self.nodes]

    def by_type(self, skill_type: SkillType | str) -> list[SkillNode]:
        key = skill_type.value if isinstance(skill_type, SkillType) else skill_type
        return [self.nodes[sid] for sid in self._by_type.get(key, set()) if sid in self.nodes]

    def by_state(self, state: LifecycleState | str) -> list[SkillNode]:
        key = state.value if isinstance(state, LifecycleState) else state
        return [self.nodes[sid] for sid in self._by_state.get(key, set()) if sid in self.nodes]

    def by_tag(self, tag: str) -> list[SkillNode]:
        return [self.nodes[sid] for sid in self._by_tag.get(tag, set()) if sid in self.nodes]

    def by_namespace(self, namespace: str) -> list[SkillNode]:
        return [self.nodes[sid] for sid in self._by_namespace.get(namespace, set()) if sid in self.nodes]

    def by_enrichment(self, level: EnrichmentLevel | str) -> list[SkillNode]:
        key = level.value if isinstance(level, EnrichmentLevel) else level
        return [self.nodes[sid] for sid in self._by_enrichment.get(key, set()) if sid in self.nodes]

    def discover(
        self,
        domain: str | None = None,
        skill_type: str | None = None,
        state: str | None = None,
        tag: str | None = None,
        namespace: str | None = None,
        text: str | None = None,
    ) -> list[SkillNode]:
        """Faceted discovery — intersect all provided filters."""
        # Start with all skill IDs
        candidates: set[str] | None = None

        def intersect(ids: set[str]) -> None:
            nonlocal candidates
            if candidates is None:
                candidates = ids.copy()
            else:
                candidates &= ids

        if domain is not None:
            intersect(self._by_domain.get(domain, set()))
        if skill_type is not None:
            intersect(self._by_type.get(skill_type, set()))
        if state is not None:
            intersect(self._by_state.get(state, set()))
        if tag is not None:
            intersect(self._by_tag.get(tag, set()))
        if namespace is not None:
            intersect(self._by_namespace.get(namespace, set()))

        if candidates is None:
            candidates = set(self.nodes.keys())

        results = [self.nodes[sid] for sid in candidates if sid in self.nodes]

        # Text filter (substring match on name, description, tags)
        if text:
            text_lower = text.lower()
            results = [
                n
                for n in results
                if text_lower in n.name.lower()
                or text_lower in n.description.lower()
                or any(text_lower in t.lower() for t in n.tags)
                or text_lower in n.skill_id.lower()
            ]

        return sorted(results, key=lambda n: n.skill_id)

    # ──────────────────────────────────────────────
    # Graph traversal
    # ──────────────────────────────────────────────

    def neighbors(
        self, skill_id: str, edge_type: EdgeType | None = None, direction: str = "forward"
    ) -> set[str]:
        """Get immediate neighbors of a node."""
        adj = self._forward if direction == "forward" else self._reverse
        if skill_id not in adj:
            return set()
        if edge_type is not None:
            return adj[skill_id].get(edge_type, set()).copy()
        result: set[str] = set()
        for targets in adj[skill_id].values():
            result |= targets
        return result

    def dependencies(self, skill_id: str, transitive: bool = False) -> list[str]:
        """What this skill REQUIRES (forward traversal on REQUIRES edges)."""
        if not transitive:
            return sorted(self.neighbors(skill_id, EdgeType.REQUIRES, "forward"))
        return sorted(self._transitive_closure(skill_id, EdgeType.REQUIRES, "forward"))

    def dependents(self, skill_id: str, transitive: bool = False) -> list[str]:
        """What skills depend on this one (reverse REQUIRES traversal)."""
        if not transitive:
            return sorted(self.neighbors(skill_id, EdgeType.REQUIRES, "reverse"))
        return sorted(self._transitive_closure(skill_id, EdgeType.REQUIRES, "reverse"))

    def subgraph(self, skill_id: str, depth: int = 1) -> SubGraph:
        """Extract the N-hop neighborhood of a skill."""
        visited: set[str] = set()
        frontier: set[str] = {skill_id}

        for _ in range(depth):
            next_frontier: set[str] = set()
            for sid in frontier:
                if sid in visited:
                    continue
                visited.add(sid)
                next_frontier |= self.neighbors(sid, direction="forward")
                next_frontier |= self.neighbors(sid, direction="reverse")
            frontier = next_frontier - visited
        visited |= frontier

        nodes = {sid: self.nodes[sid] for sid in visited if sid in self.nodes}
        edges = [
            e for e in self.edges if e.source in visited and e.target in visited
        ]
        return SubGraph(nodes=nodes, edges=edges, center=skill_id, depth=depth)

    def find_path(
        self, from_id: str, to_id: str, max_depth: int = 10
    ) -> list[str] | None:
        """BFS shortest path between two skills (any edge type)."""
        if from_id == to_id:
            return [from_id]
        visited: set[str] = {from_id}
        queue: list[tuple[str, list[str]]] = [(from_id, [from_id])]
        while queue:
            current, path = queue.pop(0)
            if len(path) > max_depth:
                break
            for neighbor in self.neighbors(current, direction="forward") | self.neighbors(
                current, direction="reverse"
            ):
                if neighbor == to_id:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return None

    # ──────────────────────────────────────────────
    # Validation
    # ──────────────────────────────────────────────

    def validate(self) -> ValidationResult:
        """Check graph integrity."""
        errors: list[str] = []
        warnings: list[str] = []
        broken: list[OntologyEdge] = []
        cycles: list[list[str]] = []

        # Check for broken edges (referencing non-existent nodes)
        all_ids = set(self.nodes.keys()) | {n.skill_id for n in self.nodes.values()}
        for edge in self.edges:
            src_ok = edge.source in all_ids
            tgt_ok = edge.target in all_ids or edge.target in self.domains
            if not src_ok or not tgt_ok:
                broken.append(edge)
                errors.append(
                    f"Broken edge: {edge.source} --{edge.edge_type.value}--> {edge.target}"
                )

        # Check for cycles in REQUIRES edges
        requires_cycles = self._detect_cycles(EdgeType.REQUIRES)
        if requires_cycles:
            cycles.extend(requires_cycles)
            for cycle in requires_cycles:
                errors.append(f"REQUIRES cycle: {' → '.join(cycle)}")

        # Check CONFLICTS_WITH consistency (should be symmetric)
        for edge in self.get_edges(edge_type=EdgeType.CONFLICTS_WITH):
            reverse = OntologyEdge(
                source=edge.target, target=edge.source, edge_type=EdgeType.CONFLICTS_WITH
            )
            if reverse not in self.edges:
                warnings.append(
                    f"Asymmetric CONFLICTS_WITH: {edge.source} → {edge.target} "
                    f"(missing reverse)"
                )

        # Warn about L0 skills
        l0_count = len(self._by_enrichment.get("L0", set()))
        if l0_count > 0:
            warnings.append(
                f"{l0_count} skills at L0 (bare) — consider running "
                f"`neoskills ontology enrich --all`"
            )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            broken_edges=broken,
            cycles=cycles,
        )

    # ──────────────────────────────────────────────
    # Statistics
    # ──────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Summary statistics of the graph."""
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "total_domains": len(self.domains),
            "by_type": {k: len(v) for k, v in sorted(self._by_type.items())},
            "by_state": {k: len(v) for k, v in sorted(self._by_state.items())},
            "by_domain": {k: len(v) for k, v in sorted(self._by_domain.items())},
            "by_namespace": {k: len(v) for k, v in sorted(self._by_namespace.items())},
            "by_enrichment": {k: len(v) for k, v in sorted(self._by_enrichment.items())},
            "edge_type_counts": self._edge_type_counts(),
        }

    # ──────────────────────────────────────────────
    # Domain operations
    # ──────────────────────────────────────────────

    def add_domain(self, domain: DomainNode) -> None:
        self.domains[domain.domain_id] = domain

    def get_domain(self, domain_id: str) -> DomainNode | None:
        return self.domains.get(domain_id)

    # ──────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────

    def _index_node(self, node: SkillNode) -> None:
        key = node.qualified_id
        for d in node.domain:
            self._by_domain[d].add(key)
        self._by_type[node.type.value].add(key)
        self._by_state[node.lifecycle_state.value].add(key)
        for t in node.tags:
            self._by_tag[t].add(key)
        self._by_namespace[node.namespace or "local"].add(key)
        self._by_enrichment[node.enrichment_level.value].add(key)

    def _unindex_node(self, key: str) -> None:
        for idx in (
            self._by_domain,
            self._by_type,
            self._by_state,
            self._by_tag,
            self._by_namespace,
            self._by_enrichment,
        ):
            for bucket in idx.values():
                bucket.discard(key)

    def _transitive_closure(
        self, start: str, edge_type: EdgeType, direction: str
    ) -> set[str]:
        """BFS transitive closure along one edge type."""
        visited: set[str] = set()
        queue = [start]
        while queue:
            current = queue.pop(0)
            for neighbor in self.neighbors(current, edge_type, direction):
                if neighbor not in visited and neighbor != start:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return visited

    def _detect_cycles(self, edge_type: EdgeType) -> list[list[str]]:
        """Detect cycles in edges of a given type using DFS."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = defaultdict(int)
        cycles: list[list[str]] = []
        path: list[str] = []

        def dfs(node: str) -> None:
            color[node] = GRAY
            path.append(node)
            for neighbor in self.neighbors(node, edge_type, "forward"):
                if color[neighbor] == GRAY:
                    # Found a cycle
                    idx = path.index(neighbor)
                    cycles.append(path[idx:] + [neighbor])
                elif color[neighbor] == WHITE:
                    dfs(neighbor)
            path.pop()
            color[node] = BLACK

        for node_id in self.nodes:
            if color[node_id] == WHITE:
                dfs(node_id)

        return cycles

    def _edge_type_counts(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for e in self.edges:
            counts[e.edge_type.value] += 1
        return dict(sorted(counts.items()))

    # ──────────────────────────────────────────────
    # Iteration
    # ──────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self.nodes)

    def __iter__(self) -> Iterator[SkillNode]:
        return iter(self.nodes.values())

    def __contains__(self, skill_id: str) -> bool:
        return self.has_node(skill_id)
