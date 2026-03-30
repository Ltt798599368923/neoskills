# TASKS — Neoskills Ontology Handoff

**Date:** 2026-03-30
**Context:** Cowork session built the full v0.4 ontology layer. Claude Code should pick up from here.

---

## BLOCKING: Resolve Git Rebase Conflict

**Status:** IN PROGRESS — user ran `git pull --rebase origin main` and hit a conflict.

**File:** `src/neoskills/cli/create_cmd.py`

**What happened:**
- Remote `main` had a commit adding `metadata.yaml` generation (with `type: "regular"` and `depends_on: {skills: [], tools: [], agent: None, packages: []}`)
- Our commit `d1d91f1` replaces the entire `create` command to use the new ontology scaffold (`scaffold_full_skill()`)
- Git couldn't auto-merge — conflict markers are in the file

**Resolution (our version wins):**
The ontology scaffold (`ontology.yaml`) supersedes `metadata.yaml`. Our version already covers dependency tracking via `edges.requires`, plus type, lifecycle, versioning, and capability manifest.

**Steps:**
```bash
# The resolved file content was already written in the Cowork session.
# If conflict markers are still present, keep ONLY our version (the ontology scaffold block).
# Then:
git add src/neoskills/cli/create_cmd.py
git rebase --continue
git push origin main
```

**Resolved `create_cmd.py` should have:**
- Click options: `--type`, `--scripts`, `--references`, `--no-ontology`
- `--no-ontology` path: legacy SKILL.md-only creation
- Default path: calls `scaffold_full_skill()` from `neoskills.ontology.scaffold`
- Shows inferred domain and next-step hint

---

## TODO: Verify All Tests Pass

```bash
uv sync --dev
uv run pytest -v
```

Expected: 47+ tests across 9 test classes in `tests/unit/test_ontology.py` plus existing tests in `test_cli.py`, `test_core.py`, etc.

**Known issue:** `pyproject.toml` requires Python ≥3.13. Make sure the environment has 3.13+.

---

## TODO: Lint Check

```bash
uv run ruff check src/
```

Fix any issues, especially in the new `src/neoskills/ontology/` module.

---

## TODO: Integration Smoke Test

```bash
# CLI entry points
uv run neoskills --help
uv run neoskills ontology --help
uv run neoskills ontology load
uv run neoskills ontology stats
uv run neoskills ontology validate

# Scaffold a test skill
uv run neoskills create test-smoke -d "Smoke test" --type task
ls ~/.neoskills/taps/mySkills/skills/test-smoke/
cat ~/.neoskills/taps/mySkills/skills/test-smoke/ontology.yaml

# Enrich and discover
uv run neoskills ontology enrich test-smoke
uv run neoskills ontology discover --domain education

# Clean up
rm -rf ~/.neoskills/taps/mySkills/skills/test-smoke
```

---

## TODO: PyPI Release (v0.4.0)

Once tests pass and the rebase is resolved:
1. Bump version in `pyproject.toml` if not already `0.4.0`
2. `uv build`
3. `uv run twine upload dist/*`
4. Verify: `pip install --upgrade neoskills && neoskills ontology --help`

---

## FUTURE: Post-v0.4 Enhancements

These are design decisions made but not yet implemented:

1. **Graph persistence cache** — serialize the in-memory graph to `.neoskills/cache/graph.json` to avoid full filesystem walk on every `ontology load`. Invalidate on mtime changes.

2. **`neoskills ontology enrich-all`** — batch enrichment across all skills. The CLI command exists but needs real-world testing with 110+ skills.

3. **Composition runtime** — `compose` creates a `CompositionSpec` but there's no executor that actually chains skills at runtime. This would integrate with the KSTAR loop or agent runtime.

4. **MCP plugin tools** — 7 tools added to `src/neoskills/runtime/claude/plugin.py` (`neoskills_ontology_discover`, `_deps`, `_graph`, `_transition`, `_add_edge`, `_version`, `_stats`). Need testing inside an actual Claude Code plugin session.

5. **Ontology-aware `neoskills search`** — current search is substring-only. Could enhance with graph-backed faceted search using the ontology indexes.

6. **Export formats** — `to_mermaid`, `to_dot`, `to_json`, `to_ascii_tree` exist in `export.py`. Could add `to_cytoscape` for web visualization.

---

## Design Decisions Log

| Decision | Rationale |
|----------|-----------|
| `ontology.yaml` as sidecar (not embedded in SKILL.md) | Keeps SKILL.md human-readable; ontology can evolve independently; excluded from intrinsic checksums |
| Progressive enrichment L0→L3 | Backward compatible — bare SKILL.md still works (L0); ontology is additive |
| In-memory graph, no external DB | File-system-as-database philosophy; graph materializes from YAML at runtime |
| Inverted indexes in SkillGraph | O(1) faceted lookup by domain/type/state/tag/namespace/enrichment |
| Two-level domain taxonomy | Flat enough to be useful, deep enough for organization; defined in `taxonomy.py` |
| `metadata.yaml` superseded by `ontology.yaml` | Ontology covers everything metadata.yaml had (type, depends_on) plus lifecycle, versioning, composition |
| Templates live in `src/neoskills/ontology/templates/` | Co-located with scaffold code; `ontology.yaml.template` (full annotated) + `ontology-minimal.yaml.template` (for auto-generation) |
| Lifecycle state machine with `valid_transitions` | Prevents invalid state jumps; auditable via `LifecycleEvent` history |
| Homebrew tap/install/link model preserved | Ontology layer sits above Cellar/Brew; doesn't change the deployment model |

---

## File Map — New/Modified in This Session

### New files (ontology layer):
```
src/neoskills/ontology/
├── __init__.py          # Package exports
├── models.py            # Enums, dataclasses (SkillNode, OntologyEdge, etc.)
├── graph.py             # SkillGraph — in-memory property graph
├── loader.py            # OntologyLoader — filesystem → graph
├── writer.py            # OntologyWriter — graph → filesystem
├── engine.py            # OntologyEngine — high-level API
├── taxonomy.py          # Domain taxonomy + inference heuristics
├── lifecycle.py         # State machine transitions
├── versioning.py        # Semver parsing, bumping, lineage
├── composition.py       # Compose/decompose skills
├── export.py            # Mermaid, DOT, JSON, ASCII tree
├── scaffold.py          # scaffold_ontology_yaml, scaffold_full_skill
└── templates/
    ├── ontology.yaml.template          # Full annotated reference
    └── ontology-minimal.yaml.template  # Minimal for auto-generation
```

### New files (CLI + tests + docs):
```
src/neoskills/cli/ontology_cmd.py   # 15+ Click subcommands
tests/unit/test_ontology.py         # 47 tests, 9 test classes
docs/ontology-design.md             # Full design document
```

### Modified files:
```
src/neoskills/cli/create_cmd.py     # Ontology scaffold integration (CONFLICT — see above)
src/neoskills/cli/main.py           # Added ontology + schedule to command registry
src/neoskills/core/checksum.py      # ontology.yaml added to _SKIP_NAMES
src/neoskills/runtime/claude/plugin.py  # 7 MCP tools for ontology
README.md                           # Full rewrite for v0.3 + v0.4
pyproject.toml                      # Version bump to 0.4.0
```
