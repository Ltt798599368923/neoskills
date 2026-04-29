# Neoskills Architecture Overview

## Project Summary
**neoskills** is a Python CLI tool for managing AI agent skills across multiple platforms (Claude Code, OpenCode, and plugins). It provides skill discovery, import, deduplication, embedding, and ontology management.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI Entry Point                          │
│                     (cli/main.py)                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ Commands │  │  Core    │  │ Ontology │  │   Runtime     │  │
│  │  (cli/)  │──│ (core/)  │  │  (/)     │  │  (runtime/)   │  │
│  └──────────┘  └──────────┘  └──────────┘  └───────────────┘  │
│       │              │              │              │           │
│       ▼              ▼              ▼              ▼           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Adapters Layer                        │  │
│  │                  (adapters/)                             │  │
│  │   ┌─────────┐  ┌──────────┐  ┌──────────┐              │  │
│  │   │ Claude  │  │ OpenClaw │  │ OpenCode │              │  │
│  │   └─────────┘  └──────────┘  └──────────┘              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────┐  ┌──────────┐                                    │
│  │ Plugin   │  │Translators│                                    │
│  │ (plugin/)│  │  (/)      │                                    │
│  └──────────┘  └──────────┘                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Module Dependencies

### Core Modules (`src/neoskills/core/`)
| Module | Purpose | Dependencies |
|--------|---------|--------------|
| `config.py` | Configuration management | None (base module) |
| `auth.py` | Authentication handling | config |
| `workspace.py` | Workspace directory management | config |
| `manifest.py` | Skill manifest definitions | models, frontmatter |
| `models.py` | Data models | None |
| `frontmatter.py` | YAML frontmatter parser | None |
| `index.py` | Skill indexing | manifest, models |
| `resolver.py` | Skill resolution | index, manifest |
| `namespace.py` | Namespace management | config |
| `cellar.py` | Skill storage | manifest |
| `checksum.py` | File integrity checking | None |
| `linker.py` | Symlink management | workspace |
| `tap.py` | Tap (source) management | config |
| `mode.py` | Operating mode | config |

### CLI Commands (`src/neoskills/cli/`)
| Command | Purpose | Core Dependencies |
|---------|---------|-------------------|
| `main.py` | CLI entry point | all command modules |
| `list_cmd.py` | List skills | core/index |
| `create_cmd.py` | Create new skill | core/manifest |
| `import_cmd.py` | Import skills | core/resolver |
| `dedup_cmd.py` | Deduplicate skills | core/checksum |
| `embed_cmd.py` | Embed skills | core/linker |
| `doctor_cmd.py` | Health check | core/workspace |
| `config_cmd.py` | Config management | core/config |
| `init_cmd.py` | Initialize workspace | core/workspace |
| `update_cmd.py` | Update skills | core/resolver |
| `push_cmd.py` | Push to remote | core/auth |
| `migrate_cmd.py` | Migration utilities | core/manifest |
| `enhance_cmd.py` | Meta enhancement | meta/enhancer |
| `ontology_cmd.py` | Ontology operations | ontology/export |
| `schedule_cmd.py` | Scheduled tasks | core/config |
| `brew_install_cmd.py` | Brew installation | None |
| `agent_cmd.py` | Agent management | adapters |
| `plugin_cmd.py` | Plugin management | plugin |
| `link_cmd.py` | Link operations | core/linker |

### Ontology System (`src/neoskills/ontology/`)
| Module | Purpose |
|--------|---------|
| `models.py` | Ontology data models |
| `loader.py` | Load ontology from YAML |
| `engine.py` | Ontology processing engine |
| `graph.py` | Dependency graph |
| `taxonomy.py` | Skill classification |
| `versioning.py` | Version management |
| `lifecycle.py` | Skill lifecycle states |
| `composition.py` | Skill composition rules |
| `scaffold.py` | Ont scaffolding |
| `export.py` | Export formats |
| `writer.py` | YAML writer |

### Adapters (`src/neoskills/adapters/`)
| Adapter | Target Platform |
|---------|-----------------|
| `claude/adapter.py` | Claude Code / Claude Desktop |
| `openclaw/adapter.py` | OpenClaw |
| `opencode/adapter.py` | OpenCode |
| `factory.py` | Adapter factory pattern |
| `base.py` | Abstract adapter interface |

---

## Architecture Patterns

### 1. Factory Pattern (Adapters)
```
adapter_factory.get(target) → ClaudeAdapter | OpenClawAdapter | OpenCodeAdapter
```
The factory pattern allows adding new AI platform integrations without modifying existing code.

### 2. Command Pattern (CLI)
Each CLI command is a separate module with a consistent interface, making it easy to add new commands.

### 3. Plugin Architecture
The plugin system allows extending functionality without modifying core code.

---

## Data Flow

```
User Command → CLI Parser → Command Handler → Core Logic → Adapter → Target Platform
                      ↓
                  Ontology Engine (if applicable)
                      ↓
                  Plugin System (if applicable)
```

---

## Entry Points

1. **CLI**: `src/neoskills/cli/main.py` - Main entry point for all user interactions
2. **Core**: `src/neoskills/core/workspace.py` - Workspace initialization
3. **Ontology**: `src/neoskills/ontology/engine.py` - Ontology processing

---

## Key Insights for New Contributors

1. **Start with `cli/main.py`** to understand the command structure
2. **Read `core/config.py`** to understand configuration hierarchy
3. **Study `adapters/base.py`** to understand the adapter interface
4. **The ontology system is the most complex** - start with `ontology/models.py` before diving into the engine
