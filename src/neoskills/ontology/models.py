"""Domain models for the skill ontology layer.

Defines node types, edge types, and enumerations for the in-memory
property graph that represents skill relationships, lifecycle states,
and capability metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# ──────────────────────────────────────────────
# Enumerations
# ──────────────────────────────────────────────


class SkillType(str, Enum):
    """What kind of skill this is."""

    TASK = "task"  # Performs a concrete action
    META = "meta"  # Operates on other skills
    DOMAIN = "domain"  # Embodies domain knowledge
    UTILITY = "utility"  # Helper / infrastructure
    TEMPLATE = "template"  # Parameterized blueprint
    COMPOSITE = "composite"  # Pipeline / ensemble of skills


class SkillSubstrate(str, Enum):
    """Implementation substrate of the skill."""

    PURE_PROMPT = "pure-prompt"  # SKILL.md only, no scripts
    SCRIPT = "script"  # Has executable scripts/
    COMPOSITE = "composite"  # Mix of prompt + scripts
    EXTERNAL_TOOL = "external-tool"  # Wraps an external CLI / API


class LifecycleState(str, Enum):
    """Maturity lifecycle of a skill."""

    CANDIDATE = "candidate"
    VALIDATED = "validated"
    OPERATIONAL = "operational"
    REFINED = "refined"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"

    @classmethod
    def valid_transitions(cls) -> dict[LifecycleState, list[LifecycleState]]:
        """Return the allowed state transitions."""
        return {
            cls.CANDIDATE: [cls.VALIDATED, cls.DEPRECATED],
            cls.VALIDATED: [cls.OPERATIONAL, cls.DEPRECATED],
            cls.OPERATIONAL: [cls.REFINED, cls.DEPRECATED],
            cls.REFINED: [cls.OPERATIONAL, cls.DEPRECATED],
            cls.DEPRECATED: [cls.ARCHIVED, cls.OPERATIONAL],  # allow un-deprecate
            cls.ARCHIVED: [],  # terminal
        }

    def can_transition_to(self, target: LifecycleState) -> bool:
        return target in self.valid_transitions().get(self, [])


class EdgeType(str, Enum):
    """Types of relationships between nodes in the ontology graph."""

    REQUIRES = "requires"  # Hard dependency
    EXTENDS = "extends"  # Inherits + overrides
    COMPOSES_WITH = "composes_with"  # Can be chained
    CONFLICTS_WITH = "conflicts_with"  # Mutual exclusion
    BELONGS_TO = "belongs_to"  # Domain classification
    PROVIDES = "provides"  # Capability provision
    MEMBER_OF = "member_of"  # Bundle membership
    TARGETS = "targets"  # Agent compatibility
    SUPERSEDES = "supersedes"  # Version lineage
    DERIVED_FROM = "derived_from"  # Split / merge provenance


class EnrichmentLevel(str, Enum):
    """How much ontology metadata a skill has."""

    L0_BARE = "L0"  # SKILL.md only (name + description)
    L1_TAGGED = "L1"  # + ontology.yaml with type, domain, tags
    L2_CONNECTED = "L2"  # + explicit edges
    L3_GOVERNED = "L3"  # + lifecycle, versioning, capability manifest


class CompositionMode(str, Enum):
    """How skills are composed together."""

    PIPELINE = "pipeline"  # Sequential chaining
    ENSEMBLE = "ensemble"  # Parallel execution, merge results
    SELECTOR = "selector"  # Pick one based on context


# ──────────────────────────────────────────────
# Data classes
# ──────────────────────────────────────────────


@dataclass
class LifecycleEvent:
    """A recorded lifecycle state transition."""

    from_state: str
    to_state: str
    timestamp: str  # ISO 8601
    reason: str = ""


@dataclass
class CapabilityManifest:
    """What a skill can do and what it needs to do it."""

    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    tools_required: list[str] = field(default_factory=list)
    pre_flight: list[dict[str, str]] = field(default_factory=list)
    model_preference: str = ""


@dataclass
class CompositionSpec:
    """How a composite skill chains its component skills."""

    mode: CompositionMode = CompositionMode.PIPELINE
    stages: list[dict[str, Any]] = field(default_factory=list)
    fallback: str | None = None


@dataclass
class SkillNode:
    """A node in the skill ontology graph.

    Represents a single skill with all its ontology metadata.
    Designed for progressive enrichment: L0 skills have only
    skill_id/name/description; L3 skills have everything.
    """

    # ── Identity (always present) ──
    skill_id: str
    name: str = ""
    description: str = ""
    namespace: str = ""  # "" (local), "plugin/<name>", "remote/<id>"
    path: Path | None = None  # Filesystem path to skill directory

    # ── Classification (L1+) ──
    type: SkillType = SkillType.TASK
    domain: list[str] = field(default_factory=list)
    layer: str = ""  # L0-execution, L1-learning, L2-meta, L3-governance
    substrate: SkillSubstrate = SkillSubstrate.PURE_PROMPT
    tags: list[str] = field(default_factory=list)

    # ── Lifecycle (L3) ──
    lifecycle_state: LifecycleState = LifecycleState.CANDIDATE
    maturity: str = "created"  # created | tested | production | battle-tested
    confidence: float = 0.0
    lifecycle_history: list[LifecycleEvent] = field(default_factory=list)

    # ── Versioning (L2+) ──
    version: str = "0.1.0"
    lineage: list[str] = field(default_factory=list)

    # ── Capability (L3) ──
    capability: CapabilityManifest = field(default_factory=CapabilityManifest)

    # ── Composition (composite skills) ──
    composition: CompositionSpec | None = None

    # ── Instance params (for template instances) ──
    instance_params: dict[str, Any] = field(default_factory=dict)

    # ── Source tracking ──
    source_type: str = "local"  # local | tap | plugin | remote | marketplace
    source_location: str = ""
    tap: str = ""
    checksum: str = ""

    # ── Enrichment tracking ──
    enrichment_level: EnrichmentLevel = EnrichmentLevel.L0_BARE
    schema_version: str = "1.0"

    @property
    def qualified_id(self) -> str:
        """Namespace-qualified skill ID."""
        if self.namespace:
            return f"{self.namespace}/{self.skill_id}"
        return self.skill_id


@dataclass
class OntologyEdge:
    """A typed, directed edge between two nodes in the graph."""

    source: str  # skill_id (or qualified_id)
    target: str  # skill_id, domain_id, capability, bundle, agent
    edge_type: EdgeType
    metadata: dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash((self.source, self.target, self.edge_type))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, OntologyEdge):
            return NotImplemented
        return (
            self.source == other.source
            and self.target == other.target
            and self.edge_type == other.edge_type
        )


@dataclass
class DomainNode:
    """A domain in the taxonomy."""

    domain_id: str
    display_name: str = ""
    description: str = ""
    parent_domain: str | None = None
    children: list[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of graph validation."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    broken_edges: list[OntologyEdge] = field(default_factory=list)
    cycles: list[list[str]] = field(default_factory=list)


@dataclass
class SubGraph:
    """A subset of the graph (e.g., neighborhood of a node)."""

    nodes: dict[str, SkillNode] = field(default_factory=dict)
    edges: list[OntologyEdge] = field(default_factory=list)
    center: str = ""
    depth: int = 0
