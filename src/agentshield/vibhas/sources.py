from __future__ import annotations

from typing import Dict, Tuple

from agentshield import EventKind, Label, Sensitivity, Trust

LABELED_KINDS = {EventKind.TOOL_RESULT, EventKind.MEMORY_READ, EventKind.AGENT_MESSAGE}


class SourceLabeler:
    """Labels incoming content by its source. Anything not in the config is untrusted."""

    def __init__(self, sources: dict[str, tuple[Trust, Sensitivity]]):
        self.sources = sources

    def label(self, event, session):
        if event.kind not in LABELED_KINDS:
            return
        
        # Unknown sources default to UNTRUSTED trust and INTERNAL sensitivity
        trust, sensitivity = self.sources.get(event.name, (Trust.UNTRUSTED, Sensitivity.INTERNAL))
        
        # Establish origin naming convention (e.g. tool:<name>, memory:<key>, agent:<id>)
        origin_prefix = {
            EventKind.TOOL_RESULT: "tool",
            EventKind.MEMORY_READ: "memory",
            EventKind.AGENT_MESSAGE: "agent",
        }.get(event.kind, "source")
        
        origin = f"{origin_prefix}:{event.name}"
        yield Label(origin, trust, sensitivity)