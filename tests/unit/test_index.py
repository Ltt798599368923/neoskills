"""Tests for SkillIndex — multi-scope skill discovery."""

from pathlib import Path

import pytest

from neoskills.core.cellar import Cellar
from neoskills.core.index import SkillIndex
from neoskills.core.manifest import Scope, SkillType
from neoskills.core.tap import TapManager


@pytest.fixture
def populated_cellar(tmp_path: Path) -> Cellar:
    """Cellar with a tap containing two skills, one with metadata.yaml."""
    cellar = Cellar(root=tmp_path / ".neoskills")
    cellar.initialize()
    tap_skills = cellar.tap_skills_dir("mySkills")
    tap_skills.mkdir(parents=True)

    # Regular skill
    s1 = tap_skills / "git-commit"
    s1.mkdir()
    (s1 / "SKILL.md").write_text(
        "---\nname: git-commit\ndescription: Commit helper\n---\n\n# Git Commit\n"
    )

    # Agent skill with metadata
    s2 = tap_skills / "evaluate-artifact"
    s2.mkdir()
    (s2 / "SKILL.md").write_text(
        "---\nname: evaluate-artifact\ndescription: Evaluate student work\n---\n\n# Eval\n"
    )
    (s2 / "metadata.yaml").write_text(
        "type: agent-skill\ndepends_on:\n  skills:\n    - rubric-builder\n  agent: tutoring-agent\n"
    )

    return cellar


class TestSkillIndex:
    def test_scan_user_skills(self, populated_cellar: Cellar):
        """scan() discovers both skills in the tap."""
        tap_mgr = TapManager(populated_cellar)
        index = SkillIndex(populated_cellar, tap_mgr)
        results = index.scan()
        assert len(results) == 2
        ids = {m.spec.skill_id for m in results}
        assert ids == {"git-commit", "evaluate-artifact"}

    def test_scan_returns_correct_types(self, populated_cellar: Cellar):
        """git-commit is REGULAR, evaluate-artifact is AGENT_SKILL."""
        tap_mgr = TapManager(populated_cellar)
        index = SkillIndex(populated_cellar, tap_mgr)
        results = index.scan()
        by_id = {m.spec.skill_id: m for m in results}
        assert by_id["git-commit"].type is SkillType.REGULAR
        assert by_id["evaluate-artifact"].type is SkillType.AGENT_SKILL

    def test_scan_returns_correct_scope(self, populated_cellar: Cellar):
        """All skills from taps directory should be USER scope."""
        tap_mgr = TapManager(populated_cellar)
        index = SkillIndex(populated_cellar, tap_mgr)
        results = index.scan()
        for m in results:
            assert m.scope is Scope.USER

    def test_get_existing_skill(self, populated_cellar: Cellar):
        """get() finds evaluate-artifact with its dependencies."""
        tap_mgr = TapManager(populated_cellar)
        index = SkillIndex(populated_cellar, tap_mgr)
        manifest = index.get("evaluate-artifact")
        assert manifest is not None
        assert manifest.spec.skill_id == "evaluate-artifact"
        assert manifest.type is SkillType.AGENT_SKILL
        assert "rubric-builder" in manifest.depends_on.skills
        assert manifest.depends_on.agent == "tutoring-agent"

    def test_get_missing_skill(self, populated_cellar: Cellar):
        """get() returns None for a nonexistent skill."""
        tap_mgr = TapManager(populated_cellar)
        index = SkillIndex(populated_cellar, tap_mgr)
        assert index.get("no-such-skill") is None

    def test_search(self, populated_cellar: Cellar):
        """search('evaluate') finds exactly 1 result."""
        tap_mgr = TapManager(populated_cellar)
        index = SkillIndex(populated_cellar, tap_mgr)
        results = index.search("evaluate")
        assert len(results) == 1
        assert results[0].spec.skill_id == "evaluate-artifact"

    def test_search_no_match(self, populated_cellar: Cellar):
        """search() returns [] when nothing matches."""
        tap_mgr = TapManager(populated_cellar)
        index = SkillIndex(populated_cellar, tap_mgr)
        results = index.search("zzz-nonexistent")
        assert results == []

    def test_scan_project_skills(self, populated_cellar: Cellar, tmp_path: Path):
        """scan_project() discovers skills with PROJECT scope."""
        tap_mgr = TapManager(populated_cellar)
        index = SkillIndex(populated_cellar, tap_mgr)

        # Create a project skills directory
        project_skills = tmp_path / "myproject" / "skills"
        project_skills.mkdir(parents=True)
        s = project_skills / "lint-code"
        s.mkdir()
        (s / "SKILL.md").write_text(
            "---\nname: lint-code\ndescription: Lint the code\n---\n\n# Lint\n"
        )

        results = index.scan_project(project_skills)
        assert len(results) == 1
        assert results[0].spec.skill_id == "lint-code"
        assert results[0].scope is Scope.PROJECT

    def test_scan_plugin_skills(self, populated_cellar: Cellar):
        """scan() discovers plugin skills with PLUGIN scope."""
        tap_mgr = TapManager(populated_cellar)
        index = SkillIndex(populated_cellar, tap_mgr)

        # Create a plugin skills directory under the tap
        plugins_dir = populated_cellar.tap_plugins_dir("mySkills")
        plugin_skills = plugins_dir / "my-plugin" / "skills"
        plugin_skills.mkdir(parents=True)
        s = plugin_skills / "plugin-skill"
        s.mkdir()
        (s / "SKILL.md").write_text(
            "---\nname: plugin-skill\ndescription: A plugin skill\n---\n\n# Plugin\n"
        )

        results = index.scan(scopes=[Scope.PLUGIN])
        assert len(results) == 1
        assert results[0].spec.skill_id == "plugin-skill"
        assert results[0].scope is Scope.PLUGIN

    def test_scan_filter_by_scope(self, populated_cellar: Cellar):
        """scan(scopes=[Scope.PROJECT]) returns empty when no project skills exist."""
        tap_mgr = TapManager(populated_cellar)
        index = SkillIndex(populated_cellar, tap_mgr)
        results = index.scan(scopes=[Scope.PROJECT])
        assert results == []
