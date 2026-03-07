"""Test that create command scaffolds metadata.yaml."""
from pathlib import Path
from click.testing import CliRunner
from neoskills.cli.create_cmd import create
from neoskills.core.cellar import Cellar


def test_create_scaffolds_metadata_yaml(tmp_path: Path):
    cellar = Cellar(root=tmp_path / ".neoskills")
    cellar.initialize()
    cellar.tap_skills_dir("mySkills").mkdir(parents=True)

    runner = CliRunner()
    result = runner.invoke(create, ["my-new-skill", "--root", str(cellar.root)])
    assert result.exit_code == 0

    skill_dir = cellar.tap_skills_dir("mySkills") / "my-new-skill"
    assert (skill_dir / "SKILL.md").exists()
    assert (skill_dir / "metadata.yaml").exists()

    import yaml
    meta = yaml.safe_load((skill_dir / "metadata.yaml").read_text())
    assert meta["type"] == "regular"
    assert "depends_on" in meta
    assert meta["depends_on"]["skills"] == []
