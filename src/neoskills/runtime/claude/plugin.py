"""Claude Code MCP tools for neoskills embedded plugin mode.

These tools are exposed via the MCP protocol so Claude Code can invoke
neoskills operations directly as tool calls. In plugin mode, results
are namespace-qualified to avoid collisions with host agent skills.
"""

from neoskills.core.cellar import Cellar
from neoskills.core.linker import Linker
from neoskills.core.mode import detect_mode
from neoskills.core.namespace import NamespaceManager
from neoskills.core.tap import TapManager

_ns = NamespaceManager(mode=detect_mode())


def neoskills_list(query: str = "") -> dict:
    """List skills in taps, optionally filtered by query.

    Args:
        query: Optional search query to filter skills by name/description/tags.

    Returns:
        Dictionary with skill list and count.
    """
    cellar = Cellar()
    mgr = TapManager(cellar)

    if query:
        results = mgr.search(query)
        return {
            "mode": detect_mode().value,
            "count": len(results),
            "skills": [
                {
                    "id": _ns.qualify(s.skill_id),
                    "name": s.name,
                    "description": s.description,
                }
                for s in results
            ],
        }

    default_tap = cellar.default_tap
    skills = mgr.list_skills(default_tap)
    return {
        "mode": detect_mode().value,
        "count": len(skills),
        "skills": [
            {
                "id": _ns.qualify(s["skill_id"]),
                "name": s.get("name", s["skill_id"]),
                "description": s.get("description", ""),
            }
            for s in skills
        ],
    }


def neoskills_scan(target: str | None = None) -> dict:
    """Scan a target for linked skills.

    Args:
        target: Target to scan (default: from config).

    Returns:
        Dictionary with discovered skills.
    """
    cellar = Cellar()
    linker = Linker(cellar)
    links = linker.list_links(target)

    return {
        "target": target or cellar.load_config().get("default_target", "claude-code"),
        "count": len(links),
        "skills": [
            {
                "id": lnk["skill_id"],
                "is_symlink": lnk["is_symlink"],
                "source": lnk.get("source", ""),
            }
            for lnk in links
        ],
    }


def neoskills_deploy(skill_id: str, target: str | None = None) -> dict:
    """Link a skill from the default tap to a target.

    Args:
        skill_id: Skill to link (bare or namespace-qualified).
        target: Target to link to.

    Returns:
        Dictionary with link result.
    """
    bare_id = _ns.strip(skill_id)

    cellar = Cellar()
    mgr = TapManager(cellar)
    linker = Linker(cellar)

    source = mgr.get_skill_path(bare_id)
    if not source:
        return {"error": f"Skill '{bare_id}' not found in any tap"}

    action = linker.link(bare_id, source, target)
    return {
        "status": action.action,
        "skill_id": _ns.qualify(bare_id),
        "path": str(action.link_path),
    }


def neoskills_enhance(skill_id: str, operation: str = "audit") -> dict:
    """Enhance a skill using Claude.

    Args:
        skill_id: Skill to enhance (bare or namespace-qualified).
        operation: Enhancement operation (normalize, audit, add-docs, add-tests, generate-variant).

    Returns:
        Dictionary with enhancement result or error.
    """
    from neoskills.meta.enhancer import Enhancer

    bare_id = _ns.strip(skill_id)

    cellar = Cellar()
    mgr = TapManager(cellar)
    skill_path = mgr.get_skill_path(bare_id)

    if not skill_path:
        return {"error": f"Skill '{bare_id}' not found in any tap"}

    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return {"error": f"No SKILL.md found for '{bare_id}'"}

    enhancer = Enhancer()
    if not enhancer.available:
        return {"error": "No LLM backend available"}

    try:
        result = enhancer.enhance(skill_md.read_text(), operation)
        return {"status": "success", "operation": operation, "result": result}
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────
# Ontology MCP tools
# ──────────────────────────────────────────────


def neoskills_ontology_discover(
    domain: str = "",
    skill_type: str = "",
    state: str = "",
    tag: str = "",
    text: str = "",
) -> dict:
    """Discover skills by ontology facets.

    Args:
        domain: Filter by domain (e.g., "agent-architecture", "education").
        skill_type: Filter by type (task, meta, composite, template, utility, domain).
        state: Filter by lifecycle state (candidate, validated, operational, etc.).
        tag: Filter by tag.
        text: Free-text search in name/description/tags.

    Returns:
        Dictionary with matching skills.
    """
    from neoskills.ontology.engine import OntologyEngine

    engine = OntologyEngine.from_cellar()
    results = engine.discover(
        domain=domain or None,
        skill_type=skill_type or None,
        state=state or None,
        tag=tag or None,
        text=text or None,
    )

    return {
        "count": len(results),
        "skills": [
            {
                "id": _ns.qualify(n.skill_id),
                "name": n.name,
                "type": n.type.value,
                "domain": n.domain,
                "state": n.lifecycle_state.value,
                "version": n.version,
                "enrichment": n.enrichment_level.value,
            }
            for n in results[:50]  # Cap at 50 for tool responses
        ],
    }


def neoskills_ontology_deps(skill_id: str, transitive: bool = False) -> dict:
    """Get dependencies for a skill.

    Args:
        skill_id: Skill to check dependencies for.
        transitive: Whether to include transitive (indirect) dependencies.

    Returns:
        Dictionary with dependency list.
    """
    from neoskills.ontology.engine import OntologyEngine

    bare_id = _ns.strip(skill_id)
    engine = OntologyEngine.from_cellar()

    deps = engine.dependencies(bare_id, transitive=transitive)
    rdeps = engine.dependents(bare_id, transitive=transitive)

    return {
        "skill_id": bare_id,
        "dependencies": deps,
        "dependents": rdeps,
        "transitive": transitive,
    }


def neoskills_ontology_graph(skill_id: str, depth: int = 1, fmt: str = "mermaid") -> dict:
    """Get the neighborhood graph of a skill.

    Args:
        skill_id: Center skill for the graph view.
        depth: How many hops from center (1-3).
        fmt: Output format (mermaid, dot, json).

    Returns:
        Dictionary with rendered graph.
    """
    from neoskills.ontology.engine import OntologyEngine

    bare_id = _ns.strip(skill_id)
    engine = OntologyEngine.from_cellar()

    if fmt == "mermaid":
        content = engine.export_mermaid(bare_id, min(depth, 3))
    elif fmt == "dot":
        content = engine.export_dot(bare_id, min(depth, 3))
    else:
        sub = engine.find_related(bare_id, min(depth, 3))
        import json

        content = json.dumps(
            {
                "center": sub.center,
                "nodes": [n.skill_id for n in sub.nodes.values()],
                "edges": [
                    {"source": e.source, "target": e.target, "type": e.edge_type.value}
                    for e in sub.edges
                ],
            }
        )

    return {"skill_id": bare_id, "format": fmt, "depth": depth, "graph": content}


def neoskills_ontology_transition(skill_id: str, to_state: str, reason: str = "") -> dict:
    """Transition a skill's lifecycle state.

    Args:
        skill_id: Skill to transition.
        to_state: Target state (candidate, validated, operational, refined, deprecated, archived).
        reason: Reason for the transition.

    Returns:
        Dictionary with transition result.
    """
    from neoskills.ontology.engine import OntologyEngine

    bare_id = _ns.strip(skill_id)
    engine = OntologyEngine.from_cellar()

    try:
        result = engine.transition(bare_id, to_state, reason)
        return {"status": "success", **result}
    except Exception as e:
        return {"error": str(e)}


def neoskills_ontology_add_edge(source: str, target: str, edge_type: str) -> dict:
    """Add a relationship between two skills.

    Args:
        source: Source skill ID.
        target: Target skill ID.
        edge_type: One of: requires, extends, composes_with, conflicts_with, supersedes, derived_from.

    Returns:
        Dictionary with edge creation result.
    """
    from neoskills.ontology.engine import OntologyEngine

    engine = OntologyEngine.from_cellar()
    try:
        edge = engine.add_edge(_ns.strip(source), _ns.strip(target), edge_type)
        return {
            "status": "success",
            "source": edge.source,
            "target": edge.target,
            "type": edge.edge_type.value,
        }
    except Exception as e:
        return {"error": str(e)}


def neoskills_ontology_version(skill_id: str, bump: str = "patch") -> dict:
    """Bump a skill's version.

    Args:
        skill_id: Skill to version-bump.
        bump: Bump type (major, minor, patch).

    Returns:
        Dictionary with new version.
    """
    from neoskills.ontology.engine import OntologyEngine

    bare_id = _ns.strip(skill_id)
    engine = OntologyEngine.from_cellar()

    try:
        node = engine.get(bare_id)
        old_ver = node.version if node else "?"
        new_ver = engine.version_bump(bare_id, bump)
        return {"skill_id": bare_id, "old_version": old_ver, "new_version": new_ver}
    except Exception as e:
        return {"error": str(e)}


def neoskills_ontology_stats() -> dict:
    """Get ontology graph statistics.

    Returns:
        Dictionary with graph stats (counts by type, state, domain, etc.).
    """
    from neoskills.ontology.engine import OntologyEngine

    engine = OntologyEngine.from_cellar()
    return engine.stats()


def neoskills_capabilities() -> dict:
    """List available capability groups in the current execution mode.

    Returns:
        Dictionary with mode and available capabilities.
    """
    mode = detect_mode()
    caps = [
        "list",
        "scan",
        "deploy",
        "enhance",
        "doctor",
        "ontology_discover",
        "ontology_deps",
        "ontology_graph",
        "ontology_transition",
        "ontology_add_edge",
        "ontology_version",
        "ontology_stats",
    ]

    return {
        "mode": mode.value,
        "capabilities": [_ns.qualify(c) for c in caps],
    }
