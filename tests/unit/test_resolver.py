"""Tests for Resolver — dependency resolution engine."""

import pytest
import yaml

from neoskills.core.cellar import Cellar
from neoskills.core.index import SkillIndex
from neoskills.core.linker import Linker
from neoskills.core.resolver import CyclicDependencyError, Resolver, ResolveResult
from neoskills.core.tap import TapManager


def _make_skill(cellar, skill_id, deps=None, skill_type="regular"):
    """Create a skill directory with SKILL.md and optional metadata.yaml."""
    skill_dir = cellar.tap_skills_dir("mySkills") / skill_id
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {skill_id}\ndescription: Test skill {skill_id}\n---\n\n# {skill_id}\n"
    )
    if deps or skill_type != "regular":
        meta = {"type": skill_type}
        if deps:
            meta["depends_on"] = deps
        (skill_dir / "metadata.yaml").write_text(yaml.dump(meta))
    return skill_dir


@pytest.fixture
def resolver_env(tmp_path):
    cellar = Cellar(root=tmp_path / ".neoskills")
    cellar.initialize()
    cellar.tap_skills_dir("mySkills").mkdir(parents=True)
    target_dir = tmp_path / "claude_skills"
    target_dir.mkdir()
    config = cellar.load_config()
    config["targets"] = {"claude-code": {"skill_path": str(target_dir)}}
    cellar.save_config(config)
    mgr = TapManager(cellar)
    linker = Linker(cellar)
    index = SkillIndex(cellar, mgr)
    resolver = Resolver(index, linker)
    return cellar, mgr, linker, index, resolver


class TestResolveResult:
    def test_ok_when_empty(self):
        result = ResolveResult()
        assert result.ok is True

    def test_not_ok_with_unresolved_skills(self):
        result = ResolveResult(unresolved_skills=["missing"])
        assert result.ok is False

    def test_not_ok_with_unresolved_tools(self):
        result = ResolveResult(unresolved_tools=["missing-tool"])
        assert result.ok is False

    def test_not_ok_with_unresolved_packages(self):
        result = ResolveResult(unresolved_packages=["missing-pkg"])
        assert result.ok is False

    def test_not_ok_with_agent_mismatch(self):
        result = ResolveResult(agent_mismatch="expected agent-x")
        assert result.ok is False


class TestResolverResolve:
    def test_no_deps(self, resolver_env):
        """Single skill with no deps: install_order=[itself], ok=True."""
        cellar, mgr, linker, index, resolver = resolver_env
        _make_skill(cellar, "solo-skill")
        manifest = index.get("solo-skill")
        result = resolver.resolve(manifest, "claude-code")
        assert result.ok is True
        assert len(result.install_order) == 1
        assert result.install_order[0].spec.skill_id == "solo-skill"

    def test_single_dep(self, resolver_env):
        """dep-b depends on dep-a: order has dep-a before dep-b."""
        cellar, mgr, linker, index, resolver = resolver_env
        _make_skill(cellar, "dep-a")
        _make_skill(cellar, "dep-b", deps={"skills": ["dep-a"]})
        manifest = index.get("dep-b")
        result = resolver.resolve(manifest, "claude-code")
        assert result.ok is True
        ids = [m.spec.skill_id for m in result.install_order]
        assert ids.index("dep-a") < ids.index("dep-b")

    def test_transitive_deps(self, resolver_env):
        """base -> middle -> top: order base < middle < top."""
        cellar, mgr, linker, index, resolver = resolver_env
        _make_skill(cellar, "base")
        _make_skill(cellar, "middle", deps={"skills": ["base"]})
        _make_skill(cellar, "top", deps={"skills": ["middle"]})
        manifest = index.get("top")
        result = resolver.resolve(manifest, "claude-code")
        assert result.ok is True
        ids = [m.spec.skill_id for m in result.install_order]
        assert ids.index("base") < ids.index("middle") < ids.index("top")

    def test_unresolved_skill(self, resolver_env):
        """Depends on missing skill: ok=False, unresolved_skills contains it."""
        cellar, mgr, linker, index, resolver = resolver_env
        _make_skill(cellar, "needy", deps={"skills": ["ghost"]})
        manifest = index.get("needy")
        result = resolver.resolve(manifest, "claude-code")
        assert result.ok is False
        assert "ghost" in result.unresolved_skills

    def test_cyclic_dependency(self, resolver_env):
        """a -> b -> a raises CyclicDependencyError."""
        cellar, mgr, linker, index, resolver = resolver_env
        _make_skill(cellar, "cycle-a", deps={"skills": ["cycle-b"]})
        _make_skill(cellar, "cycle-b", deps={"skills": ["cycle-a"]})
        manifest = index.get("cycle-a")
        with pytest.raises(CyclicDependencyError) as exc_info:
            resolver.resolve(manifest, "claude-code")
        assert "cycle-a" in exc_info.value.cycle or "cycle-b" in exc_info.value.cycle

    def test_package_dep_unresolved(self, resolver_env):
        """Depends on nonexistent_pkg_xyz: in unresolved_packages."""
        cellar, mgr, linker, index, resolver = resolver_env
        _make_skill(cellar, "pkg-needy", deps={"packages": ["nonexistent_pkg_xyz"]})
        manifest = index.get("pkg-needy")
        result = resolver.resolve(manifest, "claude-code")
        assert result.ok is False
        assert "nonexistent_pkg_xyz" in result.unresolved_packages


class TestResolverValidate:
    def test_validate_healthy(self, resolver_env):
        """No deps: validate returns []."""
        cellar, mgr, linker, index, resolver = resolver_env
        _make_skill(cellar, "healthy")
        manifest = index.get("healthy")
        issues = resolver.validate(manifest, "claude-code")
        assert issues == []

    def test_validate_missing_dep(self, resolver_env):
        """Depends on ghost: returns DepIssue with kind='missing_skill'."""
        cellar, mgr, linker, index, resolver = resolver_env
        _make_skill(cellar, "broken", deps={"skills": ["ghost"]})
        manifest = index.get("broken")
        issues = resolver.validate(manifest, "claude-code")
        assert len(issues) >= 1
        assert any(i.kind == "missing_skill" and i.detail == "ghost" for i in issues)


class TestResolverCheckAll:
    def test_check_all_no_linked(self, resolver_env):
        """No linked skills: check_all returns []."""
        cellar, mgr, linker, index, resolver = resolver_env
        issues = resolver.check_all("claude-code")
        assert issues == []

    def test_check_all_with_linked_broken_dep(self, resolver_env):
        """Link a skill with missing dep: check_all finds it."""
        cellar, mgr, linker, index, resolver = resolver_env
        skill_dir = _make_skill(cellar, "linked-broken", deps={"skills": ["phantom"]})
        linker.link("linked-broken", skill_dir, "claude-code")
        issues = resolver.check_all("claude-code")
        assert len(issues) >= 1
        assert any(i.kind == "missing_skill" and i.detail == "phantom" for i in issues)
