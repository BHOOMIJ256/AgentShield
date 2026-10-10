"""Human approval for decisions that REQUIRE_APPROVAL.

The answer must come from a person, through a channel the agent cannot reach. MCP
elicitation is deliberately not used: it travels back through the agent's own
client, which may answer it automatically.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, Sequence

import anyio

from ..model import Decision, Event

_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class ApprovalRequest:
    event: Event
    decision: Decision
    trace: tuple[Event, ...]  # earlier events in the session, oldest first — what actually happened


class Approver(Protocol):
    name: str

    async def decide(self, request: ApprovalRequest) -> bool: ...


class DenyAll:
    """Used when no approval channel is configured: anything needing approval is refused."""

    name = "deny-all"

    async def decide(self, request: ApprovalRequest) -> bool:
        return False


def summarize(request: ApprovalRequest) -> dict[str, Any]:
    """What the human sees: the real call and the real trace, not the agent's account of it."""

    def labels(event: Event) -> list[str]:
        return [f"{l.origin} ({l.trust.value}, {l.sensitivity.value})" for l in event.labels]

    return {
        "id": request.event.event_id,
        "agent": request.event.agent_id,
        "session": request.event.session_id,
        "kind": request.event.kind.value,
        "tool": request.event.name,
        "payload": request.event.payload,
        "labels": labels(request.event),
        "policy": request.decision.policy_id,
        "reasons": list(request.decision.reasons),
        "trace": [
            {"kind": e.kind.value, "name": e.name, "labels": labels(e), "payload": _preview(e.payload)}
            for e in request.trace
        ],
    }


def _preview(payload: Any, limit: int = 300) -> str:
    text = json.dumps(payload, default=str, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + "…"


class FileApprover:
    """Writes each request to `<directory>/<id>.json` and waits for a human to answer with
    `agentshield-approve approve <id>` or `deny <id>`. No answer before the timeout means deny.

    Put the directory somewhere the agent's tools cannot write to.
    """

    name = "file"

    def __init__(self, directory: str | Path, *, timeout: float = 300.0, poll_interval: float = 0.5) -> None:
        self.directory = Path(directory)
        self.timeout = timeout
        self.poll_interval = poll_interval

    async def decide(self, request: ApprovalRequest) -> bool:
        request_id = request.event.event_id
        if not _SAFE_ID.match(request_id):
            return False
        self.directory.mkdir(parents=True, exist_ok=True)
        pending = self.directory / f"{request_id}.json"
        markers = {True: self.directory / f"{request_id}.approved", False: self.directory / f"{request_id}.denied"}
        pending.write_text(json.dumps(summarize(request), indent=2, default=str), encoding="utf-8")
        try:
            with anyio.move_on_after(self.timeout):
                while True:
                    for answer, marker in markers.items():
                        if marker.exists():
                            return answer
                    await anyio.sleep(self.poll_interval)
            return False
        finally:
            pending.unlink(missing_ok=True)
            for marker in markers.values():
                marker.unlink(missing_ok=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agentshield-approve", description="Answer pending AgentShield approvals.")
    parser.add_argument("--dir", required=True, help="the approvals directory given to the proxy")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="show pending requests")
    for command in ("show", "approve", "deny"):
        sub.add_parser(command).add_argument("id")
    args = parser.parse_args(argv)

    directory = Path(args.dir)
    if args.command == "list":
        pending = sorted(directory.glob("*.json"), key=lambda p: p.stat().st_mtime) if directory.exists() else []
        if not pending:
            print("no pending approvals")
        for path in pending:
            request = json.loads(path.read_text(encoding="utf-8"))
            print(f"{request['id']}  {request['agent']}  {request['tool']}  — {'; '.join(request['reasons'])}")
        return 0

    if not _SAFE_ID.match(args.id) or not (directory / f"{args.id}.json").exists():
        print(f"no pending approval with id {args.id!r}", file=sys.stderr)
        return 1
    if args.command == "show":
        print((directory / f"{args.id}.json").read_text(encoding="utf-8"))
        return 0
    answer = "approved" if args.command == "approve" else "denied"
    (directory / f"{args.id}.{answer}").touch()
    print(f"{answer} {args.id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
