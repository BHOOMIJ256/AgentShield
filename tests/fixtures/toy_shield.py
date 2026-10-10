"""Toy stand-ins for the real tracks, just enough to drive the proxy end to end.

The real versions are Vibhas's labelers and session policy (V1, V2, V3) and Sahil's SQL
policy (S2). Keep these deliberately naive; don't import them outside tests.
"""

from agentshield import Action, Decision, EventKind, Label, Sensitivity, Trust

SOURCES = {
    "read_resume": (Trust.UNTRUSTED, Sensitivity.INTERNAL),
    "read_salaries": (Trust.TRUSTED, Sensitivity.CONFIDENTIAL),
}


class ToySourceLabeler:
    def label(self, event, session):
        if event.kind is EventKind.TOOL_RESULT and event.name in SOURCES:
            trust, sensitivity = SOURCES[event.name]
            yield Label(f"tool:{event.name}", trust, sensitivity)


class ToyTrifecta:
    policy_id = "toy-trifecta"

    def evaluate(self, event, session):
        if not (event.kind is EventKind.TOOL_CALL and event.name == "send_email"):
            return None
        seen = [label for e in session.events for label in e.labels]
        untrusted = any(label.trust is Trust.UNTRUSTED for label in seen)
        sensitive = any(label.sensitivity is Sensitivity.CONFIDENTIAL for label in seen)
        external = not str(event.payload.get("to", "")).endswith("@ourco.com")
        if untrusted and sensitive and external:
            return Decision(Action.REQUIRE_APPROVAL, reasons=("untrusted input + confidential data + external send",))
        return None


class ToyNoDrop:
    policy_id = "toy-no-drop"

    def evaluate(self, event, session):
        if event.kind is EventKind.TOOL_CALL and event.name == "run_sql":
            if "drop" in str(event.payload.get("query", "")).lower():
                return Decision(Action.BLOCK, reasons=("destructive SQL",))
        return None


class ToyPoisonedDescription:
    policy_id = "toy-poisoned-description"

    def evaluate(self, event, session):
        if event.kind is EventKind.TOOL_DESCRIPTION and "secretly" in event.payload["description"].lower():
            return Decision(Action.BLOCK, reasons=("tool description contains hidden instructions",))
        return None


def build():
    return [ToyTrifecta(), ToyNoDrop(), ToyPoisonedDescription()], [ToySourceLabeler()]
