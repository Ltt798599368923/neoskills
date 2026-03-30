"""Tests for the ontology layer — models, graph, lifecycle, versioning, composition."""

import sys
import tempfile
from pathlib import Path

import pytest
import yaml

# Ensure src is on the path for direct pytest runs
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from neoskills.ontology.models import (
    EdgeType,
    EnrichmentLevel,
    LifecycleState,
    OntologyEdge,
    SkillNode,
    SkillType,
    SkillSubstrate,
    CapabilityManifest,
    CompositionSpec,
    CompositionMode,
    ValidationResult,
)
from neoskills.ontology.graph import SkillGraph
from neoskills.ontology.lifecycle import LifecycleError, transition, lifecycle_summary
from neoskills.ontology.versioning import VersionError, bump_version, parse_semver, compare_versions
from neoskills.ontology.taxonomy import build_domain_nodes, infer_domain_from_skill_id, get_all_domain_ids
from neoskills.ontology.writer import OntologyWriter
from neoskills.ontology.loader import _parse_ontology_yaml, _parse_skill_md, _build_node
from neoskills.ontology.export import to_mermaid, to_json, to_ascii_tree
from neoskills.ontology.engine import OntologyEngine


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────


def _make_node(skill_id: str, **kwargs) -> SkillNode:
    """Helper to create a SkillNode with defaults."""
    defaults = {
        "name": skill_id,
        "type": SkillType.TASK,
        "domain": ["general"],
        "lifecycle_state": LifecycleState.CANDIDATE,
        "version": "0.1.0",
        "enrichment_level": EnrichmentLevel.L0_BARE,
    }
    defaults.update(kwargs)
    return SkillNode(skill_id=skill_id, **defaults)


def _make_graph() -> SkillGraph:
    """Build a small test graph with 5 skills and relationships."""
    g = SkillGraph()

    # Nodes
    loop = _make_node("kstar-loop", type=SkillType.META, domain=["agent-architecture"])
    planner = _make_node("kstar-planner", domain=["agent-architecture"])
    observer = _make_node("kstar-observer", domain=["agent-architecture"])
    delta = _make_node("kstar-delta", domain=["agent-architecture"])
    compiler = _make_node(
        "kstar-episode-compiler",
        type=SkillType.META,
        domain=["agent-architecture", "skill-management"],
        lifecycle_state=LifecycleState.OPERATIONAL,
        version="1.0.0",
        enrichment_level=EnrichmentLevel.L3_GOVERNED,
    )

    for n in [loop, planner, observer, delta, compiler]:
        g.add_node(n)

    # Edges: loop requires planner, observer, delta
    for dep in ["kstar-planner", "kstar-observer", "kstar-delta"]:
        g.add_edge(OntologyEdge(source="kstar-loop", target=dep, edge_type=EdgeType.REQUIRES))

    # Compiler composes with loop
    g.add_edge(
        OntologyEdge(source="kstar-episode-compiler", target="kstar-loop", edge_type=EdgeType.COMPOSES_WITH)
    )

    return g


# ──────────────────────────────────────────────
# Model tests
# ──────────────────────────────────────────────


class TestLifecycleState:
    def test_valid_transitions(self):
        assert LifecycleState.CANDIDATE.can_transition_to(LifecycleState.VALIDATED)
        assert LifecycleState.VALIDATED.can_transition_to(LifecycleState.OPERATIONAL)
        assert LifecycleState.OPERATIONAL.can_transition_to(LifecycleState.REFINED)
        assert LifecycleState.REFINED.can_transition_to(LifecycleState.OPERATIONAL)

    def test_invalid_transitions(self):
        assert not LifecycleState.CANDIDATE.can_transition_to(LifecycleState.OPERATIONAL)
        assert not LifecycleState.ARCHIVED.can_transition_to(LifecycleState.CANDIDATE)

    def test_deprecation_from_any_active(self):
        for state in [LifecycleState.CANDIDATE, LifecycleState.VALIDATED,
                      LifecycleState.OPERATIONAL, LifecycleState.REFINED]:
            assert state.can_transition_to(LifecycleState.DEPRECATED)


class TestSkillNode:
    def test_qualified_id_local(self):
        n = _make_node("my-skill")
        assert n.qualified_id == "my-skill"

    def test_qualified_id_namespaced(self):
        n = _make_node("variance-analysis", namespace="plugin/finance")
        assert n.qualified_id == "plugin/finance/variance-analysis"


class TestOntologyEdge:
    def test_equality(self):
        e1 = OntologyEdge(source="a", target="b", edge_type=EdgeType.REQUIRES)
        e2 = OntologyEdge(source="a", target="b", edge_type=EdgeType.REQUIRES, metadata={"x": 1})
        assert e1 == e2

    def test_inequality(self):
        e1 = OntologyEdge(source="a", target="b", edge_type=EdgeType.REQUIRES)
        e2 = OntologyEdge(source="a", target="b", edge_type=EdgeType.EXTENDS)
        assert e1 != e2

    def test_hashable(self):
        e = OntologyEdge(source="a", target="b", edge_type=EdgeType.REQUIRES)
        s = {e}
        assert len(s) == 1


# ──────────────────────────────────────────────
# Graph tests
# ──────────────────────────────────────────────


class TestSkillGraph:
    def test_add_and_get_node(self):
        g = SkillGraph()
        n = _make_node("test-skill")
        g.add_node(n)
        assert g.get_node("test-skill") == n
        assert "test-skill" in g
        assert len(g) == 1

    def test_remove_node(self):
        g = _make_graph()
        removed = g.remove_node("kstar-delta")
        assert removed is not None
        assert "kstar-delta" not in g
        # Edges involving delta should be gone
        assert not g.get_edges(target="kstar-delta")

    def test_add_edge_idempotent(self):
        g = SkillGraph()
        g.add_node(_make_node("a"))
        g.add_node(_make_node("b"))
        e = OntologyEdge(source="a", target="b", edge_type=EdgeType.REQUIRES)
        g.add_edge(e)
        g.add_edge(e)  # Duplicate
        assert len(g.get_edges(source="a")) == 1

    def test_faceted_discovery(self):
        g = _make_graph()
        # By type
        metas = g.by_type(SkillType.META)
        assert len(metas) == 2
        ids = {n.skill_id for n in metas}
        assert "kstar-loop" in ids
        assert "kstar-episode-compiler" in ids

        # By domain
        arch = g.by_domain("agent-architecture")
        assert len(arch) == 5

        # By state
        ops = g.by_state(LifecycleState.OPERATIONAL)
        assert len(ops) == 1
        assert ops[0].skill_id == "kstar-episode-compiler"

    def test_discover_intersection(self):
        g = _make_graph()
        results = g.discover(domain="agent-architecture", skill_type="meta")
        assert len(results) == 2

    def test_discover_text(self):
        g = _make_graph()
        results = g.discover(text="compiler")
        assert len(results) == 1
        assert results[0].skill_id == "kstar-episode-compiler"

    def test_dependencies(self):
        g = _make_graph()
        deps = g.dependencies("kstar-loop")
        assert set(deps) == {"kstar-planner", "kstar-observer", "kstar-delta"}

    def test_dependents(self):
        g = _make_graph()
        rdeps = g.dependents("kstar-planner")
        assert "kstar-loop" in rdeps

    def test_subgraph(self):
        g = _make_graph()
        sub = g.subgraph("kstar-loop", depth=1)
        # Should include loop + its 3 REQUIRES targets + compiler (via COMPOSES_WITH reverse)
        assert "kstar-loop" in sub.nodes
        assert "kstar-planner" in sub.nodes

    def test_validate_clean(self):
        g = _make_graph()
        result = g.validate()
        # Should have no errors (maybe warnings about L0 skills)
        assert len(result.errors) == 0

    def test_validate_broken_edge(self):
        g = SkillGraph()
        g.add_node(_make_node("a"))
        g.add_edge(OntologyEdge(source="a", target="nonexistent", edge_type=EdgeType.REQUIRES))
        result = g.validate()
        assert len(result.errors) > 0
        assert len(result.broken_edges) == 1

    def test_find_path(self):
        g = _make_graph()
        path = g.find_path("kstar-episode-compiler", "kstar-planner")
        assert path is not None
        assert path[0] == "kstar-episode-compiler"
        assert path[-1] == "kstar-planner"

    def test_stats(self):
        g = _make_graph()
        s = g.stats()
        assert s["total_nodes"] == 5
        assert s["total_edges"] == 4  # 3 REQUIRES + 1 COMPOSES_WITH


# ──────────────────────────────────────────────
# Lifecycle tests
# ──────────────────────────────────────────────


class TestLifecycle:
    def test_transition_happy_path(self):
        n = _make_node("s", lifecycle_state=LifecycleState.CANDIDATE)
        ev = transition(n, "validated", "Passed tests")
        assert n.lifecycle_state == LifecycleState.VALIDATED
        assert ev.from_state == "candidate"
        assert ev.to_state == "validated"
        assert len(n.lifecycle_history) == 1

    def test_transition_invalid(self):
        n = _make_node("s", lifecycle_state=LifecycleState.CANDIDATE)
        with pytest.raises(LifecycleError):
            transition(n, "operational")

    def test_transition_same_state(self):
        n = _make_node("s", lifecycle_state=LifecycleState.CANDIDATE)
        with pytest.raises(LifecycleError):
            transition(n, "candidate")

    def test_lifecycle_summary(self):
        nodes = [
            _make_node("a", lifecycle_state=LifecycleState.CANDIDATE),
            _make_node("b", lifecycle_state=LifecycleState.OPERATIONAL),
            _make_node("c", lifecycle_state=LifecycleState.OPERATIONAL),
        ]
        summary = lifecycle_summary(nodes)
        assert len(summary["candidate"]) == 1
        assert len(summary["operational"]) == 2


# ──────────────────────────────────────────────
# Versioning tests
# ──────────────────────────────────────────────


class TestVersioning:
    def test_parse_semver(self):
        assert parse_semver("1.2.3") == (1, 2, 3, "")
        assert parse_semver("0.1.0-beta") == (0, 1, 0, "beta")

    def test_parse_semver_invalid(self):
        with pytest.raises(VersionError):
            parse_semver("not-a-version")

    def test_bump_patch(self):
        n = _make_node("s", version="1.2.3")
        new = bump_version(n, "patch")
        assert new == "1.2.4"
        assert n.version == "1.2.4"
        assert "s@1.2.3" in n.lineage

    def test_bump_minor(self):
        n = _make_node("s", version="1.2.3")
        new = bump_version(n, "minor")
        assert new == "1.3.0"

    def test_bump_major(self):
        n = _make_node("s", version="1.2.3")
        new = bump_version(n, "major")
        assert new == "2.0.0"

    def test_compare_versions(self):
        assert compare_versions("1.0.0", "2.0.0") == -1
        assert compare_versions("1.0.0", "1.0.0") == 0
        assert compare_versions("2.0.0", "1.0.0") == 1


# ──────────────────────────────────────────────
# Taxonomy tests
# ──────────────────────────────────────────────


class TestTaxonomy:
    def test_build_domains(self):
        nodes = build_domain_nodes()
        assert "agent-architecture" in nodes
        assert "kstar-cognitive" in nodes
        assert nodes["kstar-cognitive"].parent_domain == "agent-architecture"

    def test_all_domain_ids(self):
        ids = get_all_domain_ids()
        assert len(ids) > 20
        assert "education" in ids
        assert "finance" in ids

    def test_infer_domain(self):
        assert "kstar-cognitive" in infer_domain_from_skill_id("kstar-planner")
        assert "academic" in infer_domain_from_skill_id("paper-refinement")
        assert "bidding" in infer_domain_from_skill_id("bid-doc-composer")
        assert "general" in infer_domain_from_skill_id("unknown-random-skill")


# ──────────────────────────────────────────────
# Writer / Loader round-trip tests
# ──────────────────────────────────────────────


class TestWriterLoader:
    def test_write_and_read_ontology_yaml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "my-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("---\nname: My Skill\ndescription: test\n---\nBody\n")

            # Write
            node = _make_node(
                "my-skill",
                path=skill_dir,
                type=SkillType.META,
                domain=["agent-architecture"],
                version="1.0.0",
                tags=["test", "meta"],
            )
            writer = OntologyWriter()
            edge = OntologyEdge(source="my-skill", target="other-skill", edge_type=EdgeType.REQUIRES)
            writer.write_node(node, [edge])

            # Read back
            onto = _parse_ontology_yaml(skill_dir)
            assert onto is not None
            assert onto["type"] == "meta"
            assert "agent-architecture" in onto["domain"]
            assert onto["version"] == "1.0.0"
            assert "requires" in onto.get("edges", {})
            assert "other-skill" in onto["edges"]["requires"]

    def test_add_edge_to_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "s"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("---\nname: S\n---\n")

            node = _make_node("s", path=skill_dir)
            writer = OntologyWriter()

            # Add first edge
            e1 = OntologyEdge(source="s", target="a", edge_type=EdgeType.REQUIRES)
            writer.add_edge_to_file(node, e1)

            # Add second edge
            e2 = OntologyEdge(source="s", target="b", edge_type=EdgeType.COMPOSES_WITH)
            writer.add_edge_to_file(node, e2)

            onto = _parse_ontology_yaml(skill_dir)
            assert "a" in onto["edges"]["requires"]
            assert "b" in onto["edges"]["composes_with"]

    def test_build_node_from_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "test-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: Test Skill\ndescription: A test\ntags: [test]\n---\nBody\n"
            )
            (skill_dir / "ontology.yaml").write_text(yaml.dump({
                "schema_version": "1.0",
                "type": "meta",
                "domain": ["education"],
                "lifecycle": {"state": "operational", "maturity": "production"},
                "edges": {"requires": ["other-skill"]},
            }))

            fm = _parse_skill_md(skill_dir)
            onto = _parse_ontology_yaml(skill_dir)
            node = _build_node(skill_dir, fm, onto, "", "local")

            assert node.skill_id == "test-skill"
            assert node.type == SkillType.META
            assert "education" in node.domain
            assert node.lifecycle_state == LifecycleState.OPERATIONAL
            # Has both lifecycle.state and edges → L3
            assert node.enrichment_level == EnrichmentLevel.L3_GOVERNED


# ──────────────────────────────────────────────
# Export tests
# ──────────────────────────────────────────────


class TestExport:
    def test_mermaid_output(self):
        g = _make_graph()
        sub = g.subgraph("kstar-loop", depth=1)
        output = to_mermaid(sub, title="Test Graph")
        assert "graph LR" in output
        assert "kstar_loop" in output

    def test_json_output(self):
        g = _make_graph()
        output = to_json(g)
        import json
        data = json.loads(output)
        assert data["stats"]["total_nodes"] == 5

    def test_ascii_tree(self):
        g = _make_graph()
        tree = to_ascii_tree(g, "kstar-loop", edge_type="requires")
        assert "kstar-planner" in tree
        assert "kstar-observer" in tree


# ──────────────────────────────────────────────
# Engine integration tests
# ──────────────────────────────────────────────


class TestEngine:
    def test_from_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create two skill dirs
            for name in ["skill-a", "skill-b"]:
                d = Path(tmpdir) / name
                d.mkdir()
                (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: test\n---\nBody\n")

            engine = OntologyEngine.from_paths([Path(tmpdir) / "skill-a", Path(tmpdir) / "skill-b"])
            assert len(engine.graph) == 2

    def test_engine_lifecycle(self):
        g = SkillGraph()
        g.add_node(_make_node("s", lifecycle_state=LifecycleState.CANDIDATE))
        engine = OntologyEngine(g)

        result = engine.transition("s", "validated", reason="tested", persist=False)
        assert result["from"] == "candidate"
        assert result["to"] == "validated"

    def test_engine_version_bump(self):
        g = SkillGraph()
        g.add_node(_make_node("s", version="1.0.0"))
        engine = OntologyEngine(g)
        new_v = engine.version_bump("s", "minor", persist=False)
        assert new_v == "1.1.0"

    def test_engine_add_edge(self):
        g = SkillGraph()
        g.add_node(_make_node("a"))
        g.add_node(_make_node("b"))
        engine = OntologyEngine(g)
        edge = engine.add_edge("a", "b", "requires", persist=False)
        assert edge.edge_type == EdgeType.REQUIRES
        assert engine.dependencies("a") == ["b"]

    def test_engine_discover(self):
        g = _make_graph()
        engine = OntologyEngine(g)
        results = engine.discover(domain="agent-architecture", skill_type="meta")
        assert len(results) == 2

    def test_engine_stats(self):
        g = _make_graph()
        engine = OntologyEngine(g)
        s = engine.stats()
        assert s["total_nodes"] == 5

    def test_engine_validate(self):
        g = _make_graph()
        engine = OntologyEngine(g)
        result = engine.validate()
        assert result.is_valid
