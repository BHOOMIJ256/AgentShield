from agentshield import (
    Action,
    AuditLog,
    Decision,
    Event,
    EventKind,
    Label,
    Mode,
    Sensitivity,
    Shield,
    Trust,
    verify,
)


def _event(kind=EventKind.TOOL_CALL, name="tool", session_id="s1", **payload):
    return Event(kind=kind, session_id=session_id, agent_id="agent", name=name, payload=payload)


class Vote:
    def __init__(self, policy_id, action, reason="because"):
        self.policy_id, self.action, self.reason = policy_id, action, reason

    def evaluate(self, event, session):
        return Decision(self.action, reasons=(self.reason,))


class NoOpinion:
    policy_id = "silent"

    def evaluate(self, event, session):
        return None


class Crashes:
    policy_id = "broken"

    def evaluate(self, event, session):
        raise RuntimeError("boom")


def test_no_votes_allows():
    assert Shield(policies=[NoOpinion()]).check(_event()).action is Action.ALLOW


def test_most_severe_vote_wins_and_reasons_are_kept():
    shield = Shield(policies=[Vote("a", Action.WARN, "odd"), Vote("b", Action.BLOCK, "bad"), Vote("c", Action.ALLOW)])
    decision = shield.check(_event())
    assert decision.action is Action.BLOCK
    assert decision.policy_id == "b"
    assert decision.reasons == ("a: odd", "b: bad")


def test_shield_mode_overrides_policy_mode():
    event = _event()
    shadow = Shield(policies=[Vote("a", Action.BLOCK)]).check(event)
    enforce = Shield(policies=[Vote("a", Action.BLOCK)], mode=Mode.ENFORCE).check(event)
    assert shadow.action is Action.BLOCK and shadow.enforced_action is Action.ALLOW
    assert enforce.enforced_action is Action.BLOCK


def test_crashing_policy_fails_closed():
    decision = Shield(policies=[Crashes()], mode=Mode.ENFORCE).check(_event())
    assert decision.enforced_action is Action.BLOCK
    assert "boom" in decision.reasons[0]


def test_crashing_labeler_marks_content_untrusted():
    class BadLabeler:
        def label(self, event, session):
            raise ValueError

    shield = Shield(labelers=[BadLabeler()])
    shield.check(_event())
    (event,) = shield.session("s1").events
    assert event.labels[0].trust is Trust.UNTRUSTED


def test_sessions_are_kept_apart():
    shield = Shield()
    shield.check(_event(session_id="s1"))
    shield.check(_event(session_id="s1"))
    shield.check(_event(session_id="s2"))
    assert len(shield.session("s1").history) == 2
    assert len(shield.session("s2").history) == 1
    shield.end_session("s1")
    assert shield.session("s1").history == []


def test_labeler_sees_earlier_events_but_not_the_current_one():
    seen = []

    class Spy:
        def label(self, event, session):
            seen.append([e.name for e in session.events])
            return ()

    shield = Shield(labelers=[Spy()])
    shield.check(_event(name="first"))
    shield.check(_event(name="second"))
    assert seen == [[], ["first"]]


def test_current_turn_starts_at_latest_user_input():
    shield = Shield()
    shield.check(_event(name="before"))
    assert [e.name for e in shield.session("s1").current_turn()] == ["before"]

    shield.check(_event(EventKind.USER_INPUT, "user", text="hi"))
    shield.check(_event(name="a"))
    shield.check(_event(EventKind.USER_INPUT, "user", text="again"))
    shield.check(_event(name="b"))
    assert [e.name for e in shield.session("s1").current_turn()] == ["user", "b"]


# --- Contract check: the interfaces are enough for each owner's problem. ---
# These toy versions only prove the plumbing; the real implementations live in each owner's module.

class ToyResumeLabeler:  # Problem 2 shape
    def label(self, event, session):
        if event.kind is EventKind.TOOL_RESULT and event.name == "read_resume":
            yield Label("tool:read_resume", Trust.UNTRUSTED)
        if event.kind is EventKind.TOOL_RESULT and event.name == "read_salaries":
            yield Label("db:salaries", Trust.TRUSTED, Sensitivity.CONFIDENTIAL)


class ToyTrifecta:  # Problem 5 shape
    policy_id = "trifecta"

    def evaluate(self, event, session):
        if not (event.kind is EventKind.TOOL_CALL and event.name == "send_email"):
            return None
        seen = [label for e in session.events for label in e.labels]
        untrusted = any(label.trust is Trust.UNTRUSTED for label in seen)
        sensitive = any(label.sensitivity is Sensitivity.CONFIDENTIAL for label in seen)
        external = not event.payload["to"].endswith("@ourco.com")
        if untrusted and sensitive and external:
            return Decision(Action.REQUIRE_APPROVAL, reasons=("untrusted input + confidential data + external send",))
        return None


def test_flagship_scenario_runs_through_the_contract(tmp_path):
    audit = AuditLog(tmp_path / "audit.jsonl")
    shield = Shield(policies=[ToyTrifecta()], labelers=[ToyResumeLabeler()], audit=audit, mode=Mode.ENFORCE)

    shield.check(_event(EventKind.TOOL_RESULT, "read_resume"))
    shield.check(_event(EventKind.TOOL_RESULT, "read_salaries"))
    internal = shield.check(_event(name="send_email", to="hiring@ourco.com"))
    external = shield.check(_event(name="send_email", to="leaks@competitor.com"))

    assert internal.enforced_action is Action.ALLOW
    assert external.enforced_action is Action.REQUIRE_APPROVAL
    assert verify(audit.path).entries == 4
