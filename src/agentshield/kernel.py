"""Policy kernel: the one place every event passes through.

For each event the kernel:
  1. runs every `Labeler` so the event carries provenance labels (Problem 2),
  2. runs every `Policy` against the event and the session history (Problems 3, 4, 5),
  3. combines their verdicts — most severe wins — and applies the shield's mode,
  4. appends the event to the session and records event + decision in the audit log (Problem 6).

Policies are plain functions of (event, session history). They keep no state of
their own, so replaying a recorded session through the same policies gives the
same decisions.

Failures are closed: a labeler that crashes marks the content untrusted, and a
policy that crashes votes BLOCK.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Iterable, Protocol, Sequence

from .audit import AuditLog
from .model import Action, Decision, Event, Label, Mode, Trust

SEVERITY = {
    Action.ALLOW: 0,
    Action.WARN: 1,
    Action.REQUIRE_APPROVAL: 2,
    Action.BLOCK: 3,
    Action.TERMINATE: 4,
}


class Labeler(Protocol):
    """Attaches provenance labels to an event as it enters, e.g. tool results from a web fetch."""

    def label(self, event: Event) -> Iterable[Label]: ...


class Policy(Protocol):
    """Votes on one event. Return None for "no opinion". The kernel sets the mode, not the policy."""

    policy_id: str

    def evaluate(self, event: Event, session: Session) -> Decision | None: ...


@dataclass
class Session:
    session_id: str
    history: list[tuple[Event, Decision]] = field(default_factory=list)

    @property
    def events(self) -> list[Event]:
        return [event for event, _ in self.history]


class Shield:
    """Not thread-safe; use one Shield per worker or guard `check` externally."""

    def __init__(
        self,
        *,
        policies: Sequence[Policy] = (),
        labelers: Sequence[Labeler] = (),
        audit: AuditLog | None = None,
        mode: Mode = Mode.SHADOW,
    ) -> None:
        self.policies = list(policies)
        self.labelers = list(labelers)
        self.audit = audit
        self.mode = mode
        self._sessions: dict[str, Session] = {}

    def session(self, session_id: str) -> Session:
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(session_id)
        return self._sessions[session_id]

    def end_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def check(self, event: Event) -> Decision:
        event = self._apply_labelers(event)
        session = self.session(event.session_id)

        votes: list[tuple[str, Decision]] = []
        for policy in self.policies:
            try:
                vote = policy.evaluate(event, session)
            except Exception as e:
                vote = Decision(Action.BLOCK, reasons=(f"policy raised {e!r}",))
            if vote is not None:
                votes.append((policy.policy_id, vote))

        decision = combine(votes, self.mode)
        session.history.append((event, decision))
        if self.audit is not None:
            self.audit.record(event, decision)
        return decision

    def _apply_labelers(self, event: Event) -> Event:
        added: list[Label] = []
        for labeler in self.labelers:
            try:
                added.extend(labeler.label(event))
            except Exception:
                added.append(Label(f"labeler-error:{type(labeler).__name__}", Trust.UNTRUSTED))
        if not added:
            return event
        return dataclasses.replace(event, labels=event.labels + tuple(added))


def combine(votes: Sequence[tuple[str, Decision]], mode: Mode) -> Decision:
    """Most severe vote wins; every non-ALLOW vote's reasons are kept, tagged with its policy id."""
    if not votes:
        return Decision(Action.ALLOW, mode=mode)
    worst_id, worst = max(votes, key=lambda v: SEVERITY[v[1].action])
    reasons = tuple(
        f"{policy_id}: {reason}"
        for policy_id, vote in votes
        if vote.action is not Action.ALLOW
        for reason in vote.reasons
    )
    return Decision(worst.action, mode=mode, reasons=reasons, policy_id=worst_id)
