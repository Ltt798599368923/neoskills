# neoskills v0.3.1 — Specification

**Homebrew-Style Skill Manager for AI Coding Agents**

**Version:** v0.3.1

**Author:** Richard Tong

**License:** MIT

---

## 1. Mission

neoskills v0.3.0 is a **Homebrew-inspired skill manager** that treats AI agent skills as packages. It replaces the deep bank/registry/mappings architecture of v0.2 with a flat, git-native model where:

1. **GitHub repos are taps** — the master copy of your skill library lives in a git repository (e.g. `github.com/neolaf2/mySkills`)
2. **The tap IS the cellar** — the git clone at `~/.neoskills/taps/mySkills/` serves directly as installed skills. No copy step.
3. **Per-skill flat symlinks** connect tap skills to agent targets — `~/.claude/skills/foo → ~/.neoskills/taps/mySkills/skills/foo`
4. **All metadata lives in SKILL.md frontmatter** — no separate metadata.yaml, provenance.yaml, or registry.yaml
5. **Tags replace directories** — `first-party` vs `external` distinguished by YAML tags, not directory structure

---

## 2. Homebrew Analogy Mapping

| Homebrew Concept | neoskills Equivalent |
|------------------|---------------------|
| **Tap** (GitHub repo of formulae) | mySkills GitHub repo |
| **Formula** (package definition) | SKILL.md with YAML frontmatter |
| **Cellar** (installed packages) | `~/.neoskills/taps/mySkills/` (tap IS the cellar) |
| **Linking** (`/usr/local/bin/` symlinks) | `~/.claude/skills/foo →` tap skill |
| **`brew tap`** | `neoskills tap <url>` |
| **`brew install`** | `neoskills install <skill>` |
| **`brew link/unlink`** | `neoskills link/unlink <skill>` |
| **`brew update`** | `neoskills update` (git pull taps) |
| **`brew upgrade`** | `neoskills upgrade` (update + refresh links) |
| **`brew doctor`** | `neoskills doctor` (health check) |
| **`brew list`** | `neoskills list` |
| **`brew search`** | `neoskills search <query>` |
| **`brew info`** | `neoskills info <skill>` |
| **`brew create`** | `neoskills create <skill>` |

### Key differences from Homebrew

- **No central registry.** Homebrew has `homebrew-core` with 6,000+ formulae. neoskills has only personal taps (your own repos) and optional community taps. There is no global package index.
- **Users are often authors.** Many skills are created by the user, not pulled from upstream. This means version tracking, local modifications, and push workflows matter more.
- **Skills are Markdown, not code.** A "formula" is a SKILL.md file with YAML frontmatter and Markdown instructions, not an executable build recipe.

---

## 3. Directory Layouts

### 3.1 mySkills GitHub Repo (the Tap)

```
mySkills/                          # github.com/user/mySkills
├── tap.yaml                       # Tap metadata (name, description, version)
├── skills/
│   ├── agent-factory/             # tags: [first-party]
│   │   ├── SKILL.md
│   │   ├── scripts/
│   │   └── references/
│   ├── remotion/                  # tags: [external, video]
│   │   └── SKILL.md
│   └── ...                        # 100 skills
├── plugins/                       # Plugin repos (future)
│   └── my-plugin/
│       ├── .claude-plugin/plugin.json
│       └── skills/
└── README.md
```

`tap.yaml`:
```yaml
name: mySkills
description: "Personal skill & plugin library"
version: "1.0.0"
```

### 3.2 ~/.neoskills/ (Workspace)

```
~/.neoskills/
├── config.yaml                    # Taps, targets, auth
├── taps/
│   ├── mySkills/                  # git clone (THE cellar)
│   │   ├── tap.yaml
│   │   ├── skills/
│   │   │   ├── agent-factory/
│   │   │   ├── remotion/
│   │   │   └── ... (100 skills)
│   │   └── plugins/
│   └── community/                 # Other taps (optional)
│       └── ...
├── cache/                         # Ephemeral (backups, scratch)
└── .gitignore
```

**Removed from v0.2:** `LTM/`, `STM/`, `bank/`, `registry.yaml`, `state.yaml`, `mappings/targets/*.yaml`

### 3.3 Agent Targets (Symlinks)

```
~/.claude/skills/
  agent-factory → /Users/rich/.neoskills/taps/mySkills/skills/agent-factory
  remotion → /Users/rich/.neoskills/taps/mySkills/skills/remotion
  unmanaged-skill/           # Not managed by neoskills — left alone
    SKILL.md

~/.config/opencode/skills/
  agent-factory → /Users/rich/.neoskills/taps/mySkills/skills/agent-factory
```

Each skill gets its own symlink. Non-symlink (local) skills are left untouched.

---

## 4. SKILL.md Frontmatter Schema

All metadata in one file — replaces the v0.2 trifecta of SKILL.md + metadata.yaml + provenance.yaml:

```yaml
---
name: agent-factory
description: "Guided workflow for creating custom agents"
version: "1.2.0"
author: "Richard Tong"
tags: [first-party, agents, p3394]
targets: [claude-code, opencode]
source: mySkills
tools: [Bash, Read, Write]
model: inherit
---

# Agent Factory

Skill body (Markdown instructions)...
```

### Field reference

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Skill identifier (matches directory name) |
| `description` | Yes | What the skill does and when to use it |
| `version` | No | Semantic version |
| `author` | No | Creator name |
| `tags` | No | Classification tags (includes `first-party` or `external`) |
| `targets` | No | Which agents this skill supports |
| `source` | No | Which tap it came from |
| `tools` | No | Tools the skill needs |
| `model` | No | Model requirement (`inherit`, `sonnet`, `opus`, `haiku`) |

---

## 5. config.yaml Schema

```yaml
version: "0.3.0"

default_tap: mySkills
default_target: claude-code

targets:
  claude-code:
    skill_path: "~/.claude/skills"
  opencode:
    skill_path: "~/.config/opencode/skills"

taps:
  mySkills:
    url: "https://github.com/neolaf2/mySkills"
    branch: main
    default: true
  community:
    url: "https://github.com/org/community-skills"
    branch: main

auth:
  mode: auto
```

---

## 6. CLI Commands

### 6.1 Tap Management

| Command | Description |
|---------|-------------|
| `neoskills tap <url> [--name N]` | Clone a tap repo to `~/.neoskills/taps/` |
| `neoskills untap <name>` | Remove a tap and unregister it |
| `neoskills update [tap]` | `git pull` all (or one) tap |

### 6.2 Skill Lifecycle

| Command | Description |
|---------|-------------|
| `neoskills install <skill> [--from TAP]` | Copy skill to default tap (if from another) + link |
| `neoskills uninstall <skill>` | Unlink + optionally remove from tap |
| `neoskills upgrade [skill]` | Update taps + refresh/verify symlinks |
| `neoskills create <skill>` | Scaffold new skill in default tap |

### 6.3 Link Management

| Command | Description |
|---------|-------------|
| `neoskills link <skill> [--target T] [--all]` | Create symlink(s) from tap skill to target |
| `neoskills unlink <skill> [--target T] [--all]` | Remove symlink(s) from target |

### 6.4 Discovery & Information

| Command | Description |
|---------|-------------|
| `neoskills list [--linked\|--available]` | Show skills (all, linked only, or available only) |
| `neoskills search <query>` | Search across all taps by name/description/tags |
| `neoskills info <skill>` | Show frontmatter, path, and link status |
| `neoskills doctor` | Health check: broken links, missing descriptions, orphans |

### 6.5 Git Operations

| Command | Description |
|---------|-------------|
| `neoskills push [--tap T] [-m MSG]` | Git commit + push tap changes |

### 6.6 Configuration & Setup

| Command | Description |
|---------|-------------|
| `neoskills init [--root PATH]` | Initialize `~/.neoskills/` workspace |
| `neoskills config set KEY VALUE` | Set a config value |
| `neoskills config get KEY` | Get a config value |
| `neoskills config show` | Show all configuration |
| `neoskills migrate [--dry-run]` | One-time migration from v0.2 structure |

### 6.7 Kept from v0.2

| Command | Description |
|---------|-------------|
| `neoskills enhance OPERATION --skill ID` | AI-powered skill enhancement |
| `neoskills agent` | Agent discovery and execution |
| `neoskills plugin` | Plugin creation and validation |

### 6.8 Removed from v0.2

| Old Command | Replaced By |
|-------------|-------------|
| `embed` / `unembed` | `link` / `unlink` |
| `import from-target/from-git/from-web` | `install --from` |
| `sync status/commit/push/pull` | `update` + `push` |
| `deploy skill/bundle` | `install` + `link` |
| `scan` | `list` |
| `validate` | `doctor` |
| `target list/add` | `config` (targets in config.yaml) |

---

## 7. Core Architecture

### 7.1 Class Diagram

```
Cellar                          TapManager                     Linker
  ├── root: Path                  ├── cellar: Cellar            ├── cellar: Cellar
  ├── taps_dir                    ├── add(name, url)            ├── link(id, source, target)
  ├── cache_dir                   ├── remove(name)              ├── unlink(id, target)
  ├── config_file                 ├── update(name?)             ├── link_all(dir, target)
  ├── default_tap                 ├── list_taps()               ├── unlink_all(target)
  ├── load_config()               ├── list_skills(tap)          ├── list_links(target)
  ├── save_config()               ├── get_skill_path(id)        ├── check_health(target)
  ├── target_path(target)         └── search(query)             └───────────────────
  └── initialize()

SkillSpec (dataclass)
  ├── skill_id, name, description, version, author
  ├── tags, targets, source, tools, model, tap, path
  └── from_skill_dir(path, tap_name) → SkillSpec
```

### 7.2 Cellar (`core/cellar.py`)

Manages the `~/.neoskills/` directory tree. Replaces the v0.2 `Workspace` class.

- **No LTM/STM hierarchy.** Just `root/`, `taps/`, `cache/`, `config.yaml`.
- **Config is flat YAML.** No layered config hierarchy needed for the simplified model.
- **`target_path(target)`** resolves a target name to its skill directory (e.g. `claude-code` → `~/.claude/skills`).

### 7.3 TapManager (`core/tap.py`)

Manages tap repositories (git clones under `~/.neoskills/taps/`).

- **`add(name, url)`** — `git clone --depth 1` to `taps/{name}/`, register in config.
- **`remove(name)`** — `rm -rf taps/{name}/`, unregister from config.
- **`update(name?)`** — `git pull` one or all taps.
- **`list_skills(tap)`** — scan `taps/{tap}/skills/*/SKILL.md`, parse frontmatter, return metadata dicts.
- **`get_skill_path(id, tap?)`** — find a skill directory, searching default tap first then all taps.
- **`search(query)`** — case-insensitive search across all taps by name/description/tags.

### 7.4 Linker (`core/linker.py`)

Manages per-skill symlinks from target directories to tap skills.

- **Stateless.** No `state.yaml` — derives all state from filesystem inspection (is it a symlink? does it resolve? does it point into our taps?).
- **`link(id, source, target)`** — create symlink. If a real directory exists at the target, back it up to `cache/backup_{id}/` first.
- **`unlink(id, target)`** — remove symlink.
- **`check_health(target)`** — returns `{total, healthy, broken, unmanaged, local}` counts and details.
- **Managed vs unmanaged:** A symlink is "managed" if it points into `~/.neoskills/taps/`. Symlinks pointing elsewhere are "unmanaged". Non-symlink directories are "local".

### 7.5 SkillSpec (`core/models.py`)

Dataclass representing a skill's metadata, parsed from SKILL.md frontmatter.

- **`from_skill_dir(path, tap_name)`** — class method that reads `SKILL.md`, parses frontmatter, returns a populated `SkillSpec`.
- Fields: `skill_id`, `name`, `description`, `version`, `author`, `tags`, `targets`, `source`, `tools`, `model`, `tap`, `path`.

---

## 8. Command Flow Examples

### 8.1 `neoskills install remotion --from community`

```
1. Find remotion in ~/.neoskills/taps/community/skills/remotion/
2. Copy to ~/.neoskills/taps/mySkills/skills/remotion/
3. Add source: community to frontmatter
4. Create symlink: ~/.claude/skills/remotion → taps/mySkills/skills/remotion
5. Report: "Installed remotion from community tap, linked to claude-code"
```

### 8.2 `neoskills create my-new-skill`

```
1. Create ~/.neoskills/taps/mySkills/skills/my-new-skill/
2. Generate SKILL.md with template frontmatter + TODO body
3. Report path for editing
```

### 8.3 `neoskills update && neoskills upgrade`

```
1. update: git pull all taps
2. upgrade: For each linked skill, verify symlink target still exists
3. Report any changes or broken links
```

### 8.4 `neoskills doctor`

```
1. Check workspace is initialized
2. Count registered taps
3. Count skills in default tap, report missing descriptions
4. Check all symlinks in target — report broken, unmanaged, local
5. Report unlinked tap skills (advisory)
6. Summary: "N issue(s) found" or "System is healthy"
```

### 8.5 `neoskills push`

```
1. Check for changes in default tap repo (git status)
2. Stage existing paths only (skills/, plugins/, tap.yaml, README.md — skips missing)
3. Commit with message (default or -m flag)
4. Push to origin
5. Report success or "committed locally" if push fails
```

> **v0.3.1 fix:** The push command now gracefully skips non-existent paths (e.g. `plugins/`) instead of crashing with `fatal: pathspec did not match`.

---

## 9. Migration from v0.2

The `neoskills migrate` command performs a one-time conversion:

### What it does

1. **Creates new directory structure** — `taps/mySkills/skills/`, `cache/`
2. **Creates `tap.yaml`** in the new tap directory
3. **For each skill in `LTM/bank/skills/{id}/canonical/`:**
   - Copies contents to `taps/mySkills/skills/{id}/`
   - Merges `metadata.yaml` fields into SKILL.md frontmatter (version, author, tags)
   - Merges `provenance.yaml` source info into frontmatter
   - Drops the `canonical/` nesting, `variants/`, and separate YAML files
4. **Updates `config.yaml`** to v0.3.0 format (adds taps, targets sections)
5. **Re-creates symlinks** — flat per-skill symlinks pointing to the new tap locations

### What it does NOT do

- Does **not** delete the old `LTM/bank/` structure (left for archival)
- Does **not** require a GitHub remote (works with local-only taps)
- Supports `--dry-run` for preview without changes

### Migration stats (actual)

- 100 skills migrated, 0 skipped
- 100 symlinks created, all healthy
- 4 skills initially had missing descriptions (fixed in v0.3.1)

### Post-migration frontmatter fixes (v0.3.1)

Four skills had malformed YAML frontmatter after migration:

| Skill | Issue | Fix |
|-------|-------|-----|
| `canvas` | Missing `name` and `description` entirely | Added fields to frontmatter |
| `discord` | Dual frontmatter blocks (parser only reads first) | Merged into single block |
| `food-order` | Dual frontmatter blocks + unquoted colons in description | Merged blocks, quoted description |
| `paper-draft-stitcher` | Dual frontmatter blocks + unquoted colons in description | Merged blocks, quoted description |

**Root cause:** Some skills had two `---` YAML blocks. The `parse_frontmatter()` function finds the first closing `---` delimiter, so only the first block was parsed. The first block contained `version`/`author`/`tags` but not `name`/`description`. Additionally, descriptions containing colons (e.g. `discord tool: send messages`) caused `yaml.ScannerError` because YAML interprets unquoted colons as key-value separators. The error was silently caught, returning empty metadata.

**Lesson:** Always quote YAML string values that contain colons.

---

## 10. Modules Removed from v0.2

| Module | Files | Reason |
|--------|-------|--------|
| `bank/` | store.py, registry.py, provenance.py, validator.py | Skills live in taps — no bank layer |
| `mappings/` | resolver.py, target.py | Replaced by Linker + config.yaml targets |
| `bundles/` | manager.py | Bundles not needed in tap model |
| `capabilities/` | discover.py, lifecycle.py, evolution.py, registry_ops.py, governance.py | Replaced by direct core class usage |
| Old CLI | embed, import, sync, deploy, scan, validate, target, install (old) | Replaced by Brew-style commands |

### Net code change

- **+2,768 lines** (new core + CLI + tests)
- **-3,580 lines** (deleted old infrastructure)
- **Net: -812 lines** (simpler overall)

---

## 11. Modules Kept from v0.2

| Module | Purpose |
|--------|---------|
| `core/workspace.py` | Legacy class, still importable but unused by new code |
| `core/config.py` | `Config` and `ConfigHierarchy` classes |
| `core/frontmatter.py` | `parse_frontmatter()`, `write_frontmatter()`, `extract_skill_name()` |
| `core/checksum.py` | `checksum_string()`, `checksum_file()`, `checksum_directory()` |
| `core/mode.py` | `ExecutionMode`, `detect_mode()` |
| `core/namespace.py` | `NamespaceManager` for plugin mode |
| `meta/enhancer.py` | AI-powered skill enhancement |
| `adapters/` | Agent type adapters (discover, export, install) |
| `runtime/claude/plugin.py` | MCP tool exposure (rewritten for v0.3) |
| `cli/agent_cmd.py` | Agent discovery and execution |
| `cli/plugin_cmd.py` | Plugin creation and validation |
| `cli/enhance_cmd.py` | AI enhancement (rewritten for v0.3) |

---

## 12. Testing

### Test suite

- **79 tests** total (78 unit + 1 integration)
- **test_linker.py** — 17 tests: link, unlink, link_all, unlink_all, list_links, check_health
- **test_tap.py** — 13 tests: list_taps, list_skills, get_skill_path, search, remove
- **test_core.py** — 18 tests: frontmatter, checksum, config, cellar, skillspec
- **test_config_hierarchy.py** — 8 tests: config layering, backward compat, init validation
- **test_cli.py** — 4 tests: version, help, init, config
- **test_mode.py** — 11 tests: execution mode, namespace, plugin context
- **test_e2e.py** — 1 test: full workflow (init → create tap → add skill → link → doctor → unlink)

### Running tests

```bash
uv run pytest              # All tests
uv run pytest tests/unit   # Unit only
uv run pytest -v           # Verbose
```

---

## 13. Dependencies

```toml
[project]
requires-python = ">=3.13"
dependencies = [
    "pyyaml>=6.0",
    "jinja2>=3.1",
    "rich>=13.0",
    "click>=8.1",
    "gitpython>=3.1",
    "python-dotenv>=1.0",
]
```

---

## 14. Workflow Discipline

### The Golden Rule

**Always create the master copy in the mySkills GitHub repo first, then install locally from there.**

Whether a skill comes from:
- Claude Code's built-in skill creator
- A community repository
- Manual authoring
- An agent-created skill

The discipline is:
1. Create/edit the skill in `~/.neoskills/taps/mySkills/skills/{id}/`
2. Test it locally (it's already linked via symlink)
3. Run `neoskills push` to commit and push to GitHub
4. Full history, PRs, and README management via GitHub

### Two-track skill management

| Track | Description | Tag |
|-------|-------------|-----|
| **First-party** | Skills you created or significantly customized | `first-party` |
| **External** | Skills consumed from other sources with minimal modification | `external` |

Both live in the same `skills/` directory, distinguished only by tags — no separate directories.

### Plugin management

Plugins follow the same model:
- Stored in `taps/mySkills/plugins/`
- Each plugin is a subdirectory with `.claude-plugin/plugin.json`
- Two tracks: externally consumed vs first-party developed

---

## 15. Future Considerations

- **Multi-target linking:** Link the same skill to multiple targets in one command
- **Tap indexing:** Generate `cache/index.json` for faster search across large taps
- **Remote search:** Search community taps without cloning them first
- **Skill dependencies:** Declare that skill A requires skill B
- **Plugin tap support:** Full lifecycle for plugins within taps (beyond skills)
- **Version pinning:** Pin skills to specific versions/commits within a tap

---

## 16. Changelog

### v0.3.1

- **Fix:** `neoskills push` no longer crashes when `plugins/` directory doesn't exist in a tap. Skips non-existent paths gracefully.
- **Fix:** Repaired 4 skills with missing descriptions caused by dual YAML frontmatter blocks and unquoted colons in description values.

### v0.3.0

- **Major refactor:** Replaced deep `LTM/bank/skills/{id}/canonical/` hierarchy with Homebrew-inspired tap/cellar/link model.
- **New core classes:** `Cellar`, `TapManager`, `Linker`, `SkillSpec` replace `SkillStore`, `Registry`, `SymlinkResolver`, `TargetManager`.
- **New CLI commands:** `tap`, `untap`, `update`, `install`, `uninstall`, `link`, `unlink`, `upgrade`, `list`, `search`, `info`, `doctor`, `create`, `push`, `migrate`.
- **Removed:** `bank/`, `mappings/`, `bundles/`, `capabilities/` modules and 7 old CLI commands.
- **Net -812 lines** of code (simpler overall).
- **Migration:** `neoskills migrate` converts v0.2 structure to v0.3 in-place.

---

## 17. Quick Reference Card

```bash
# Setup
neoskills init                    # Initialize workspace
neoskills tap <url>               # Add a skill repo

# Daily workflow
neoskills create my-skill         # Scaffold new skill
neoskills link my-skill           # Symlink to agent
neoskills list --linked           # See what's active
neoskills search "keyword"        # Find skills
neoskills info my-skill           # Skill details

# Maintenance
neoskills doctor                  # Health check
neoskills update                  # Pull latest from taps
neoskills upgrade                 # Update + refresh links
neoskills push -m "Add new skill" # Commit + push to GitHub

# Install from other taps
neoskills install cool-skill --from community
neoskills uninstall old-skill
```
