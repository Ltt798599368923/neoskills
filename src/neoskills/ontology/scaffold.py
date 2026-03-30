"""Scaffold ontology.yaml for new skills.

Generates the initial ontology.yaml when `neoskills create` runs,
and provides the full annotated template for reference.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from neoskills.ontology.taxonomy import infer_domain_from_skill_id


# Directory containing template files
_TEMPLATES_DIR = Path(__file__).parent / "templates"


def scaffold_ontology_yaml(
    skill_id: str,
    skill_type: str = "task",
    domain: list[str] | None = None,
    tags: list[str] | None = None,
    version: str = "0.1.0",
) -> str:
    """Generate a minimal ontology.yaml for a new skill.

    Args:
        skill_id: The skill identifier.
        skill_type: One of task, meta, domain, utility, template, composite.
        domain: Domain classification. If None, inferred from skill_id.
        tags: Free-form tags. If None, defaults to empty list.
        version: Initial version string.

    Returns:
        YAML string ready to write to ontology.yaml.
    """
    if domain is None:
        domain = infer_domain_from_skill_id(skill_id)

    if tags is None:
        tags = []

    data = {
        "schema_version": "1.0",
        "type": skill_type,
        "domain": domain,
        "lifecycle": {
            "state": "candidate",
            "maturity": "created",
        },
        "version": version,
        "tags": tags,
    }

    header = (
        f"# ontology.yaml — {skill_id}\n"
        f"# Run `neoskills ontology enrich {skill_id}` to auto-populate.\n"
        f"# Full template: src/neoskills/ontology/templates/ontology.yaml.template\n\n"
    )

    return header + yaml.dump(
        data,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )


def scaffold_full_skill(
    skill_dir: Path,
    skill_id: str,
    description: str = "",
    author: str = "",
    tags: list[str] | None = None,
    skill_type: str = "task",
    include_scripts: bool = False,
    include_references: bool = False,
) -> dict[str, Path]:
    """Scaffold a complete skill directory with SKILL.md + ontology.yaml.

    Creates the directory structure:
        <skill_id>/
        ├── SKILL.md
        ├── ontology.yaml
        ├── scripts/          (if include_scripts)
        └── references/       (if include_references)

    Returns:
        Dict mapping file type to created path.
    """
    from neoskills.core.frontmatter import write_frontmatter

    skill_dir.mkdir(parents=True, exist_ok=True)
    created: dict[str, Path] = {}

    # SKILL.md
    fm = {
        "name": skill_id,
        "description": description or f"TODO: describe {skill_id}",
        "author": author,
        "tags": tags or [],
        "targets": ["claude-code"],
    }
    body = f"# {skill_id.replace('-', ' ').title()}\n\nTODO: Add skill content here.\n"
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(write_frontmatter(fm, body), encoding="utf-8")
    created["skill_md"] = skill_md

    # ontology.yaml
    ontology_content = scaffold_ontology_yaml(
        skill_id=skill_id,
        skill_type=skill_type,
        tags=tags,
    )
    ontology_path = skill_dir / "ontology.yaml"
    ontology_path.write_text(ontology_content, encoding="utf-8")
    created["ontology_yaml"] = ontology_path

    # Optional directories
    if include_scripts:
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        (scripts_dir / ".gitkeep").touch()
        created["scripts"] = scripts_dir

    if include_references:
        refs_dir = skill_dir / "references"
        refs_dir.mkdir(exist_ok=True)
        (refs_dir / ".gitkeep").touch()
        created["references"] = refs_dir

    return created


def get_full_template() -> str:
    """Return the full annotated ontology.yaml template as a string."""
    template_path = _TEMPLATES_DIR / "ontology.yaml.template"
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    return "# Template file not found. Run `neoskills create` to scaffold a new skill.\n"
