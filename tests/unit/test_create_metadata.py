"""Test that create command scaffolds ontology.yaml (replaces metadata.yaml)."""
from pathlib import Path
from click.testing import CliRunner
from neoskills.cli.create_cmd import create
from neoskills.core.cellar import Cellar


def test_create_scaffolds_ontology_yaml(tmp_path: Path):
    cellar = Cellar(root=tmp_path / ".neoskills")
    cellar.initialize()
    cellar.tap_skills_dir("mySkills").mkdir(parents=True)

    runner = CliRunner()
    result = runner.invoke(create, ["my-new-skill", "--root", str(cellar.root)])
    assert result.exit_code == 0

    skill_dir = cellar.tap_skills_dir("mySkills") / "my-new-skill"
    assert (skill_dir / "SKILL.md").exists()
    assert (skill_dir / "ontology.yaml").exists()

    import yaml
    onto = yaml.safe_load((skill_dir / "ontology.yaml").read_text())
    assert onto["type"] == "task"
    assert onto["schema_version"] == "1.0"
    assert "lifecycle" in onto


def test_create_no_ontology_skips_yaml(tmp_path: Path):
    cellar = Cellar(root=tmp_path / ".neoskills")
    cellar.initialize()
    cellar.tap_skills_dir("mySkills").mkdir(parents=True)

    runner = CliRunner()
    result = runner.invoke(create, ["legacy-skill", "--no-ontology", "--root", str(cellar.root)])
    assert result.exit_code == 0

    skill_dir = cellar.tap_skills_dir("mySkills") / "legacy-skill"
    assert (skill_dir / "SKILL.md").exists()
    assert not (skill_dir / "ontology.yaml").exists()
