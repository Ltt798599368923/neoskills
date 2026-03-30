# neoskills

**Cross-Agent Skill Bank & Transfer System**

neoskills manages **skills as the common denominator** across multiple agent ecosystems (Claude Code, OpenCode, OpenClaw). It maintains a canonical, portable master skill bank that you can browse in one place, sync to GitHub, and deploy selectively to different agents via symlinks — like Homebrew for AI skills.

## Features

- **Homebrew-style skill management** — `tap`, `install`, `link`, `update` for skills
- **Tap repositories** — git-cloned skill sources, searchable across all taps
- **Symlink-based deployment** — zero-copy, reversible projection into agent skill directories
- **Multi-agent targets** — Claude Code, OpenCode, OpenClaw, and custom targets
- **Ontology layer** — property graph over skills for discovery, dependency analysis, lifecycle governance, composition, and versioning (v0.4)
- **Claude-powered enhancement** — normalize, audit, enrich ontology metadata
- **Plugin mode** — runs inside Claude Code as an embedded MCP plugin
- **Git sync** — version control your skill bank and push/pull to GitHub

## Installation

```bash
pip install neoskills
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv add neoskills
```

## Quick Start

```bash
# Initialize workspace
neoskills init

# Add a tap (git-hosted skill repository)
neoskills tap https://github.com/your-org/my-skills

# List and search skills across all taps
neoskills list
neoskills search "document processing"

# Link a skill to your agent (creates symlink)
neoskills link wechat-html-converter
neoskills install kstar-loop   # one-step alias

# Check health
neoskills doctor
```

## Architecture

```
~/.neoskills/
├── config.yaml                  # Configuration (targets, taps, defaults)
├── taps/                        # Git-cloned tap repositories
│   ├── mySkills/                # Default tap
│   │   └── skills/
│   │       └── <skill_id>/
│   │           ├── SKILL.md         # Skill definition (frontmatter + body)
│   │           ├── ontology.yaml    # Ontology metadata (optional)
│   │           ├── scripts/         # Executable code (optional)
│   │           ├── references/      # Documentation (optional)
│   │           └── assets/          # Media/templates (optional)
│   └── <other-taps>/
└── cache/                       # Temporary/backup storage
```

Skills are deployed to agents via per-skill symlinks:

```
~/.claude/skills/kstar-loop → ~/.neoskills/taps/mySkills/skills/kstar-loop
```

## Ontology Layer (v0.4)

The ontology layer adds a **property graph** over your skills — nodes (skills, domains, capabilities) and typed edges (requires, extends, composes, conflicts) — all stored as `ontology.yaml` sidecar files alongside SKILL.md. No external database required.

### What it provides

**Discovery** — faceted search by domain, type, lifecycle state, tag, or free text:

```bash
neoskills ontology discover --domain agent-architecture --state operational
neoskills ontology discover --type meta --text "compiler"
```

**Dependency analysis** — what a skill requires and what depends on it:

```bash
neoskills ontology deps kstar-loop --transitive
neoskills ontology rdeps kstar-planner --tree
```

**Lifecycle governance** — track skill maturity through a state machine (candidate → validated → operational → refined → deprecated → archived):

```bash
neoskills ontology lifecycle
neoskills ontology transition my-skill validated --reason "Passed 5 test sessions"
```

**Composition** — compose skills into pipelines, ensembles, or selectors:

```bash
neoskills ontology compose source-text-to-markdown research-md-to-latex --mode pipeline --name md-to-paper
```

**Versioning** — semver bumps with lineage tracking:

```bash
neoskills ontology version kstar-loop --bump minor
```

**Graph visualization** — export as Mermaid, DOT, or JSON:

```bash
neoskills ontology graph kstar-loop --depth 2 --format mermaid
neoskills ontology export --format json --output graph.json
```

**Validation** — detect broken edges, dependency cycles, and asymmetric conflicts:

```bash
neoskills ontology validate
```

### Progressive enrichment

Skills don't need full metadata on day one. The ontology recognizes four levels:

| Level | What's present | How to get there |
|-------|---------------|-----------------|
| **L0 — Bare** | SKILL.md only | Default (all existing skills) |
| **L1 — Tagged** | + ontology.yaml with type, domain, tags | `neoskills ontology enrich <id>` |
| **L2 — Connected** | + explicit edges (requires, extends, ...) | Author declares relationships |
| **L3 — Governed** | + lifecycle state, versioning, capability manifest | Author + system maintain |

```bash
# Preview what would be inferred for all L0 skills
neoskills ontology enrich --all --level L1 --dry-run

# Apply enrichment
neoskills ontology enrich --all --level L1
```

### Domain taxonomy

Skills are classified into a two-level domain hierarchy: agent-architecture (kstar-cognitive, agent-lifecycle, agent-design, agent-memory), education (learning-runtime, curriculum, assessment), document-processing (conversion, academic, wechat, pipeline), business (bidding, planning, strategy), knowledge-work (finance, legal, marketing, sales, data-analysis, ...), and meta (skill-management, understanding, infrastructure).

See [docs/ontology-design.md](docs/ontology-design.md) for the full design document including schema details, composition model, and implementation plan.

## Targets

neoskills ships with built-in targets:

| Target | Agent | Skill Path |
|--------|-------|-----------|
| `claude-code` | Claude Code | `~/.claude/skills` |
| `opencode` | OpenCode | `~/.config/opencode/skills` |

Add custom targets:
```bash
neoskills config set targets.my-server.skill_path /path/to/skills
```

## CLI Reference

### Workspace & Config

| Command | Description |
|---------|-------------|
| `neoskills init` | Create `~/.neoskills/` workspace |
| `neoskills config set\|get\|show` | Configuration management |
| `neoskills doctor` | Health check (symlinks, config, taps) |

### Tap Management

| Command | Description |
|---------|-------------|
| `neoskills tap <url>` | Add a tap (git clone) |
| `neoskills untap <name>` | Remove a tap |
| `neoskills update [name]` | Git pull tap(s) |
| `neoskills upgrade` | Update all taps |

### Skill Discovery & Deployment

| Command | Description |
|---------|-------------|
| `neoskills list [--linked\|--available]` | List skills |
| `neoskills search <query>` | Cross-tap search |
| `neoskills info <skill_id>` | Detailed skill info |
| `neoskills link <skill_id>` | Create symlink (tap → target) |
| `neoskills unlink <skill_id>` | Remove symlink |
| `neoskills install <skill_id>` | One-step link |
| `neoskills uninstall <skill_id>` | Remove installation |
| `neoskills create <skill_id>` | Scaffold a new skill |
| `neoskills push` | Deploy to agent targets |

### Ontology

| Command | Description |
|---------|-------------|
| `neoskills ontology load` | Build graph, print summary |
| `neoskills ontology stats` | Graph statistics (JSON) |
| `neoskills ontology discover` | Faceted search (--domain, --type, --state, --tag, --text) |
| `neoskills ontology deps <id>` | Dependency tree |
| `neoskills ontology rdeps <id>` | Reverse dependency tree |
| `neoskills ontology graph <id>` | Neighborhood graph (Mermaid/DOT/JSON) |
| `neoskills ontology lifecycle` | Skills grouped by lifecycle state |
| `neoskills ontology transition <id> <state>` | Change lifecycle state |
| `neoskills ontology add-edge <src> <tgt> -t <type>` | Add relationship |
| `neoskills ontology remove-edge <src> <tgt> -t <type>` | Remove relationship |
| `neoskills ontology version <id> --bump minor` | Version bump |
| `neoskills ontology compose <ids...> --mode pipeline` | Create composite skill |
| `neoskills ontology split <id> <sub-names...>` | Decomposition plan |
| `neoskills ontology enrich [<id>\|--all]` | Auto-enrich metadata |
| `neoskills ontology validate` | Check graph integrity |
| `neoskills ontology export --format json` | Export full graph |

### Enhancement & Advanced

| Command | Description |
|---------|-------------|
| `neoskills enhance audit\|normalize\|add-docs\|add-tests` | Claude-powered enhancement |
| `neoskills agent list\|run` | Autonomous agent operations |
| `neoskills plugin create\|validate` | Plugin scaffolding/validation |
| `neoskills schedule daily` | Memory-enabled schedule planning |

## Three Operating Modes

1. **External Orchestrator** (default) — CLI runs independently, manages taps, links, and ontology
2. **Agent-invoked Tool** — Claude Code or OpenCode calls neoskills as a tool
3. **Embedded Plugin Mode** — neoskills runs as a Claude Code MCP plugin, exposing 12+ tools including ontology operations

## Authentication

neoskills resolves authentication automatically:

1. **.env API key** — loads from `./`, `.neoskills/`, or `~/.neoskills/.env`
2. **SDK subscription reuse** — works inside Claude Code/Desktop with no API key
3. **Disabled** — non-LLM features still work (tap, link, list, ontology, etc.)

## Documentation

- [Ontology Design Document](docs/ontology-design.md) — full schema, graph engine, lifecycle state machine, composition model, and implementation plan

## Development

```bash
# Clone and install
git clone https://github.com/neolaf2/neoskills
cd neoskills
uv sync --dev

# Run tests
uv run pytest -v

# Lint
uv run ruff check src/

# Run locally
uv run neoskills --help
```

## License

MIT — see [LICENSE](LICENSE)

## Author

Richard Tong
