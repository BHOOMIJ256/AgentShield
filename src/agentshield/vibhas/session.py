from __future__ import annotations

from typing import Collection

from ..kernel import Session
from ..model import Action, Decision, Event, EventKind, Sensitivity, Trust


class SessionCombinationPolicy:
    """Problem 2+5: Session combination policy (The Lethal Trifecta).

    Triggers REQUIRE_APPROVAL if a session combines:
    1. Untrusted content (UNTRUSTED labels seen in session history)
    2. Sensitive data (CONFIDENTIAL or SECRET labels seen in session history)
    3. An external action (current tool call is designated as an external action)

    Any two of the three conditions result in no vote (returns None).
    Stateless: reads entirely from session history and configuration.
    """

    policy_id = "session-combination"

    def __init__(self, external_tools: Collection[str]) -> None:
        """`external_tools`: tool names that perform external actions (shared config with egress check)."""
        self.external_tools = set(external_tools)

    def evaluate(self, event: Event, session: Session) -> Decision | None:
        # The trifecta culminates when an external action is attempted.
        if event.kind is not EventKind.TOOL_CALL:
            return None

        is_external_action = event.name in self.external_tools
        if not is_external_action:
            return None

        # Inspect session history and current event for untrusted content and sensitive data
        has_untrusted = False
        has_sensitive = False

        # Gather all events in the session including the current one
        all_events = list(getattr(session, "events", session.history)) + [event]

        for e in all_events:
            for label in e.labels:
                if label.trust == Trust.UNTRUSTED:
                    has_untrusted = True
                if label.sensitivity in (Sensitivity.CONFIDENTIAL, Sensitivity.SECRET):
                    has_sensitive = True

        # Lethal Trifecta: Untrusted + Sensitive + External Action
        if has_untrusted and has_sensitive and is_external_action:
            reasons = [
                "Lethal trifecta detected: session combines untrusted content, "
                "sensitive data, and an external action."
            ]
            return Decision(Action.REQUIRE_APPROVAL, reasons=tuple(reasons))

        return None