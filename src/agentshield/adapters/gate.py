"""Transport-independent enforcement for tool-using agents.

An adapter (the MCP proxy, later LangGraph) reports what it sees — tool listings,
calls, results — and the gate turns each into an Event, runs it through the Shield,
and tells the adapter whether to go ahead. Decisions that require approval wait
for a human.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Mapping

from ..kernel import SEVERITY, Shield
from ..model import Action, Decision, Event, EventKind
from .approval import ApprovalRequest, Approver, DenyAll


@dataclass(frozen=True)
class Outcome:
    proceed: bool
    message: str = ""  # shown to the agent when it may not proceed


class ToolGate:
    """One gate per agent session."""

    def __init__(
        self,
        shield: Shield,
        *,
        agent_id: str,
        server: str,
        approver: Approver | None = None,
        session_id: str | None = None,
    ) -> None:
        self.shield = shield
        self.agent_id = agent_id
        self.server = server
        self.approver = approver or DenyAll()
        self.session_id = session_id or uuid.uuid4().hex
        self.hidden: set[str] = set()
        self.terminated: str | None = None

    def describe_tool(self, name: str, description: str | None, input_schema: Mapping[str, Any]) -> bool:
        """Check a tool description before the agent sees it. Returns False if the tool must be hidden."""
        payload = {"server": self.server, "description": description or "", "input_schema": dict(input_schema)}
        _, decision = self._check(EventKind.TOOL_DESCRIPTION, name, payload)
        visible = SEVERITY[decision.enforced_action] < SEVERITY[Action.REQUIRE_APPROVAL]
        if visible:
            self.hidden.discard(name)
        else:
            self.hidden.add(name)
        return visible

    async def before_call(self, name: str, arguments: Mapping[str, Any]) -> Outcome:
        event, decision = self._check(EventKind.TOOL_CALL, name, dict(arguments))
        if self.terminated:
            return Outcome(False, f"AgentShield ended this session: {self.terminated}")
        if name in self.hidden:
            return Outcome(False, f"AgentShield: tool {name!r} is not available")
        return await self._apply(event, decision, "call")

    async def after_call(self, name: str, content: Any, is_error: bool) -> Outcome:
        event, decision = self._check(EventKind.TOOL_RESULT, name, {"content": content, "is_error": is_error})
        return await self._apply(event, decision, "result")

    def _check(self, kind: EventKind, name: str, payload: dict[str, Any]) -> tuple[Event, Decision]:
        decision = self.shield.check(Event(kind, self.session_id, self.agent_id, name, payload))
        labeled_event, _ = self.shield.session(self.session_id).history[-1]
        return labeled_event, decision

    async def _apply(self, event: Event, decision: Decision, what: str) -> Outcome:
        action = decision.enforced_action
        if action in (Action.ALLOW, Action.WARN):
            return Outcome(True)
        if action is Action.REQUIRE_APPROVAL:
            trace = tuple(e for e in self.shield.session(self.session_id).events if e.event_id != event.event_id)
            approved = await self.approver.decide(ApprovalRequest(event, decision, trace))
            self._record_approval(event, approved)
            if approved:
                return Outcome(True)
            return Outcome(False, _refusal(f"a human declined this {what}", decision))
        if action is Action.TERMINATE:
            self.terminated = "; ".join(decision.reasons) or "a policy ended the session"
        return Outcome(False, _refusal(f"blocked this {what}", decision))

    def _record_approval(self, event: Event, approved: bool) -> None:
        """The human's answer is evidence too: it goes into the same tamper-evident log."""
        if self.shield.audit is not None:
            self.shield.audit.append(
                {
                    "approval": {
                        "event_id": event.event_id,
                        "session_id": event.session_id,
                        "approved": approved,
                        "approver": self.approver.name,
                    }
                }
            )


def _refusal(what: str, decision: Decision) -> str:
    reasons = "; ".join(decision.reasons) or "policy decision"
    return f"AgentShield {what}: {reasons}"
