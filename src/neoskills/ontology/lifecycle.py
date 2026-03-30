"""Lifecycle state machine for skills.

Manages state transitions with validation and event recording.
"""

from __future__ import annotations

from datetime import datetime, timezone

from neoskills.ontology.models import LifecycleEvent, LifecycleState, SkillNode


class LifecycleError(Exception):
    """Raised when an invalid lifecycle transition is attempted."""


def transition(node: SkillNode, to_state: str | LifecycleState, reason: str = "") -> LifecycleEvent:
    """Transition a skill to a new lifecycle state.

    Validates the transition is legal, records the event, and updates the node.
    Returns the recorded event.

    Raises LifecycleError if the transition is not allowed.
    """
    if isinstance(to_state, str):
        try:
            target = LifecycleState(to_state)
        except ValueError:
            valid = [s.value for s in LifecycleState]
            raise LifecycleError(f"Unknown state '{to_state}'. Valid states: {valid}")
    else:
        target = to_state

    current = node.lifecycle_state

    if current == target:
        raise LifecycleError(f"Skill '{node.skill_id}' is already in state '{target.value}'")

    if not current.can_transition_to(target):
        allowed = [s.value for s in LifecycleState.valid_transitions().get(current, [])]
        raise LifecycleError(
            f"Cannot transition '{node.skill_id}' from '{current.value}' "
            f"to '{target.value}'. Allowed transitions: {allowed}"
        )

    event = LifecycleEvent(
        from_state=current.value,
        to_state=target.value,
        timestamp=datetime.now(timezone.utc).isoformat(),
        reason=reason,
    )

    node.lifecycle_state = target
    node.lifecycle_history.append(event)

    # Auto-update maturity based on state
    _auto_maturity(node, target)

    return event


def _auto_maturity(node: SkillNode, state: LifecycleState) -> None:
    """Auto-advance maturity when lifecycle state changes."""
    maturity_map = {
        LifecycleState.CANDIDATE: "created",
        LifecycleState.VALIDATED: "tested",
        LifecycleState.OPERATIONAL: "production",
        LifecycleState.REFINED: "battle-tested",
    }
    if state in maturity_map:
        # Only advance maturity forward, never regress
        ordering = ["created", "tested", "production", "battle-tested"]
        current_idx = ordering.index(node.maturity) if node.maturity in ordering else 0
        new_idx = ordering.index(maturity_map[state])
        if new_idx > current_idx:
            node.maturity = maturity_map[state]


def lifecycle_summary(nodes: list[SkillNode]) -> dict[str, list[str]]:
    """Group skill IDs by lifecycle state."""
    result: dict[str, list[str]] = {state.value: [] for state in LifecycleState}
    for node in nodes:
        result[node.lifecycle_state.value].append(node.skill_id)
    for v in result.values():
        v.sort()
    return result
