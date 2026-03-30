"""Runtime dependency verification — best-effort, opt-in."""

from importlib.metadata import distributions
from pathlib import Path

import yaml

from neoskills.core.resolver import DepIssue


def check_deps(skill_dir: Path) -> list[DepIssue]:
    """Read metadata.yaml and verify deps are available.

    Intended to be called by skills or agent runtime at load time.
    Only checks packages (skill-to-skill requires SkillIndex context).
    Returns empty list if no metadata.yaml or no issues found.
    Silently handles malformed YAML.
    """
    meta_file = skill_dir / "metadata.yaml"
    if not meta_file.exists():
        return []

    try:
        meta = yaml.safe_load(meta_file.read_text()) or {}
    except yaml.YAMLError:
        return []

    dep_data = meta.get("depends_on", {})
    if not isinstance(dep_data, dict):
        return []

    issues: list[DepIssue] = []
    skill_id = skill_dir.name

    # Check packages
    installed = {d.metadata["Name"].lower() for d in distributions()}
    for pkg_spec in dep_data.get("packages", []):
        pkg_name = pkg_spec.split(">")[0].split("<")[0].split("=")[0].split("!")[0].strip().lower()
        if pkg_name not in installed:
            issues.append(
                DepIssue(skill_id, "missing_package", f"Package '{pkg_spec}' not installed")
            )

    return issues
