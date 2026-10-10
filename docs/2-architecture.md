# 2. Architecture

Everything AgentShield does is a rule running on four building blocks. Learn these four and every track makes sense.

| Block | What it does | Lives in | Owner |
|---|---|---|---|
| **Interception** | Turns what the agent does (tool calls, tool results, memory, messages) into `Event`s and applies the decision | `adapters/` (not built yet) | Bhoomi |
| **Labels** | Tag content with trust, sensitivity and origin when it enters | `model.py` (type), `provenance/` (labelers) | Vibhas |
| **Policy kernel** | Runs labelers and policies, combines votes into one `Decision`, applies shadow/enforce | `kernel.py` | Bhoomi |
| **Audit log** | Records every event and decision in a tamper-evident chain | `audit.py` | Bhoomi |

## How one event flows

```
 agent does something (calls a tool, gets a result, reads memory, messages another agent)
        │
        ▼
 adapter ─────────────► Event(kind, session_id, agent_id, name, payload, labels)
        │
        ▼
 Shield.check(event)
   1. labelers   each Labeler adds Labels to the event         ← Problem 2
   2. policies   each Policy votes: Decision or None            ← Problems 1, 3, 4, 5
   3. combine    most severe vote wins; Shield's mode applied
   4. session    (event, decision) appended to session.history
   5. audit      event + decision written to the hash chain     ← Problem 6
        │
        ▼
 Decision ──► adapter applies decision.enforced_action
              ALLOW / WARN            → let it through
              REQUIRE_APPROVAL        → pause, ask a human
              BLOCK                   → return an error to the agent
              TERMINATE               → error + end the session
```

## The shared contract

`model.py` and `kernel.py` are what all three of us build against. **Any change to them needs review from all three.**

### Data model — `src/agentshield/model.py`

**`Trust`** — decided by where content entered, never by what it says.

| Value | Meaning | Example |
|---|---|---|
| `TRUSTED` | Our own systems | System policy, internal database |
| `USER` | The authenticated human driving the session | The user's own message |
| `UNTRUSTED` | Anything else | Web pages, uploaded documents, emails, third-party tools |

**`Sensitivity`** — `PUBLIC`, `INTERNAL` (default), `CONFIDENTIAL`, `SECRET` (credentials, keys).

**`Label`** — a provenance tag, frozen.

| Field | Type | Example |
|---|---|---|
| `origin` | `str` | `"tool:read_resume"`, `"db:salaries"`, `"mcp:weather/get_forecast"` |
| `trust` | `Trust` | `Trust.UNTRUSTED` |
| `sensitivity` | `Sensitivity` | `Sensitivity.CONFIDENTIAL` |

**`EventKind`** — what happened. Each kind fixes what `name` and `payload` hold (decision D19), so every policy reads events the same way regardless of which adapter produced them:

| Kind | `name` | `payload` | Notes |
|---|---|---|---|
| `USER_INPUT` | `"user"` | `{"text": str}` | Starts a new turn. Not visible to an MCP proxy. |
| `TOOL_DESCRIPTION` | tool name | `{"server": str, "description": str, "input_schema": dict}` | One per tool when the agent lists a server's tools |
| `TOOL_CALL` | tool name | the tool's arguments, exactly as the agent sent them | Which argument holds a query or recipient is per-tool config in the policy |
| `TOOL_RESULT` | tool name | `{"content": ..., "is_error": bool}` | |
| `MEMORY_READ` / `MEMORY_WRITE` | memory key | `{"value": ...}` | |
| `AGENT_MESSAGE` | receiving agent | `{"content": ...}` | Sender is `agent_id` |

**`Event`** — one thing the agent did or received, frozen.

| Field | Type | Meaning |
|---|---|---|
| `kind` | `EventKind` | What happened |
| `session_id` | `str` | The conversation it belongs to |
| `agent_id` | `str` | Which agent |
| `name` | `str` | Tool name, memory key, or target agent |
| `payload` | `Mapping[str, Any]` | Per kind, see the table above |
| `labels` | `tuple[Label, ...]` | Provenance tags (labelers add more) |
| `event_id`, `timestamp` | `str`, `float` | Filled in automatically |

`Event.from_dict`, `Label.from_dict` and `Decision.from_dict` rebuild objects from what the audit log recorded — used by replay.

**`Action`**, in order of severity: `ALLOW` < `WARN` < `REQUIRE_APPROVAL` < `BLOCK` < `TERMINATE`.

**`Mode`** — `SHADOW` (default: record what would have happened, let everything through) or `ENFORCE`.

**`Decision`** — `action`, `mode`, `reasons`, `policy_id`. Its `enforced_action` property is what actually happens: always `ALLOW` in shadow mode, otherwise `action`.

### Plug-in points — `src/agentshield/kernel.py`

```python
class Labeler(Protocol):
    def label(self, event: Event, session: Session) -> Iterable[Label]: ...

class Policy(Protocol):
    policy_id: str
    def evaluate(self, event: Event, session: Session) -> Decision | None: ...

@dataclass
class Session:
    session_id: str
    history: list[tuple[Event, Decision]]   # every earlier event in this session, with its decision
    events: list[Event]                      # property: just the events
    def current_turn(self) -> list[Event]    # events from the latest USER_INPUT onward
```

Both labelers and policies see the session **as it was before the current event** — the current event is appended after the decision. Labelers get the session (decision D17) so a labeler can tag a tool call whose arguments repeat text from an earlier untrusted result.

`Shield(policies=..., labelers=..., audit=..., mode=Mode.SHADOW)` runs them. `combine(votes, mode)` is the vote-merging rule, exposed so it can be tested on its own.

### Rules for anything you plug in

1. **Return a `Decision`, or `None` for "no opinion".** Never raise an exception to block something — a raised exception counts as a crash.
2. **Never set the mode.** Return `Decision(Action.BLOCK, reasons=(...,))`; the Shield decides whether that is enforced.
3. **Keep no state of your own.** Read everything from `event` and `session.history`. This is what makes replay give the same answer twice.
4. **Return nothing for event kinds you don't handle.** Every labeler and policy sees every event.
5. **Give a human-readable reason.** It ends up in the audit log and on the approval screen.

### What the kernel guarantees

- **Most severe vote wins.** Ties go to the first policy registered. Reasons from every non-`ALLOW` vote are kept, prefixed with the policy id.
- **Fails closed.** A policy that raises votes `BLOCK`, with the exception as the reason. A labeler that raises adds a `labeler-error:<ClassName>` label with `Trust.UNTRUSTED`.
- **Everything is recorded.** If an `AuditLog` is attached, every event and its decision is written, including shadow-mode "would have blocked" decisions.

## Audit log — `src/agentshield/audit.py`

One JSON object per line:

```json
{"seq": 0, "prev": "000…000", "body": {"event": {...}, "decision": {...}, "enforced_action": "allow"}, "hash": "9f2c…"}
```

- `hash = sha256(canonical_json({"seq", "prev", "body"}))`; `prev` is the previous entry's hash, `"0" * 64` for the first.
- `verify(path)` walks the chain and reports the first bad `seq`. It catches **edited, deleted and reordered** lines.
- It **cannot** catch the end being cut off, or the whole file being rebuilt by someone holding it. For that: `sign_checkpoint(log, private_key)` signs the current `(seq, hash)` with Ed25519; store it somewhere the agent host can't write; then `verify(path, checkpoint=..., public_key=...)` proves the log still contains that exact entry.
- `read_entries(path)` yields the entries in order, without checking the chain; rebuild objects with `Event.from_dict(entry.body["event"])` and `Decision.from_dict(entry.body["decision"])`.
- Values that aren't JSON (datetimes, sets) are stored as strings, so they come back as strings.
- One writer per file. A half-written last line makes `AuditLog(path)` raise `AuditLogCorrupted` rather than continue a broken chain.

## Code layout

```
src/agentshield/
  model.py            shared types                          Bhoomi (contract)
  kernel.py           Shield, Labeler, Policy, Session      Bhoomi (contract)
  audit.py            hash chain, checkpoints, verify       Bhoomi
  provenance/         labelers                              Vibhas   (planned)
  policies/
    session.py        session combination (trifecta)        Vibhas   (planned)
    tools.py          tool manifest, SQL, circuit breaker   Sahil    (planned)
    egress.py         outbound data check                   Sahil    (planned)
  input/              Problem 1 classifier policy           Bhoomi   (planned)
  adapters/           MCP proxy / LangGraph adapter         Bhoomi   (planned)
demo/                 flagship demo agent                   Bhoomi   (planned)
tests/                one test file per module
```

The layout is designed so that the three of us rarely edit the same file.

## Writing a labeler

```python
from agentshield import EventKind, Label, Sensitivity, Trust

class SourceLabeler:
    def __init__(self, sources: dict[str, tuple[Trust, Sensitivity]]):
        self.sources = sources

    def label(self, event, session):
        if event.kind is not EventKind.TOOL_RESULT:
            return
        trust, sensitivity = self.sources.get(event.name, (Trust.UNTRUSTED, Sensitivity.INTERNAL))
        yield Label(f"tool:{event.name}", trust, sensitivity)
```

## Writing a policy

```python
from agentshield import Action, Decision, EventKind

class NoDeletes:
    policy_id = "no-deletes"

    def evaluate(self, event, session):
        if event.kind is EventKind.TOOL_CALL and event.name == "delete_file":
            return Decision(Action.BLOCK, reasons=("file deletion is not allowed for this agent",))
        return None
```

## Testing one

Build the events by hand — including hand-written labels — so you never wait for someone else's labeler:

```python
from agentshield import Action, Event, EventKind, Mode, Shield

def test_delete_is_blocked():
    shield = Shield(policies=[NoDeletes()], mode=Mode.ENFORCE)
    event = Event(kind=EventKind.TOOL_CALL, session_id="s1", agent_id="a", name="delete_file", payload={"path": "/x"})
    assert shield.check(event).enforced_action is Action.BLOCK
```

`tests/test_kernel.py::test_flagship_scenario_runs_through_the_contract` is a complete worked example: a toy labeler and a toy trifecta policy running the resume → salaries → email scenario.

## Known gaps in the current core

Tracked in [Decisions](4-decisions.md):

- One **global** shadow/enforce mode; no per-policy mode yet (O4).
- `Shield` is not thread-safe; sessions live in memory until `end_session()`.
- An MCP proxy never sees the user's message, so `current_turn()` is the whole session there. Per-turn limits only work with an adapter that emits `USER_INPUT` (e.g. LangGraph).

Closed in contract v0.1 (2026-10-10): user input and tool-description event kinds, labelers seeing the session, turn boundaries, payload conventions, loading events back from the log — decisions D15–D19.
