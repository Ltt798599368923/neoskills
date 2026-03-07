# Skill Organization & Dependencies Design — v0.4.0

**Date:** 2026-03-07

**Status:** Approved

**Author:** Richard Tong + Claude

---

## 1. Problem

neoskills v0.3.1 treats all skills as a flat pool in `taps/{name}/skills/`, distinguished only by frontmatter tags. This is insufficient because:

- No structural distinction between user-authored skills, project-local skills, and plugin-provided skills
- No dependency system — skills can't declare requirements on other skills, tools, agents, or packages
- No concept of skill types — meta-skills (that manage other skills) and agent-skills (bound to a specific agent context) are indistinguishable from regular portable skills
- Skills are not first-class entities with full dependency graphs

---

## 2. Three Dimensions of Skill Classification

### 2.1 Platform/Origin — which agent was it developed for?

| Platform | Native directory |
|----------|-----------------|
| Claude Code | `.claude/` |
| OpenCode | `.config/opencode/` |
| OpenClaw | `.openclaw/` |
| Portable | Works across agents |

Already modeled via `targets` field in SKILL.md frontmatter. No change needed.

### 2.2 Scope/Control — who owns it, where does it live?

| Scope | Location | Auto-derived |
|-------|----------|-------------|
| **User** | `~/.neoskills/taps/{name}/skills/` | `.neoskills` + `taps` in path |
| **Project** | `./skills/`, `.claude/skills/`, `.openclaw/skills/` | Neither of the other two |
| **Plugin** | `taps/{name}/plugins/{plugin}/skills/` | `plugins` in path |

Scope is **never stored** — always derived from filesystem location.

### 2.3 Function/Type — what kind of work does the skill do?

| Type | Description | Example |
|------|-------------|---------|
| **regular** | Portable, general-purpose skills | `git-commit`, `frontend-design`, `pdf` |
| **meta** | Skills that manage other skills | `skill-dedup`, `skill-scanner`, `skill-deployer` |
| **agent-skill** | Skills bound to a specific agent's context and toolset | Tutoring agent's `create-content`, `evaluate-artifact` |

Stored in `metadata.yaml` (new sidecar file).

---

## 3. Design: SkillManifest Composition

### 3.1 Approach

Introduce `SkillManifest` as the first-class entity that composes `SkillSpec` (from SKILL.md) + dependencies + classification (from metadata.yaml). The manifest is what neoskills operates on internally.

**Key constraint:** SKILL.md format is untouched — must remain compatible with Claude Code conventions. All extended metadata goes in `metadata.yaml`.

### 3.2 metadata.yaml — extension-only sidecar

Lives alongside SKILL.md in the skill directory:

```
skills/evaluate-artifact/
├── SKILL.md           # Claude Code compatible (untouched)
├── metadata.yaml      # neoskills-managed dependency & classification data
├── scripts/           # optional
└── references/        # optional
```

Schema:

```yaml
# metadata.yaml
type: agent-skill           # regular | meta | agent-skill

depends_on:
  skills:                   # skill -> skill
    - rubric-builder
    - content-formatter
  tools:                    # skill -> tool
    - Bash
    - Read
    - Write
  agent: tutoring-agent     # skill -> agent (null = portable)
  packages:                 # skill -> external package
    - "pandas>=2.0"
    - numpy
```

All fields are optional. A skill with no `metadata.yaml` is treated as `type: regular` with no dependencies — fully backward compatible.

### 3.3 Merge strategy

`metadata.yaml` is extension-only — it carries fields that SKILL.md frontmatter doesn't. No duplication. `SkillManifest.from_skill_dir()` reads SKILL.md first (into `SkillSpec`), then overlays `metadata.yaml`.

---

## 4. Domain Models

### 4.1 New types

```python
class SkillType(Enum):
    REGULAR = "regular"
    META = "meta"
    AGENT_SKILL = "agent-skill"

class Scope(Enum):
    USER = "user"
    PROJECT = "project"
    PLUGIN = "plugin"

@dataclass
class DependencySet:
    skills: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    agent: str | None = None
    packages: list[str] = field(default_factory=list)

@dataclass
class SkillManifest:
    spec: SkillSpec
    type: SkillType = SkillType.REGULAR
    scope: Scope = Scope.USER
    depends_on: DependencySet = field(default_factory=DependencySet)
    resolved: bool = False

    @classmethod
    def from_skill_dir(cls, skill_dir: Path, tap_name: str = "") -> "SkillManifest":
        """Load SkillSpec from SKILL.md, extend with metadata.yaml."""
```

### 4.2 SkillSpec — unchanged

`SkillSpec` remains the clean SKILL.md-only representation. No modifications.

---

## 5. Resolver — Dependency Resolution Engine

New core class alongside Cellar, TapManager, and Linker.

```python
class Resolver:
    def __init__(self, tap_manager: TapManager, linker: Linker): ...

    def resolve(self, manifest: SkillManifest, target: str) -> ResolveResult:
        """Walk dependency graph, return ordered install plan.
        Auto-resolves missing skill deps from available taps."""

    def validate(self, manifest: SkillManifest, target: str) -> list[DepIssue]:
        """Check a single manifest for unmet dependencies."""

    def check_all(self, target: str) -> list[DepIssue]:
        """Validate all linked skills — full health report."""

@dataclass
class ResolveResult:
    install_order: list[SkillManifest]   # topologically sorted
    unresolved_skills: list[str]
    unresolved_tools: list[str]
    unresolved_packages: list[str]
    agent_mismatch: str | None

    @property
    def ok(self) -> bool: ...

@dataclass
class DepIssue:
    skill_id: str
    kind: str       # "missing_skill" | "missing_tool" | "missing_package" | "agent_mismatch"
    detail: str
```

### Lifecycle integration

| Command | Behavior |
|---------|----------|
| `install` | Resolver.resolve() -> auto-install deps first, then the skill |
| `link` | Resolver.resolve() -> auto-link deps first, warn if unresolvable |
| `uninstall` | Check if other skills depend on it, warn before removing |
| `doctor` | + Resolver.check_all() reports unmet deps |

### Cycle detection

Resolver builds a DAG. Circular dependencies raise `CyclicDependencyError`.

---

## 6. SkillIndex — Multi-Scope Discovery

Unified discovery across all three scopes.

```python
class SkillIndex:
    def __init__(self, cellar: Cellar, tap_manager: TapManager): ...

    def scan(self, scopes: list[Scope] | None = None) -> list[SkillManifest]:
        """Scan all (or filtered) scopes, return unified manifest list."""

    def _scan_user_skills(self) -> list[SkillManifest]: ...
    def _scan_project_skills(self, project_dir: Path) -> list[SkillManifest]: ...
    def _scan_plugin_skills(self) -> list[SkillManifest]: ...

    def get(self, skill_id: str) -> SkillManifest | None: ...
    def search(self, query: str, scopes: list[Scope] | None = None) -> list[SkillManifest]: ...
```

### Scope derivation

```python
@staticmethod
def _derive_scope(skill_dir: Path) -> Scope:
    parts = skill_dir.parts
    if "plugins" in parts:
        return Scope.PLUGIN
    elif ".neoskills" in parts and "taps" in parts:
        return Scope.USER
    else:
        return Scope.PROJECT
```

---

## 7. Runtime Verification

Best-effort dependency checking at runtime:

```python
# neoskills.runtime.deps
def check_deps(skill_dir: Path) -> list[DepIssue]:
    """Read metadata.yaml and verify deps are available.
    Opt-in: called by skills or agent runtime at load time."""
```

---

## 8. File Change Map

### New files

| File | Purpose |
|------|---------|
| `src/neoskills/core/manifest.py` | `SkillManifest`, `DependencySet`, `SkillType`, `Scope` |
| `src/neoskills/core/resolver.py` | `Resolver`, `ResolveResult`, `DepIssue` |
| `src/neoskills/core/index.py` | `SkillIndex` — multi-scope discovery |
| `src/neoskills/runtime/deps.py` | `check_deps()` — runtime verification helper |
| `tests/unit/test_manifest.py` | SkillManifest loading, merging, scope derivation |
| `tests/unit/test_resolver.py` | Dependency resolution, cycle detection, auto-install |
| `tests/unit/test_index.py` | Multi-scope scanning, search, filtering |

### Modified files

| File | Change |
|------|--------|
| `core/models.py` | Remove unused v0.2 models (Skill, SkillMetadata, Provenance, Bundle) |
| `core/tap.py` | `list_skills()` returns `SkillManifest` via index |
| `cli/brew_install_cmd.py` | Install/uninstall use Resolver |
| `cli/link_cmd.py` | Link/unlink use Resolver |
| `cli/list_cmd.py` | Add `--scope` filter, show scope/type columns |
| `cli/doctor_cmd.py` | Add Resolver.check_all() to health report |
| `cli/create_cmd.py` | Scaffold includes metadata.yaml |
| `cli/main.py` | Wire new `deps` subcommand group |

### Unchanged files

| File | Why |
|------|-----|
| `core/linker.py` | Still just manages symlinks |
| `core/cellar.py` | Already handles workspace paths |
| `core/frontmatter.py` | SKILL.md parsing unchanged |
| `adapters/*` | Platform adapters untouched |
| `runtime/claude/plugin.py` | MCP tools unchanged for now |

---

## 9. Backward Compatibility

- Skills without `metadata.yaml` work exactly as today
- SKILL.md format untouched
- Existing CLI commands behave the same unless `--scope` is used
- config.yaml unchanged
- All existing tests continue to pass

---

## 10. metadata.yaml Lifecycle

| Scenario | Behavior |
|----------|----------|
| `neoskills create my-skill` | Scaffold includes empty metadata.yaml |
| `neoskills install skill --from tap` | Copy metadata.yaml along with SKILL.md if present |
| Manual edit | Supported — plain YAML |
| Future: `neoskills deps add/remove/show` | CLI management without hand-editing |

### Validation rules (enforced by doctor)

- `depends_on.skills` must resolve to real skills in some scope
- `depends_on.agent` must match a known agent (or warn)
- `depends_on.packages` uses PEP 508 specifiers (best-effort via importlib.metadata)
- `type` must be a valid SkillType value
- Circular skill dependencies are errors
