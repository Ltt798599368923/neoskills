"""Export the skill graph to various formats (Mermaid, DOT, JSON)."""

from __future__ import annotations

import json
from typing import Any

from neoskills.ontology.models import OntologyEdge, SkillNode, SubGraph
from neoskills.ontology.graph import SkillGraph


def to_mermaid(
    graph_or_subgraph: SkillGraph | SubGraph,
    title: str = "Skill Ontology",
) -> str:
    """Export graph or subgraph as a Mermaid flowchart."""
    if isinstance(graph_or_subgraph, SubGraph):
        nodes = graph_or_subgraph.nodes
        edges = graph_or_subgraph.edges
        center = graph_or_subgraph.center
    else:
        nodes = graph_or_subgraph.nodes
        edges = graph_or_subgraph.edges
        center = ""

    lines = [f"---", f"title: {title}", f"---", "graph LR"]

    # Sanitize ID for Mermaid (replace hyphens, slashes)
    def mid(s: str) -> str:
        return s.replace("-", "_").replace("/", "__").replace(".", "_")

    # Node declarations
    for nid, node in sorted(nodes.items()):
        label = node.name or node.skill_id
        state = node.lifecycle_state.value
        ntype = node.type.value

        # Shape by type
        if ntype == "composite":
            shape = '{0}[["<b>{1}</b><br/><i>{2}</i>"]]'.format(mid(nid), label, state)
        elif ntype == "meta":
            shape = '{0}("{1}<br/><i>{2}</i>")'.format(mid(nid), label, state)
        elif ntype == "template":
            shape = '{0}["{1}<br/><i>{2}</i>"]'.format(mid(nid), label, state)
        else:
            shape = '{0}["{1}<br/><i>{2}</i>"]'.format(mid(nid), label, state)

        lines.append(f"    {shape}")

        # Highlight center node
        if nid == center:
            lines.append(f"    style {mid(nid)} fill:#f9f,stroke:#333,stroke-width:2px")

    # Edge declarations
    edge_style = {
        "requires": "-->|requires|",
        "extends": "-.->|extends|",
        "composes_with": "==>|composes|",
        "conflicts_with": "-- conflicts ---",
        "supersedes": "-->|supersedes|",
        "derived_from": "-.->|derived|",
        "belongs_to": "-->|domain|",
    }

    for edge in edges:
        src = mid(edge.source)
        tgt = mid(edge.target)
        style = edge_style.get(edge.edge_type.value, "-->")
        # Skip domain edges for cleaner diagrams
        if edge.edge_type.value == "belongs_to":
            continue
        lines.append(f"    {src} {style} {tgt}")

    return "\n".join(lines)


def to_dot(
    graph_or_subgraph: SkillGraph | SubGraph,
    title: str = "Skill Ontology",
) -> str:
    """Export graph or subgraph as Graphviz DOT."""
    if isinstance(graph_or_subgraph, SubGraph):
        nodes = graph_or_subgraph.nodes
        edges = graph_or_subgraph.edges
    else:
        nodes = graph_or_subgraph.nodes
        edges = graph_or_subgraph.edges

    lines = [f'digraph "{title}" {{', '    rankdir=LR;', '    node [shape=box, style=rounded];']

    # Type → shape mapping
    shape_map = {
        "composite": "doubleoctagon",
        "meta": "ellipse",
        "template": "diamond",
        "task": "box",
        "domain": "hexagon",
        "utility": "component",
    }

    for nid, node in sorted(nodes.items()):
        shape = shape_map.get(node.type.value, "box")
        label = f"{node.name or node.skill_id}\\n[{node.lifecycle_state.value}]"
        lines.append(f'    "{nid}" [label="{label}", shape={shape}];')

    # Edge style mapping
    edge_attrs = {
        "requires": 'style=solid, color=red',
        "extends": 'style=dashed, color=blue',
        "composes_with": 'style=bold, color=green',
        "conflicts_with": 'style=dotted, color=orange, dir=both',
        "supersedes": 'style=solid, color=gray',
        "derived_from": 'style=dashed, color=gray',
    }

    for edge in edges:
        if edge.edge_type.value == "belongs_to":
            continue
        attrs = edge_attrs.get(edge.edge_type.value, "")
        label = edge.edge_type.value
        lines.append(f'    "{edge.source}" -> "{edge.target}" [label="{label}", {attrs}];')

    lines.append("}")
    return "\n".join(lines)


def to_json(graph: SkillGraph) -> str:
    """Export full graph as JSON."""

    def node_dict(n: SkillNode) -> dict[str, Any]:
        return {
            "skill_id": n.skill_id,
            "qualified_id": n.qualified_id,
            "name": n.name,
            "description": n.description[:200],
            "namespace": n.namespace,
            "type": n.type.value,
            "domain": n.domain,
            "lifecycle_state": n.lifecycle_state.value,
            "maturity": n.maturity,
            "version": n.version,
            "enrichment_level": n.enrichment_level.value,
            "tags": n.tags,
            "source_type": n.source_type,
        }

    def edge_dict(e: OntologyEdge) -> dict[str, Any]:
        return {
            "source": e.source,
            "target": e.target,
            "type": e.edge_type.value,
            "metadata": e.metadata,
        }

    data = {
        "nodes": [node_dict(n) for n in sorted(graph, key=lambda x: x.skill_id)],
        "edges": [edge_dict(e) for e in graph.edges],
        "domains": [
            {"domain_id": d.domain_id, "display_name": d.display_name, "parent": d.parent_domain}
            for d in sorted(graph.domains.values(), key=lambda x: x.domain_id)
        ],
        "stats": graph.stats(),
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


def to_ascii_tree(
    graph: SkillGraph, skill_id: str, edge_type: str = "requires", direction: str = "forward", depth: int = 3
) -> str:
    """Render a dependency tree as ASCII art."""
    from neoskills.ontology.models import EdgeType

    try:
        et = EdgeType(edge_type)
    except ValueError:
        return f"Unknown edge type: {edge_type}"

    lines: list[str] = []

    def _render(sid: str, prefix: str, is_last: bool, visited: set[str], current_depth: int) -> None:
        if current_depth > depth:
            return

        node = graph.get_node(sid)
        label = f"{sid}"
        if node:
            state = node.lifecycle_state.value
            label = f"{node.name or sid} [{state}] v{node.version}"

        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{label}" if prefix else label)

        if sid in visited:
            lines.append(f"{prefix}{'    ' if is_last else '│   '}  (cycle)")
            return
        visited.add(sid)

        neighbors = sorted(graph.neighbors(sid, et, direction))
        for i, neighbor in enumerate(neighbors):
            child_prefix = prefix + ("    " if is_last else "│   ")
            _render(neighbor, child_prefix, i == len(neighbors) - 1, visited, current_depth + 1)

    _render(skill_id, "", True, set(), 0)
    return "\n".join(lines)
