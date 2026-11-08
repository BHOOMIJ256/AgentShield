"""LangGraph hook: a node that checks the agent's pending tool calls before the tool node runs.

    shield_node = make_shield_node(shield, agent_id="hr-agent")
    graph.add_node("shield", shield_node)
    graph.add_edge("agent", "shield")
    graph.add_conditional_edges("shield", route_after_shield, {"tools": "tools", "blocked": "agent", "end": END})

Nothing here imports langgraph: the node is a plain function over the state dict, so
it works in any graph that keeps messages under `state["messages"]` and puts tool calls
on the last message (`.tool_calls` or `["tool_calls"]`, each `{"name", "args"}`).

This hook is synchronous and cannot pause for a human. A `REQUIRE_APPROVAL` verdict
sets `shield_status` to "needs_approval" so your graph can route to its own
interrupt/approval node.
"""

from __future__ import annotations

import uuid
from typing import Any, Callable, Mapping

from ..kernel import SEVERITY, Shield
from ..model import Action, Event, EventKind

STATUS_KEY = "shield_status"  # "ok" | "needs_approval" | "blocked" | "terminated"
REASONS_KEY = "shield_reasons"


def make_shield_node(
    shield: Shield,
    *,
    agent_id: str,
    session_id: str | None = None,
) -> Callable[[Mapping[str, Any]], dict[str, Any]]:
    """Build a graph node. One node (and session id) per conversation."""
    sid = session_id or uuid.uuid4().hex

    def shield_node(state: Mapping[str, Any]) -> dict[str, Any]:
        worst = Action.ALLOW
        reasons: list[str] = []
        for call in _pending_tool_calls(state):
            decision = shield.check(Event(EventKind.TOOL_CALL, sid, agent_id, call["name"], dict(call["args"])))
            action = decision.enforced_action
            if SEVERITY[action] > SEVERITY[worst]:
                worst = action
            reasons.extend(decision.reasons)
        return {STATUS_KEY: _STATUS[worst], REASONS_KEY: reasons}

    return shield_node


def route_after_shield(state: Mapping[str, Any]) -> str:
    """Conditional-edge router: 'tools' when clear, 'end' when terminated, else 'blocked'."""
    status = state.get(STATUS_KEY, "blocked")  # missing status means the node never ran: fail closed
    if status == "ok":
        return "tools"
    return "end" if status == "terminated" else "blocked"


_STATUS = {
    Action.ALLOW: "ok",
    Action.WARN: "ok",
    Action.REQUIRE_APPROVAL: "needs_approval",
    Action.BLOCK: "blocked",
    Action.TERMINATE: "terminated",
}


def _pending_tool_calls(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    messages = state.get("messages") or []
    if not messages:
        return []
    last = messages[-1]
    raw = last.get("tool_calls") if isinstance(last, Mapping) else getattr(last, "tool_calls", None)
    return [
        {"name": c["name"], "args": c.get("args") or {}}
        for c in (raw or [])
    ]
