"""SkillIndex — multi-scope skill discovery across user, project, and plugin scopes."""

from pathlib import Path

from neoskills.core.cellar import Cellar
from neoskills.core.manifest import Scope, SkillManifest
from neoskills.core.tap import TapManager


class SkillIndex:
    """Discovers SkillManifests across user, project, and plugin scopes.

    User skills live in ``taps/{tap}/skills/*/``.
    Plugin skills live in ``taps/{tap}/plugins/{plugin}/skills/*/``.
    Project skills live in an arbitrary directory passed to ``scan_project()``.
    """

    def __init__(self, cellar: Cellar, tap_manager: TapManager):
        self.cellar = cellar
        self.tap_manager = tap_manager

    # --- Public API ---

    def scan(self, scopes: list[Scope] | None = None) -> list[SkillManifest]:
        """Scan user and plugin scopes for skills.

        *scopes* defaults to ``[USER, PLUGIN]``.  ``Scope.PROJECT`` is
        accepted but always produces an empty result — use
        :meth:`scan_project` with an explicit directory instead.
        """
        if scopes is None:
            scopes = [Scope.USER, Scope.PLUGIN]

        results: list[SkillManifest] = []
        if Scope.USER in scopes:
            results.extend(self._scan_user_skills())
        if Scope.PLUGIN in scopes:
            results.extend(self._scan_plugin_skills())
        # PROJECT scope intentionally returns nothing here —
        # callers must use scan_project() with an explicit directory.
        return results

    def scan_project(self, project_skills_dir: Path) -> list[SkillManifest]:
        """Scan a project-level skills directory.

        Returns manifests with ``Scope.PROJECT``.
        """
        return self._scan_directory(project_skills_dir, tap_name="")

    def get(self, skill_id: str) -> SkillManifest | None:
        """Find a single skill by ID across user and plugin scopes."""
        for manifest in self.scan():
            if manifest.spec.skill_id == skill_id:
                return manifest
        return None

    def search(self, query: str, scopes: list[Scope] | None = None) -> list[SkillManifest]:
        """Search by name/description/tags, optionally filtered by scope.

        Performs case-insensitive matching against skill_id, name,
        description, and tags.
        """
        query_lower = query.lower()
        results: list[SkillManifest] = []
        for manifest in self.scan(scopes):
            searchable = " ".join(
                [
                    manifest.spec.skill_id,
                    manifest.spec.name,
                    manifest.spec.description,
                    " ".join(manifest.spec.tags),
                ]
            ).lower()
            if query_lower in searchable:
                results.append(manifest)
        return results

    # --- Internal helpers ---

    def _scan_user_skills(self) -> list[SkillManifest]:
        """Iterate all taps and scan ``taps/{name}/skills/*/``."""
        results: list[SkillManifest] = []
        for tap_name in self.tap_manager.list_taps():
            skills_dir = self.cellar.tap_skills_dir(tap_name)
            results.extend(self._scan_directory(skills_dir, tap_name))
        return results

    def _scan_plugin_skills(self) -> list[SkillManifest]:
        """Iterate all taps and scan ``taps/{name}/plugins/{plugin}/skills/*/``."""
        results: list[SkillManifest] = []
        for tap_name in self.tap_manager.list_taps():
            plugins_dir = self.cellar.tap_plugins_dir(tap_name)
            if not plugins_dir.exists():
                continue
            for plugin_dir in sorted(plugins_dir.iterdir()):
                if not plugin_dir.is_dir() or plugin_dir.name.startswith("."):
                    continue
                plugin_skills = plugin_dir / "skills"
                results.extend(self._scan_directory(plugin_skills, tap_name))
        return results

    @staticmethod
    def _scan_directory(skills_dir: Path, tap_name: str) -> list[SkillManifest]:
        """Scan a directory of skill subdirectories.

        Each subdirectory is expected to contain a ``SKILL.md``.
        Malformed skills are silently skipped.
        """
        results: list[SkillManifest] = []
        if not skills_dir.exists():
            return results
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            try:
                manifest = SkillManifest.from_skill_dir(skill_dir, tap_name=tap_name)
                results.append(manifest)
            except Exception:
                pass  # Silently skip malformed skills
        return results
