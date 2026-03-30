# Neoskills Ontology Layer — Refactor Design Document

**Author:** Richard Tong
**Date:** 2026-03-30
**Version:** 0.4.0-design
**Status:** Draft
**Repo:** `neoskills/` (extends v0.3.0 Cellar/Brew architecture)

---

## 1. Problem Statement

Neoskills v0.3 manages ~110+ skills across three source locations (local `~/.claude/skills`, installed plugins via `.local-plugins`, remote plugins via `.remote-plugins`) plus tap repositories. Today these skills are **flat bags of files** — each is a directory with a SKILL.md and optional supporting files. There is:

- **No shared vocabulary** for what a skill *is* (type, domain, layer, maturity).
- **No dependency graph** — skills reference each other in prose ("integrates with kstar-loop") but nothing is indexed or queryable.
- **No lifecycle tracking** — skills have no maturity state, no version lineage, no deprecation path.
- **No composability model** — no formal way to say "these three skills compose into a pipeline" or "this skill extends that one."
- **No discovery beyond text search** — `neoskills search` does substring matching on name/description/tags; there is no faceted browsing, semantic retrieval, or graph traversal.

The single exception — `kstar-episode-compiler/manifest.json` — demonstrates what rich metadata *could* look like (lifecycle, integrations, capability manifest, domain applicability). But it's a one-off; no infrastructure consumes it.

### What We Want

An **ontology layer** that sits between the file-system storage (Cellar/taps) and the CLI/API surface, providing:

1. **A property graph of skills** — nodes (skills, domains, capabilities, agents) and typed edges (requires, extends, composes, conflicts, targets).
2. **Lifecycle governance** — every skill has a maturity state machine; transitions are auditable.
3. **Composability primitives** — compose skills into pipelines; decompose monolithic skills into focused units.
4. **File-system native storage** — the graph is materialized from sidecar YAML files at runtime; no external DB required.
5. **Backward compatibility** — skills with only a SKILL.md still work; the ontology layer infers what it can and flags what's missing.

---

## 2. Design Principles

### 2.1 File System as Source of Truth

The ontology does **not** introduce a database. Every piece of ontology data lives as a YAML sidecar file (`ontology.yaml`) inside the skill directory, next to SKILL.md. The in-memory property graph is **materialized on load** by walking the file system and parsing these sidecars.

**Analogy:** Think of it like Git's object model — the `.git/` directory IS the database, and tools like `git log` materialize views from it at query time. Similarly, the skill directories ARE the ontology; the graph engine just reads them.

### 2.2 Progressive Enrichment

Skills are not required to have full ontology metadata on day one. The system defines four **enrichment levels**:

| Level | What's Present | Auto-Inferrable? |
|-------|---------------|-----------------|
| **L0 — Bare** | SKILL.md with name + description only | Yes (most current skills) |
| **L1 — Tagged** | L0 + `ontology.yaml` with type, domain, tags | Partially (Claude can infer) |
| **L2 — Connected** | L1 + explicit edges (requires, extends, composes) | No (author declares) |
| **L3 — Governed** | L2 + lifecycle state, version lineage, capability manifest | No (author + system maintain) |

The `neoskills enhance` command (Claude-powered) can auto-promote L0 → L1 by analyzing SKILL.md content.

### 2.3 Convention over Configuration

Default behaviors are derived from conventions:

- **Skill type** defaults to `task` (the most common).
- **Domain** defaults to `general` if not specified.
- **Lifecycle state** defaults to `candidate` for newly created skills.
- **Version** defaults to `0.1.0`.

### 2.4 Graph Operations as First-Class

The ontology supports six graph operations (inspired by your KSTAR skill analyzer's structural plasticity model):

| Operation | Meaning |
|-----------|---------|
| **attach** | Add an edge between two skill nodes |
| **merge** | Combine two skills into one (with provenance) |
| **split** | Decompose a skill into focused sub-skills |
| **lift** | Generalize a concrete skill into a parameterized template |
| **ground** | Instantiate a template skill with specific parameters |
| **prune** | Remove deprecated/dead skills and their edges |

---

## 3. Ontology Schema

### 3.1 Node Types

```
SkillNode          — An individual skill (primary entity)
DomainNode         — A knowledge/application domain
CapabilityNode     — An abstract capability a skill provides
BundleNode         — A named collection of skills
AgentNode          — A deployment target / agent type
```

### 3.2 Edge Types

```
REQUIRES           — SkillNode → SkillNode        (hard dependency: must be present)
EXTENDS            — SkillNode → SkillNode        (inherits + overrides behavior)
COMPOSES_WITH      — SkillNode → SkillNode        (can be chained in a pipeline)
CONFLICTS_WITH     — SkillNode → SkillNode        (mutual exclusion)
BELONGS_TO         — SkillNode → DomainNode       (domain classification)
PROVIDES           — SkillNode → CapabilityNode   (what the skill can do)
MEMBER_OF          — SkillNode → BundleNode       (bundle membership)
TARGETS            — SkillNode → AgentNode         (which agents can run it)
SUPERSEDES         — SkillNode → SkillNode        (version lineage)
DERIVED_FROM       — SkillNode → SkillNode        (split/merge provenance)
```

### 3.3 SkillNode Properties

```yaml
# === Identity (immutable after creation) ===
skill_id: str                    # Directory name (unique within namespace)
namespace: str                   # "" (local), "plugin/<name>", "remote/<id>"

# === Classification (L1+) ===
type: enum                       # task | meta | domain | utility | template | composite
domain: list[str]                # ["agent-architecture", "document-processing"]
layer: str                       # L0-execution | L1-learning | L2-meta | L3-governance
substrate: enum                  # pure-prompt | script | composite | external-tool

# === Lifecycle (L3) ===
lifecycle_state: enum            # candidate → validated → operational → refined → deprecated → archived
maturity: enum                   # created | tested | production | battle-tested
confidence: float                # 0.0–1.0 (from KSTAR delta if available)
created_at: datetime
updated_at: datetime
deprecated_at: datetime | null

# === Versioning (L2+) ===
version: str                     # semver
version_lineage: list[str]       # [skill_id@v0.1.0, skill_id@v0.2.0, ...]

# === Capability Manifest (L3) ===
inputs: list[str]                # Named input slots
outputs: list[str]               # Named output slots
tools_required: list[str]        # MCP tools, CLI tools, etc.
pre_flight_checks: list[dict]    # Health checks before execution
model_preference: str            # sonnet | opus | haiku

# === Source Tracking ===
source_type: enum                # local | tap | plugin | remote | marketplace
source_location: str             # Path, URL, tap name
tap: str                         # Tap name if from a tap
checksum: str                    # Intrinsic SHA256
```

### 3.4 DomainNode Properties

```yaml
domain_id: str                   # "agent-architecture", "document-processing", etc.
display_name: str
description: str
parent_domain: str | null        # Hierarchical domains (e.g., "education" → "k12")
```

### 3.5 Lifecycle State Machine

```
                ┌─────────────┐
                │  candidate   │  ← default for new skills
                └──────┬──────┘
                       │ validate
                ┌──────▼──────┐
                │  validated   │  ← passes health checks, tested once
                └──────┬──────┘
                       │ promote
                ┌──────▼──────┐
          ┌────►│ operational  │  ← daily-driver, linked to targets
          │     └──────┬──────┘
          │            │ refine
          │     ┌──────▼──────┐
          └─────┤   refined    │  ← iterated improvement (loops back)
                └──────┬──────┘
                       │ deprecate
                ┌──────▼──────┐
                │  deprecated  │  ← superseded, still accessible
                └──────┬──────┘
                       │ archive
                ┌──────▼──────┐
                │   archived   │  ← removed from active graph
                └─────────────┘
```

Transitions are recorded as events in `ontology.yaml`:

```yaml
lifecycle_history:
  - from: candidate
    to: validated
    timestamp: 2026-03-15T10:00:00Z
    reason: "Passed manual testing in 3 sessions"
  - from: validated
    to: operational
    timestamp: 2026-03-20T14:30:00Z
    reason: "Linked to claude-code, stable for 5 days"
```

---

## 4. File Format: `ontology.yaml`

Every skill directory MAY contain an `ontology.yaml` sidecar file. If absent, the system infers L0 defaults from SKILL.md.

### 4.1 Full Example

```yaml
# ontology.yaml — Ontology metadata for kstar-episode-compiler
schema_version: "1.0"

# Classification
type: meta
domain:
  - agent-architecture
  - skill-management
layer: L1-learning
substrate: composite

# Lifecycle
lifecycle:
  state: operational
  maturity: battle-tested
  confidence: 0.88
  history:
    - { from: candidate, to: validated, at: "2025-12-01", reason: "Initial testing" }
    - { from: validated, to: operational, at: "2026-01-15", reason: "Stable across 20+ compilations" }

# Versioning
version: "1.0.0"
lineage:
  - "kstar-episode-compiler@0.1.0"
  - "kstar-episode-compiler@0.5.0"
  - "kstar-episode-compiler@1.0.0"

# Edges (relationships)
edges:
  requires: []
  extends: []
  composes_with:
    - kstar-transformation
    - kstar-to-skill
  conflicts_with: []
  supersedes: []
  derived_from: []

# Capability manifest
capability:
  inputs:
    - episodes_json        # KSTAR episode trace(s)
    - compilation_mode     # single_episode | multi_episode | pattern_intersection
  outputs:
    - compiled_skill       # Three-layer skill package
    - situation_model      # Parameterizable context structure
  tools_required:
    - python3
  pre_flight:
    - check: "python3 -c 'import json, re, hashlib'"
      on_fail: "Python 3 with standard library required"
  model_preference: sonnet

# Tags (free-form, for backward compat with existing search)
tags:
  - kstar
  - episode-to-skill
  - neolaf
  - compiler
```

### 4.2 Minimal Example (L1 skill)

```yaml
schema_version: "1.0"
type: task
domain: [document-processing]
tags: [wechat, html, conversion]
```

### 4.3 Checksum Policy

`ontology.yaml` is classified as a **neoskills-generated file** and excluded from intrinsic checksums (same as `metadata.yaml` and `provenance.yaml`). This means ontology enrichment never changes a skill's identity hash.

---

## 5. In-Memory Graph Engine

### 5.1 Architecture

```
┌─────────────────────────────────────────────────────┐
│                    CLI / API                         │
├─────────────────────────────────────────────────────┤
│              OntologyEngine (query layer)            │
│  ┌─────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ discover │  │ traverse │  │ compose/decompose │  │
│  └─────────┘  └──────────┘  └───────────────────┘  │
├─────────────────────────────────────────────────────┤
│              SkillGraph (property graph)             │
│  ┌───────┐  ┌───────┐  ┌────────────────────────┐  │
│  │ nodes │  │ edges │  │ indexes (by domain,     │  │
│  │ dict  │  │ list  │  │  type, state, cap, tag) │  │
│  └───────┘  └───────┘  └────────────────────────┘  │
├─────────────────────────────────────────────────────┤
│              OntologyLoader (file→graph)             │
│  ┌──────────┐  ┌───────────┐  ┌─────────────────┐  │
│  │ walk_fs  │  │ parse_yaml│  │ infer_defaults  │  │
│  └──────────┘  └───────────┘  └─────────────────┘  │
├─────────────────────────────────────────────────────┤
│          File System (Cellar / taps / plugins)       │
│  ~/.neoskills/taps/   ~/.claude/skills/   plugins/   │
└─────────────────────────────────────────────────────┘
```

### 5.2 SkillGraph Data Structure

The graph is a lightweight in-memory property graph — no external dependency. Think of it like a Python dict-of-dicts adjacency list with typed edges, plus inverted indexes for fast lookups.

```python
@dataclass
class SkillNode:
    """A node in the skill ontology graph."""
    skill_id: str
    namespace: str = ""
    # ... all properties from §3.3

@dataclass
class OntologyEdge:
    """A typed, directed edge between two nodes."""
    source: str          # skill_id
    target: str          # skill_id or domain_id or capability_id
    edge_type: EdgeType  # REQUIRES, EXTENDS, COMPOSES_WITH, etc.
    metadata: dict = field(default_factory=dict)  # weight, reason, since

class SkillGraph:
    """In-memory property graph of skills and their relationships."""

    nodes: dict[str, SkillNode]
    edges: list[OntologyEdge]

    # Inverted indexes for fast lookup
    _by_domain: dict[str, set[str]]
    _by_type: dict[str, set[str]]
    _by_state: dict[str, set[str]]
    _by_capability: dict[str, set[str]]
    _adjacency: dict[str, dict[EdgeType, set[str]]]  # forward
    _reverse_adjacency: dict[str, dict[EdgeType, set[str]]]  # reverse
```

### 5.3 Loading Strategy

The loader walks three source trees and builds a unified graph:

```
Source Tree                    Namespace Prefix
─────────────────────────────────────────────
~/.neoskills/taps/*/skills/*   ""  (local tap skills)
~/.claude/skills/*             ""  (local agent skills)
.local-plugins/*/skills/*      "plugin/<domain>"
.remote-plugins/*/skills/*     "remote/<plugin_id>"
```

**Loading pipeline:**

1. **Walk** — Discover all directories containing SKILL.md.
2. **Parse** — Read SKILL.md frontmatter + `ontology.yaml` (if present).
3. **Infer** — For L0 skills, infer type/domain/tags from SKILL.md content using heuristics.
4. **Build** — Create SkillNode, register in graph, create edges from `edges:` block.
5. **Index** — Populate inverted indexes.
6. **Validate** — Check for broken edges (referencing non-existent skills), cycles in REQUIRES, conflicting edges.

**Performance target:** Load <500ms for 150 skills (mostly YAML parsing; no LLM calls).

### 5.4 Persistence: Write-Back to `ontology.yaml`

When the graph is mutated (via CLI or API), changes write back to the corresponding `ontology.yaml`:

```python
class OntologyWriter:
    def write_node(self, node: SkillNode) -> Path:
        """Write/update ontology.yaml in the skill directory."""

    def write_edge(self, edge: OntologyEdge) -> None:
        """Add edge to source skill's ontology.yaml edges block."""
```

This is the file-system-as-database contract: reads are fast (walk + parse), writes are targeted (update one YAML file per mutation).

---

## 6. Domain Taxonomy

A predefined (but extensible) two-level domain taxonomy bootstrapped from your current skill inventory:

```yaml
domains:
  agent-architecture:
    display: "Agent Architecture"
    children:
      - kstar-cognitive      # KSTAR loop, planner, observer, delta, retrieval
      - agent-lifecycle       # skill-lifecycle-manager, kstar-to-skill
      - agent-design          # neo-agent-design, p3394-*
      - agent-memory          # kstar-transformation, kstar-xapi

  education:
    display: "Education & Learning"
    children:
      - learning-runtime      # run-module, learning-session-runtime
      - curriculum            # curriculum-guidance, teacher-companion
      - assessment            # quiz-generator, lm-quiz
      - skill-transfer        # skill-transfer-protocol, teacher-skill-compiler

  document-processing:
    display: "Document Processing"
    children:
      - conversion            # source-text-to-markdown, wechat-html-converter
      - academic              # research-md-to-latex, paper-refinement, bibitem-retriever
      - pipeline              # doc-pipeline, chat-to-wechat-article

  business:
    display: "Business Operations"
    children:
      - bidding               # quinn-bid-generator, bid-doc-composer, bid-doc-decomposer
      - planning              # master-plan-assistant, richard-master-plan
      - strategy              # neolaf-business-plan-reviewer

  knowledge-work:
    display: "Knowledge Work (Plugin)"
    children:
      - finance
      - legal
      - marketing
      - product-management
      - sales
      - customer-support
      - data-analysis
      - enterprise-search

  meta:
    display: "Meta & Tooling"
    children:
      - skill-management      # skill-creator, skill-dependency-analyzer, skill-lifecycle-manager
      - understanding         # teach-any-skill, concept-*, grokpedia-to-skill
      - infrastructure        # mcp-builder, openclaw-installer, schedule
```

---

## 7. Composition & Decomposition

### 7.1 Composition Model

Skills compose via **pipelines** (sequential) or **ensembles** (parallel/selector). A composition is itself a skill — it gets its own directory, SKILL.md, and ontology.yaml with `type: composite`.

```yaml
# ontology.yaml for a composite skill
type: composite
composition:
  mode: pipeline            # pipeline | ensemble | selector
  stages:
    - skill_id: source-text-to-markdown
      inputs: { source_file: "$input.file" }
      outputs: { markdown: "$stage.1.md" }
    - skill_id: research-md-to-latex
      inputs: { markdown: "$stage.1.md" }
      outputs: { latex: "$output.tex" }
  fallback: null            # Optional fallback skill on failure
```

### 7.2 Decomposition

When a monolithic skill needs splitting, the `neoskills ontology split` command:

1. Creates N new skill directories (sub-skills).
2. Moves relevant content from the parent.
3. Creates `DERIVED_FROM` edges from each child to the parent.
4. Optionally creates a `composite` wrapper that chains the children.
5. Marks the parent as `deprecated` with `SUPERSEDES` edges.

### 7.3 Template / Instance Pattern

For skills that are parameterized (like `richard-master-plan` being an instance of `master-plan-assistant`):

```yaml
# ontology.yaml for richard-master-plan
type: task
edges:
  extends:
    - master-plan-assistant   # This is the template
instance_params:
  user: "Richard Tong"
  timezone: "US/Eastern"
  sheet_url: "https://docs.google.com/..."
```

---

## 8. Discovery & Retrieval API

### 8.1 Query Interface

```python
class OntologyEngine:
    """High-level query and mutation API over the SkillGraph."""

    # --- Discovery ---
    def discover(self, **filters) -> list[SkillNode]:
        """Faceted search: by domain, type, state, capability, tags, text."""

    def find_by_capability(self, capability: str) -> list[SkillNode]:
        """Which skills provide this capability?"""

    def find_related(self, skill_id: str, depth: int = 1) -> SubGraph:
        """Return the neighborhood of a skill (N-hop traversal)."""

    def find_path(self, from_skill: str, to_skill: str) -> list[OntologyEdge]:
        """Shortest path between two skills in the graph."""

    # --- Dependency Analysis ---
    def dependencies(self, skill_id: str, transitive: bool = False) -> list[str]:
        """What does this skill require (direct or transitive)?"""

    def dependents(self, skill_id: str, transitive: bool = False) -> list[str]:
        """What skills depend on this one?"""

    def check_conflicts(self, skill_ids: list[str]) -> list[tuple[str, str]]:
        """Are any of these skills in conflict?"""

    # --- Lifecycle ---
    def transition(self, skill_id: str, to_state: str, reason: str) -> None:
        """Move a skill through the lifecycle state machine."""

    def lifecycle_report(self) -> dict[str, list[SkillNode]]:
        """Group all skills by lifecycle state."""

    # --- Composition ---
    def compose(self, skill_ids: list[str], mode: str, name: str) -> SkillNode:
        """Create a composite skill from component skills."""

    def decompose(self, skill_id: str, split_plan: dict) -> list[SkillNode]:
        """Split a skill into focused sub-skills."""

    # --- Versioning ---
    def version_bump(self, skill_id: str, bump: str = "patch") -> str:
        """Bump version (major/minor/patch) and record lineage."""

    def diff(self, skill_id: str, v1: str, v2: str) -> dict:
        """Compare two versions of a skill's ontology."""

    # --- Graph Mutation ---
    def add_edge(self, source: str, target: str, edge_type: str, **meta) -> None:
        """Add a relationship between two skills."""

    def remove_edge(self, source: str, target: str, edge_type: str) -> None:
        """Remove a relationship."""

    # --- Enrichment ---
    def enrich(self, skill_id: str, level: str = "L1") -> SkillNode:
        """Auto-enrich a skill's ontology metadata (Claude-powered for L1)."""

    def enrich_all(self, level: str = "L1", dry_run: bool = True) -> list[dict]:
        """Batch-enrich all skills below the target level."""
```

### 8.2 CLI Commands

```
neoskills ontology load              # Build graph from filesystem, print summary
neoskills ontology discover          # Interactive faceted search
neoskills ontology graph <skill_id>  # Show neighborhood graph (ASCII or Mermaid)
neoskills ontology deps <skill_id>   # Show dependency tree
neoskills ontology rdeps <skill_id>  # Show reverse dependency tree
neoskills ontology conflicts         # Report all conflict edges
neoskills ontology lifecycle         # Show all skills grouped by lifecycle state
neoskills ontology transition <id> <state> --reason "..."
neoskills ontology compose <id1> <id2> ... --mode pipeline --name <name>
neoskills ontology split <id> --plan <plan.yaml>
neoskills ontology version <id> --bump minor
neoskills ontology enrich [<id>|--all] [--level L1]
neoskills ontology validate          # Check graph integrity
neoskills ontology export            # Export graph as JSON/Mermaid/DOT
neoskills ontology stats             # Counts by type, domain, state, enrichment level
```

---

## 9. Implementation Plan

### 9.1 New Modules

```
src/neoskills/
├── ontology/                      # NEW — Ontology layer
│   ├── __init__.py
│   ├── models.py                  # SkillNode, OntologyEdge, EdgeType, enums
│   ├── graph.py                   # SkillGraph (in-memory property graph)
│   ├── loader.py                  # OntologyLoader (filesystem → graph)
│   ├── writer.py                  # OntologyWriter (graph mutations → YAML)
│   ├── engine.py                  # OntologyEngine (query/mutation API)
│   ├── taxonomy.py                # Domain taxonomy definitions
│   ├── lifecycle.py               # State machine, transition rules
│   ├── composition.py             # Compose/decompose logic
│   ├── versioning.py              # Semver ops, lineage tracking
│   ├── inference.py               # L0 → L1 heuristic inference
│   └── export.py                  # Graph → Mermaid, DOT, JSON
├── cli/
│   └── ontology_cmd.py            # NEW — Click command group
```

### 9.2 Changes to Existing Modules

| Module | Change |
|--------|--------|
| `core/models.py` | Add `OntologyMixin` fields to `SkillSpec`; keep backward compat |
| `core/frontmatter.py` | No change (SKILL.md parsing unchanged) |
| `core/checksum.py` | Add `ontology.yaml` to excluded files list |
| `core/cellar.py` | Add `ontology_cache_path` property |
| `cli/main.py` | Register `ontology` command group |
| `cli/list_cmd.py` | Use ontology engine for richer search results |
| `meta/enhancer.py` | Add `enrich_ontology` enhancement type |

### 9.3 Phased Rollout

**Phase 1 — Foundation (this PR)**
- `ontology/models.py` — SkillNode, OntologyEdge, EdgeType, LifecycleState, SkillType, etc.
- `ontology/graph.py` — SkillGraph with indexes
- `ontology/loader.py` — Walk filesystem, parse SKILL.md + ontology.yaml, build graph
- `ontology/writer.py` — Write ontology.yaml back to disk
- `ontology/taxonomy.py` — Bootstrap domain taxonomy
- `ontology/lifecycle.py` — State machine with transition validation
- `cli/ontology_cmd.py` — load, stats, discover, deps, validate, graph, lifecycle, transition

**Phase 2 — Composition & Versioning**
- `ontology/composition.py` — compose, decompose, template/instance
- `ontology/versioning.py` — semver bump, lineage tracking, diff
- CLI: compose, split, version commands

**Phase 3 — Intelligence**
- `ontology/inference.py` — Claude-powered L0→L1 enrichment
- `ontology/export.py` — Mermaid, DOT, JSON graph export
- Integration with `kstar-memory` MCP for semantic similarity queries
- CLI: enrich, export commands

### 9.4 Migration Path

No breaking changes. The ontology layer is **additive**:

1. Existing skills without `ontology.yaml` → loaded as L0, fully functional.
2. `neoskills ontology enrich --all --level L1 --dry-run` → preview what would be inferred.
3. `neoskills ontology enrich --all --level L1` → write `ontology.yaml` sidecars.
4. Authors manually add L2 edges and L3 lifecycle data over time.

---

## 10. Plugin / API Interface

### 10.1 Python API

```python
from neoskills.ontology import OntologyEngine

# Load the full graph
engine = OntologyEngine.from_cellar()

# Discovery
skills = engine.discover(domain="agent-architecture", type="meta", state="operational")

# Dependencies
deps = engine.dependencies("kstar-episode-compiler", transitive=True)

# Composition
pipeline = engine.compose(
    ["source-text-to-markdown", "research-md-to-latex"],
    mode="pipeline",
    name="md-to-paper"
)

# Lifecycle
engine.transition("my-new-skill", "validated", reason="Passed 5 test runs")

# Versioning
engine.version_bump("kstar-episode-compiler", bump="minor")
```

### 10.2 MCP Tool Interface (for embedded plugin mode)

```python
# Added to runtime/claude/plugin.py
@mcp_tool
def neoskills_ontology_discover(domain: str = "", type: str = "", state: str = "") -> list[dict]:
    """Discover skills by ontology facets."""

@mcp_tool
def neoskills_ontology_deps(skill_id: str, transitive: bool = False) -> list[str]:
    """Get dependencies for a skill."""

@mcp_tool
def neoskills_ontology_graph(skill_id: str, depth: int = 1) -> str:
    """Get the neighborhood graph as Mermaid diagram."""

@mcp_tool
def neoskills_ontology_transition(skill_id: str, to_state: str, reason: str) -> dict:
    """Transition a skill's lifecycle state."""
```

### 10.3 Export Formats

- **Mermaid** — For rendering in Markdown / Obsidian / GitHub.
- **DOT** — For Graphviz rendering.
- **JSON** — For programmatic consumption.
- **YAML** — For human editing (the native format).

---

## 11. Worked Example: Full Lifecycle

**Scenario:** Richard creates a new skill `wechat-math-renderer`, enriches it, connects it, composes it, and eventually deprecates it.

```bash
# 1. Create
neoskills create wechat-math-renderer
# → Creates ~/.neoskills/taps/mySkills/skills/wechat-math-renderer/SKILL.md
# → ontology.yaml auto-generated with: type=task, state=candidate, version=0.1.0

# 2. Enrich (Claude-powered)
neoskills ontology enrich wechat-math-renderer --level L1
# → Analyzes SKILL.md, infers domain=[document-processing],
#   tags=[wechat, math, latex, rendering]

# 3. Connect
neoskills ontology add-edge wechat-math-renderer --requires wechat-html-converter
neoskills ontology add-edge wechat-math-renderer --composes-with chat-to-wechat-article
# → Edges written to ontology.yaml

# 4. Validate + promote
neoskills ontology transition wechat-math-renderer validated \
  --reason "Tested with 10 articles, all formulas render correctly"

# 5. Deploy + promote
neoskills link wechat-math-renderer
neoskills ontology transition wechat-math-renderer operational \
  --reason "Linked to claude-code, daily use"

# 6. Compose into pipeline
neoskills ontology compose chat-to-wechat-article wechat-math-renderer \
  --mode pipeline --name wechat-math-article-pipeline
# → Creates new composite skill directory

# 7. Version bump after improvement
neoskills ontology version wechat-math-renderer --bump minor
# → version 0.1.0 → 0.2.0, lineage updated

# 8. Eventually supersede
neoskills ontology transition wechat-math-renderer deprecated \
  --reason "Merged into doc-pipeline wechat-math-html skill"
neoskills ontology add-edge wechat-math-html --supersedes wechat-math-renderer
```

---

## 12. Success Criteria

1. `neoskills ontology load` builds a graph of all ~110 skills in <500ms.
2. `neoskills ontology stats` shows enrichment level distribution.
3. `neoskills ontology discover --domain agent-architecture --state operational` returns the correct subset.
4. `neoskills ontology deps kstar-episode-compiler --transitive` shows the full dependency tree.
5. `neoskills ontology validate` catches broken edges and REQUIRES cycles.
6. `neoskills ontology graph kstar-loop --depth 2` renders a readable Mermaid diagram.
7. All existing skills (L0) continue to work without any `ontology.yaml` file.
8. `neoskills ontology enrich --all --level L1 --dry-run` previews inferred metadata for review.
