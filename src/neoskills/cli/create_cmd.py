"""CLI command: create — scaffold a new skill in the default tap."""

import click

from neoskills.core.cellar import Cellar


@click.command()
@click.argument("skill_id")
@click.option("--description", "-d", default="", help="Skill description.")
@click.option("--author", "-a", default="", help="Author name.")
@click.option("--tags", "-t", default="first-party", help="Comma-separated tags.")
@click.option(
    "--type",
    "skill_type",
    default="task",
    type=click.Choice(["task", "meta", "domain", "utility", "template", "composite"]),
    help="Skill type for ontology classification.",
)
@click.option("--scripts", is_flag=True, help="Create scripts/ directory.")
@click.option("--references", is_flag=True, help="Create references/ directory.")
@click.option("--no-ontology", is_flag=True, help="Skip ontology.yaml generation.")
@click.option("--root", default=None, type=click.Path(), help="Workspace root.")
def create(
    skill_id: str,
    description: str,
    author: str,
    tags: str,
    skill_type: str,
    scripts: bool,
    references: bool,
    no_ontology: bool,
    root: str | None,
) -> None:
    """Scaffold a new skill in the default tap.

    Creates SKILL.md and ontology.yaml with sensible defaults.
    The ontology layer auto-infers domain from the skill name.
    """
    from pathlib import Path

    cellar = Cellar(Path(root) if root else None)
    skill_dir = cellar.default_tap_skills_dir / skill_id

    if skill_dir.exists():
        click.echo(f"Skill '{skill_id}' already exists at {skill_dir}")
        raise SystemExit(1)

    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    if no_ontology:
        # Legacy behavior: SKILL.md only
        from neoskills.core.frontmatter import write_frontmatter

        skill_dir.mkdir(parents=True)
        fm = {
            "name": skill_id,
            "description": description or f"TODO: describe {skill_id}",
            "author": author,
            "tags": tag_list,
            "targets": ["claude-code"],
        }
        body = f"# {skill_id.replace('-', ' ').title()}\n\nTODO: Add skill content here.\n"
        (skill_dir / "SKILL.md").write_text(write_frontmatter(fm, body))
        click.echo(f"Created {skill_id} at {skill_dir}")
        click.echo(f"  Edit: {skill_dir / 'SKILL.md'}")
    else:
        # Full scaffold: SKILL.md + ontology.yaml
        from neoskills.ontology.scaffold import scaffold_full_skill

        created = scaffold_full_skill(
            skill_dir=skill_dir,
            skill_id=skill_id,
            description=description,
            author=author,
            tags=tag_list,
            skill_type=skill_type,
            include_scripts=scripts,
            include_references=references,
        )

        click.echo(f"Created {skill_id} at {skill_dir}")
        for file_type, path in created.items():
            click.echo(f"  {file_type}: {path}")

        # Show inferred domain
        from neoskills.ontology.taxonomy import infer_domain_from_skill_id

        inferred = infer_domain_from_skill_id(skill_id)
        click.echo(f"  Inferred domain: {', '.join(inferred)}")
        click.echo(f"\n  Next: edit SKILL.md, then run `neoskills ontology enrich {skill_id}`")
