from __future__ import annotations

from agentshield import EventKind, Label, Sensitivity, Trust


class MCPLabeler:
    """Labels TOOL_DESCRIPTION events by the MCP server's trust level.

    A poisoned or malicious tool description from an unverified MCP server
    is correctly tagged as UNTRUSTED content.
    """

    def __init__(self, server_trusts: dict[str, Trust]) -> None:
        """`server_trusts`: mapping of MCP server names/IDs to their Trust level."""
        self.server_trusts = server_trusts

    def label(self, event, session):
        if event.kind != EventKind.TOOL_DESCRIPTION:
            return

        # Extract server identifier from event or payload, defaulting to UNTRUSTED
        server_name = getattr(event, "server", None) or event.payload.get("server", "unknown")
        trust = self.server_trusts.get(server_name, Trust.UNTRUSTED)
        
        # Tool descriptions default to internal sensitivity
        sensitivity = Sensitivity.INTERNAL

        origin = f"mcp:{server_name}/{event.name}"
        yield Label(origin, trust, sensitivity)