"""Predefined domain taxonomy for the skill ontology.

A two-level hierarchy of knowledge domains, bootstrapped from
Richard's current skill inventory. Extensible at runtime.
"""

from __future__ import annotations

from neoskills.ontology.models import DomainNode


# ──────────────────────────────────────────────
# Bootstrap taxonomy
# ──────────────────────────────────────────────

_TAXONOMY: dict[str, dict] = {
    "agent-architecture": {
        "display": "Agent Architecture",
        "description": "Design and implementation of AI agent systems",
        "children": {
            "kstar-cognitive": {
                "display": "KSTAR Cognitive Cycle",
                "description": "KSTAR loop, planner, observer, delta, retrieval",
            },
            "agent-lifecycle": {
                "display": "Agent Lifecycle",
                "description": "Skill lifecycle management, kstar-to-skill compilation",
            },
            "agent-design": {
                "display": "Agent Design",
                "description": "NEOLAF/Neo agent design, P3394 configuration",
            },
            "agent-memory": {
                "display": "Agent Memory",
                "description": "KSTAR transformation, xAPI integration, memory encoding",
            },
        },
    },
    "education": {
        "display": "Education & Learning",
        "description": "Teaching, learning, curriculum, and assessment",
        "children": {
            "learning-runtime": {
                "display": "Learning Runtime",
                "description": "Module execution, learning session orchestration",
            },
            "curriculum": {
                "display": "Curriculum & Teaching",
                "description": "Curriculum guidance, teacher companion, skill transfer",
            },
            "assessment": {
                "display": "Assessment & Quizzes",
                "description": "Quiz generation, flashcards, learning validation",
            },
        },
    },
    "document-processing": {
        "display": "Document Processing",
        "description": "Document conversion, formatting, and pipeline processing",
        "children": {
            "conversion": {
                "display": "Format Conversion",
                "description": "Markdown, Word, PDF, HTML format conversion",
            },
            "academic": {
                "display": "Academic Publishing",
                "description": "LaTeX, paper refinement, bibliography, arXiv",
            },
            "wechat": {
                "display": "WeChat Publishing",
                "description": "WeChat Official Account article formatting",
            },
            "pipeline": {
                "display": "Document Pipeline",
                "description": "Multi-stage document processing workflows",
            },
        },
    },
    "business": {
        "display": "Business Operations",
        "description": "Business planning, bidding, and strategy",
        "children": {
            "bidding": {
                "display": "Procurement & Bidding",
                "description": "Bid document generation, decomposition, composition",
            },
            "planning": {
                "display": "Strategic Planning",
                "description": "Master planning, daily planning, goal alignment",
            },
            "strategy": {
                "display": "Business Strategy",
                "description": "Business plan review, NEOLAF strategy",
            },
        },
    },
    "knowledge-work": {
        "display": "Knowledge Work",
        "description": "Domain-specific professional skills from plugins",
        "children": {
            "finance": {
                "display": "Finance & Accounting",
                "description": "Financial statements, reconciliation, audit, variance",
            },
            "legal": {
                "display": "Legal",
                "description": "Contract review, NDA triage, compliance, risk",
            },
            "marketing": {
                "display": "Marketing",
                "description": "Campaigns, content, brand voice, analytics",
            },
            "product-management": {
                "display": "Product Management",
                "description": "Specs, roadmaps, metrics, stakeholder comms",
            },
            "sales": {
                "display": "Sales",
                "description": "Outreach, call prep, competitive intel, pipeline",
            },
            "customer-support": {
                "display": "Customer Support",
                "description": "Triage, response drafting, escalation, KB",
            },
            "data-analysis": {
                "display": "Data Analysis",
                "description": "SQL, visualization, statistics, dashboards",
            },
            "enterprise-search": {
                "display": "Enterprise Search",
                "description": "Multi-source search, knowledge synthesis",
            },
        },
    },
    "meta": {
        "display": "Meta & Tooling",
        "description": "Skills about skills, infrastructure, and utilities",
        "children": {
            "skill-management": {
                "display": "Skill Management",
                "description": "Skill creation, analysis, dependency tracking",
            },
            "understanding": {
                "display": "Understanding & Teaching",
                "description": "Teach-any-skill, concept skills, Grokpedia",
            },
            "infrastructure": {
                "display": "Infrastructure",
                "description": "MCP builders, installers, schedulers, plugin management",
            },
        },
    },
}


def build_domain_nodes() -> dict[str, DomainNode]:
    """Build the full domain node dictionary from the taxonomy definition."""
    nodes: dict[str, DomainNode] = {}

    for domain_id, spec in _TAXONOMY.items():
        children_ids = list(spec.get("children", {}).keys())
        nodes[domain_id] = DomainNode(
            domain_id=domain_id,
            display_name=spec["display"],
            description=spec.get("description", ""),
            parent_domain=None,
            children=children_ids,
        )
        for child_id, child_spec in spec.get("children", {}).items():
            nodes[child_id] = DomainNode(
                domain_id=child_id,
                display_name=child_spec["display"],
                description=child_spec.get("description", ""),
                parent_domain=domain_id,
                children=[],
            )

    return nodes


def get_all_domain_ids() -> list[str]:
    """Return all valid domain IDs (top-level + children)."""
    ids: list[str] = []
    for domain_id, spec in _TAXONOMY.items():
        ids.append(domain_id)
        ids.extend(spec.get("children", {}).keys())
    return sorted(ids)


def infer_domain_from_skill_id(skill_id: str) -> list[str]:
    """Heuristic: infer likely domain(s) from a skill's ID.

    This is a best-effort mapping used for L0 → L1 enrichment.
    """
    sid = skill_id.lower()

    mappings: list[tuple[list[str], list[str]]] = [
        # KSTAR cognitive cycle
        (
            ["kstar-loop", "kstar-planner", "kstar-observer", "kstar-delta", "kstar-retrieval"],
            ["agent-architecture", "kstar-cognitive"],
        ),
        # KSTAR memory/transformation
        (["kstar-transformation", "kstar-xapi"], ["agent-architecture", "agent-memory"]),
        # Skill lifecycle
        (
            ["kstar-to-skill", "skill-lifecycle", "kstar-episode-compiler", "kstar-skill-analyzer"],
            ["agent-architecture", "agent-lifecycle"],
        ),
        # Agent design
        (["neo-agent-design", "p3394"], ["agent-architecture", "agent-design"]),
        # Education
        (
            ["teacher-", "curriculum-", "learning-session", "skill-transfer"],
            ["education", "curriculum"],
        ),
        (["quiz-", "lm-quiz"], ["education", "assessment"]),
        (["run-module"], ["education", "learning-runtime"]),
        # Document processing
        (
            ["wechat-html", "wechat-article", "wechat-math", "chat-to-wechat"],
            ["document-processing", "wechat"],
        ),
        (
            ["research-md-to-latex", "paper-refinement", "bibitem"],
            ["document-processing", "academic"],
        ),
        (["source-text-to-markdown", "doc-pipeline"], ["document-processing", "pipeline"]),
        (["debate-transcript"], ["document-processing", "conversion"]),
        # Business
        (["bid-doc", "quinn-bid"], ["business", "bidding"]),
        (["master-plan", "daily-strategic"], ["business", "planning"]),
        (["neolaf-business"], ["business", "strategy"]),
        # Meta
        (["skill-creator", "skill-dependency", "skill-analyzer"], ["meta", "skill-management"]),
        (["teach-any-skill", "concept-", "grokpedia"], ["meta", "understanding"]),
        (["mcp-builder", "openclaw-installer", "schedule"], ["meta", "infrastructure"]),
    ]

    for patterns, domains in mappings:
        for pattern in patterns:
            if pattern in sid:
                return domains

    return ["general"]


def infer_domain_from_namespace(namespace: str) -> list[str]:
    """Infer domain from plugin namespace (e.g., 'plugin/finance' → ['knowledge-work', 'finance'])."""
    if not namespace.startswith("plugin/"):
        return []
    plugin_domain = namespace.split("/", 1)[1] if "/" in namespace else ""

    # Map plugin domains to taxonomy
    plugin_to_taxonomy: dict[str, list[str]] = {
        "finance": ["knowledge-work", "finance"],
        "legal": ["knowledge-work", "legal"],
        "marketing": ["knowledge-work", "marketing"],
        "product-management": ["knowledge-work", "product-management"],
        "sales": ["knowledge-work", "sales"],
        "customer-support": ["knowledge-work", "customer-support"],
        "data": ["knowledge-work", "data-analysis"],
        "enterprise-search": ["knowledge-work", "enterprise-search"],
    }

    return plugin_to_taxonomy.get(plugin_domain, [])
