"""Semantic versioning and lineage tracking for skills."""

from __future__ import annotations

import re

from neoskills.ontology.models import SkillNode


class VersionError(Exception):
    """Raised for version-related errors."""


_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$")


def parse_semver(version: str) -> tuple[int, int, int, str]:
    """Parse a semver string into (major, minor, patch, prerelease)."""
    m = _SEMVER_RE.match(version)
    if not m:
        raise VersionError(f"Invalid semver: '{version}'")
    return int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4) or ""


def bump_version(node: SkillNode, bump: str = "patch") -> str:
    """Bump a skill's version and update lineage.

    Args:
        node: The skill node to version-bump.
        bump: One of 'major', 'minor', 'patch'.

    Returns:
        The new version string.
    """
    old_version = node.version or "0.1.0"

    try:
        major, minor, patch, _ = parse_semver(old_version)
    except VersionError:
        major, minor, patch = 0, 1, 0

    if bump == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump == "minor":
        minor += 1
        patch = 0
    elif bump == "patch":
        patch += 1
    else:
        raise VersionError(f"Unknown bump type: '{bump}'. Use major/minor/patch.")

    new_version = f"{major}.{minor}.{patch}"

    # Record in lineage
    old_entry = f"{node.skill_id}@{old_version}"
    if old_entry not in node.lineage:
        node.lineage.append(old_entry)

    node.version = new_version
    return new_version


def compare_versions(v1: str, v2: str) -> int:
    """Compare two semver strings. Returns -1, 0, or 1."""
    a = parse_semver(v1)[:3]
    b = parse_semver(v2)[:3]
    if a < b:
        return -1
    elif a > b:
        return 1
    return 0
