"""CLI commands for the ontology layer.

neoskills ontology <subcommand>

Provides skill discovery, dependency analysis, lifecycle management,
composition, versioning, validation, and graph export.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from neoskills.ontology.engine import OntologyEngine
from neoskills.ontology.models import EnrichmentLevel


def _build_engine(ctx: click.Context) -> OntologyEngine:
    """Build the ontology engine, auto-detecting plugin paths."""
    home = Path.home()

    # Detect plugin roots from common locations
    local_plugins = None
    remote_plugins = None

    # Check for .local-plugins in standard locations
    for candidate in [
        home / ".local-plugins" / "cache",
        home / ".local-plugins" / "marketplaces",
        Path(".local-plugins") / "cache",
    ]:
        if candidate.exists():
            local_plugins = candidate
            break

    for candidate in [
        home / ".remote-plugins",
        Path(".remote-plugins"),
    ]:
        if candidate.exists():
            remote_plugins = candidate
            break

    return OntologyEngine.from_cellar(
        local_plugins_root=local_plugins,
        remote_plugins_root=remote_plugins,
    )


@click.group("ontology")
@click.pass_context
def ontology(ctx: click.Context) -> None:
    """Skill ontology — graph-based skill discovery, lifecycle, and composition."""
    ctx.ensure_object(dict)


# ──────────────────────────────────────────────
# Load / Stats / Validate
# ──────────────────────────────────────────────


@ontology.command("load")
@click.pass_context
def load_graph(ctx: click.Context) -> None:
    """Build the ontology graph from filesystem and print summary."""
    engine = _build_engine(ctx)
    s = engine.stats()

    click.echo(f"Ontology loaded: {s['total_nodes']} skills, {s['total_edges']} edges, {s['total_domains']} domains\n")

    if s["by_type"]:
        click.echo("By type:")
        for t, c in s["by_type"].items():
            click.echo(f"  {t:20s} {c}")
        click.echo()

    if s["by_enrichment"]:
        click.echo("By enrichment level:")
        for lev, c in s["by_enrichment"].items():
            click.echo(f"  {lev:20s} {c}")
        click.echo()

    if s["by_namespace"]:
        click.echo("By namespace:")
        for ns, c in s["by_namespace"].items():
            click.echo(f"  {ns or 'local':20s} {c}")
        click.echo()

    if s["edge_type_counts"]:
        click.echo("Edge types:")
        for et, c in s["edge_type_counts"].items():
            click.echo(f"  {et:20s} {c}")


@ontology.command("stats")
@click.pass_context
def stats(ctx: click.Context) -> None:
    """Print graph statistics as JSON."""
    engine = _build_engine(ctx)
    click.echo(json.dumps(engine.stats(), indent=2))


@ontology.command("validate")
@click.pass_context
def validate(ctx: click.Context) -> None:
    """Check graph integrity — broken edges, cycles, conflicts."""
    engine = _build_engine(ctx)
    result = engine.validate()

    if result.is_valid:
        click.echo("Graph is valid.")
    else:
        click.echo("Graph has errors:")
        for err in result.errors:
            click.echo(f"  ERROR: {err}")

    if result.warnings:
        click.echo("\nWarnings:")
        for w in result.warnings:
            click.echo(f"  WARN: {w}")

    sys.exit(0 if result.is_valid else 1)


# ──────────────────────────────────────────────
# Discovery
# ──────────────────────────────────────────────


@ontology.command("discover")
@click.option("--domain", "-d", help="Filter by domain")
@click.option("--type", "-t", "skill_type", help="Filter by type (task, meta, composite, ...)")
@click.option("--state", "-s", help="Filter by lifecycle state")
@click.option("--tag", help="Filter by tag")
@click.option("--namespace", "-n", help="Filter by namespace (local, plugin/<name>, ...)")
@click.option("--text", "-q", help="Text search in name/description/tags")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
@click.pass_context
def discover(
    ctx: click.Context,
    domain: str | None,
    skill_type: str | None,
    state: str | None,
    tag: str | None,
    namespace: str | None,
    text: str | None,
    json_output: bool,
) -> None:
    """Faceted skill discovery."""
    engine = _build_engine(ctx)
    results = engine.discover(
        domain=domain,
        skill_type=skill_type,
        state=state,
        tag=tag,
        namespace=namespace,
        text=text,
    )

    if json_output:
        click.echo(
            json.dumps(
                [
                    {
                        "skill_id": n.skill_id,
                        "name": n.name,
                        "type": n.type.value,
                        "domain": n.domain,
                        "state": n.lifecycle_state.value,
                        "version": n.version,
                        "enrichment": n.enrichment_level.value,
                        "namespace": n.namespace,
                    }
                    for n in results
                ],
                indent=2,
            )
        )
    else:
        if not results:
            click.echo("No skills match the given filters.")
            return
        click.echo(f"Found {len(results)} skills:\n")
        for n in results:
            ns = f" [{n.namespace}]" if n.namespace else ""
            domains = ", ".join(n.domain[:2]) if n.domain else "general"
            click.echo(
                f"  {n.skill_id:40s} {n.type.value:10s} {n.lifecycle_state.value:12s} "
                f"v{n.version:8s} {domains}{ns}"
            )


# ──────────────────────────────────────────────
# Dependencies
# ──────────────────────────────────────────────


@ontology.command("deps")
@click.argument("skill_id")
@click.option("--transitive", "-t", is_flag=True, help="Include transitive dependencies")
@click.option("--tree", is_flag=True, help="Show as ASCII tree")
@click.pass_context
def deps(ctx: click.Context, skill_id: str, transitive: bool, tree: bool) -> None:
    """Show what a skill requires (dependency tree)."""
    engine = _build_engine(ctx)

    if tree:
        output = engine.export_tree(skill_id, edge_type="requires", direction="forward")
        click.echo(output)
    else:
        dep_list = engine.dependencies(skill_id, transitive=transitive)
        if dep_list:
            click.echo(f"Dependencies for {skill_id}:")
            for d in dep_list:
                click.echo(f"  {d}")
        else:
            click.echo(f"{skill_id} has no dependencies.")


@ontology.command("rdeps")
@click.argument("skill_id")
@click.option("--transitive", "-t", is_flag=True, help="Include transitive dependents")
@click.option("--tree", is_flag=True, help="Show as ASCII tree")
@click.pass_context
def rdeps(ctx: click.Context, skill_id: str, transitive: bool, tree: bool) -> None:
    """Show what depends on a skill (reverse dependencies)."""
    engine = _build_engine(ctx)

    if tree:
        output = engine.export_tree(skill_id, edge_type="requires", direction="reverse")
        click.echo(output)
    else:
        dep_list = engine.dependents(skill_id, transitive=transitive)
        if dep_list:
            click.echo(f"Dependents of {skill_id}:")
            for d in dep_list:
                click.echo(f"  {d}")
        else:
            click.echo(f"Nothing depends on {skill_id}.")


@ontology.command("conflicts")
@click.pass_context
def conflicts(ctx: click.Context) -> None:
    """Report all conflict edges in the graph."""
    engine = _build_engine(ctx)
    from neoskills.ontology.models import EdgeType

    conflict_edges = engine.graph.get_edges(edge_type=EdgeType.CONFLICTS_WITH)
    if not conflict_edges:
        click.echo("No conflict edges found.")
    else:
        click.echo(f"Found {len(conflict_edges)} conflict edges:")
        for e in conflict_edges:
            click.echo(f"  {e.source} <--conflicts--> {e.target}")


# ──────────────────────────────────────────────
# Graph visualization
# ──────────────────────────────────────────────


@ontology.command("graph")
@click.argument("skill_id")
@click.option("--depth", "-d", default=1, help="Neighborhood depth (default: 1)")
@click.option("--format", "-f", "fmt", type=click.Choice(["mermaid", "dot", "json"]), default="mermaid")
@click.pass_context
def graph_cmd(ctx: click.Context, skill_id: str, depth: int, fmt: str) -> None:
    """Show the neighborhood graph of a skill."""
    engine = _build_engine(ctx)

    if fmt == "mermaid":
        click.echo(engine.export_mermaid(skill_id, depth))
    elif fmt == "dot":
        click.echo(engine.export_dot(skill_id, depth))
    elif fmt == "json":
        sub = engine.find_related(skill_id, depth)
        click.echo(
            json.dumps(
                {
                    "center": sub.center,
                    "depth": sub.depth,
                    "nodes": [n.skill_id for n in sub.nodes.values()],
                    "edges": [
                        {"source": e.source, "target": e.target, "type": e.edge_type.value}
                        for e in sub.edges
                    ],
                },
                indent=2,
            )
        )


# ──────────────────────────────────────────────
# Lifecycle
# ──────────────────────────────────────────────


@ontology.command("lifecycle")
@click.pass_context
def lifecycle_cmd(ctx: click.Context) -> None:
    """Show all skills grouped by lifecycle state."""
    engine = _build_engine(ctx)
    report = engine.lifecycle_report()

    for state, skills in report.items():
        if skills:
            click.echo(f"\n{state.upper()} ({len(skills)}):")
            for s in skills:
                click.echo(f"  {s}")

    click.echo()


@ontology.command("transition")
@click.argument("skill_id")
@click.argument("to_state")
@click.option("--reason", "-r", default="", help="Reason for transition")
@click.pass_context
def transition_cmd(ctx: click.Context, skill_id: str, to_state: str, reason: str) -> None:
    """Transition a skill's lifecycle state."""
    engine = _build_engine(ctx)
    try:
        result = engine.transition(skill_id, to_state, reason)
        click.echo(
            f"Transitioned {result['skill_id']}: "
            f"{result['from']} → {result['to']}"
        )
        if result["reason"]:
            click.echo(f"  Reason: {result['reason']}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# ──────────────────────────────────────────────
# Edges
# ──────────────────────────────────────────────


@ontology.command("add-edge")
@click.argument("source")
@click.argument("target")
@click.option(
    "--type", "-t", "edge_type", required=True,
    type=click.Choice(["requires", "extends", "composes_with", "conflicts_with", "supersedes", "derived_from"]),
    help="Edge type",
)
@click.pass_context
def add_edge_cmd(ctx: click.Context, source: str, target: str, edge_type: str) -> None:
    """Add a relationship between two skills."""
    engine = _build_engine(ctx)
    try:
        edge = engine.add_edge(source, target, edge_type)
        click.echo(f"Added: {edge.source} --{edge.edge_type.value}--> {edge.target}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@ontology.command("remove-edge")
@click.argument("source")
@click.argument("target")
@click.option(
    "--type", "-t", "edge_type", required=True,
    type=click.Choice(["requires", "extends", "composes_with", "conflicts_with", "supersedes", "derived_from"]),
)
@click.pass_context
def remove_edge_cmd(ctx: click.Context, source: str, target: str, edge_type: str) -> None:
    """Remove a relationship between two skills."""
    engine = _build_engine(ctx)
    removed = engine.remove_edge(source, target, edge_type)
    if removed:
        click.echo(f"Removed: {source} --{edge_type}--> {target}")
    else:
        click.echo("Edge not found.")


# ──────────────────────────────────────────────
# Versioning
# ──────────────────────────────────────────────


@ontology.command("version")
@click.argument("skill_id")
@click.option("--bump", "-b", type=click.Choice(["major", "minor", "patch"]), default="patch")
@click.pass_context
def version_cmd(ctx: click.Context, skill_id: str, bump: str) -> None:
    """Bump a skill's version (major/minor/patch)."""
    engine = _build_engine(ctx)
    try:
        old_node = engine.get(skill_id)
        old_ver = old_node.version if old_node else "?"
        new_ver = engine.version_bump(skill_id, bump)
        click.echo(f"{skill_id}: {old_ver} → {new_ver}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# ──────────────────────────────────────────────
# Composition / Decomposition
# ──────────────────────────────────────────────


@ontology.command("compose")
@click.argument("skill_ids", nargs=-1, required=True)
@click.option("--mode", "-m", type=click.Choice(["pipeline", "ensemble", "selector"]), default="pipeline")
@click.option("--name", "-n", default="", help="Name for the composite skill")
@click.option("--output-dir", "-o", type=click.Path(), default=None, help="Output directory")
@click.pass_context
def compose_cmd(
    ctx: click.Context,
    skill_ids: tuple[str, ...],
    mode: str,
    name: str,
    output_dir: str | None,
) -> None:
    """Compose multiple skills into a pipeline/ensemble/selector."""
    engine = _build_engine(ctx)
    out = Path(output_dir) if output_dir else None
    try:
        composite = engine.compose(list(skill_ids), mode, name, output_dir=out)
        click.echo(f"Created composite skill: {composite.skill_id}")
        click.echo(f"  Mode: {mode}")
        click.echo(f"  Components: {', '.join(skill_ids)}")
        if composite.path:
            click.echo(f"  Path: {composite.path}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@ontology.command("split")
@click.argument("skill_id")
@click.argument("sub_names", nargs=-1, required=True)
@click.option("--dry-run", is_flag=True, help="Preview the split plan without executing")
@click.pass_context
def split_cmd(ctx: click.Context, skill_id: str, sub_names: tuple[str, ...], dry_run: bool) -> None:
    """Plan decomposition of a monolithic skill into sub-skills."""
    engine = _build_engine(ctx)
    try:
        plan = engine.decompose(skill_id, list(sub_names))
        click.echo(json.dumps(plan, indent=2))
        if dry_run:
            click.echo("\n(dry run — no changes made)")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# ──────────────────────────────────────────────
# Enrichment
# ──────────────────────────────────────────────


@ontology.command("enrich")
@click.argument("skill_id", required=False, default=None)
@click.option("--all", "enrich_all", is_flag=True, help="Enrich all L0 skills")
@click.option("--level", "-l", default="L1", help="Target enrichment level")
@click.option("--dry-run", is_flag=True, help="Preview changes without writing")
@click.pass_context
def enrich_cmd(
    ctx: click.Context,
    skill_id: str | None,
    enrich_all: bool,
    level: str,
    dry_run: bool,
) -> None:
    """Auto-enrich skill ontology metadata (heuristic + Claude-powered)."""
    engine = _build_engine(ctx)

    if enrich_all:
        results = engine.enrich_all(level=level, dry_run=dry_run)
        if results:
            click.echo(f"{'Would enrich' if dry_run else 'Enriched'} {len(results)} skills:")
            for r in results:
                click.echo(f"  {r['skill_id']}: {json.dumps(r.get('changes', {}))}")
        else:
            click.echo("All skills already at or above target level.")
    elif skill_id:
        result = engine.enrich(skill_id, level=level, dry_run=dry_run)
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo("Specify a skill_id or --all", err=True)
        sys.exit(1)


# ──────────────────────────────────────────────
# Export
# ──────────────────────────────────────────────


@ontology.command("export")
@click.option("--format", "-f", "fmt", type=click.Choice(["mermaid", "dot", "json"]), default="json")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output file (default: stdout)")
@click.pass_context
def export_cmd(ctx: click.Context, fmt: str, output: str | None) -> None:
    """Export the full graph."""
    engine = _build_engine(ctx)

    if fmt == "mermaid":
        content = engine.export_mermaid()
    elif fmt == "dot":
        content = engine.export_dot()
    else:
        content = engine.export_json()

    if output:
        Path(output).write_text(content, encoding="utf-8")
        click.echo(f"Exported to {output}")
    else:
        click.echo(content)
