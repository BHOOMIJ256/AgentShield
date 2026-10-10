# Track: Input, Audit + Shared Core — Bhoomi

**Problems:** 1 (someone types something nasty) + 6 (nobody can prove what happened), plus the shared core and integration
**Covers components:** #1 Ingress guardrail, #7 Audit & replay, #13 Explainability (approval screen)
**OWASP:** ASI01 (input side), ASI09 Human-agent trust exploitation; the audit log supports all ten

## Your mission

Three jobs:

1. **Own the shared contract** (`model.py`, `kernel.py`) so Vibhas and Sahil can build in parallel without breaking each other.
2. **Connect AgentShield to a real agent** — the hook that turns tool calls into events and applies decisions. Nothing is demonstrable without it.
3. **Problems 1 and 6** — plug in an existing input classifier, and finish the audit log into something a compliance reviewer can rely on.

## Tasks

| ID | Task | Done when | Depends on |
|---|---|---|---|
| B0 | Shared types, kernel, audit core, knowledge base, contract v0.1 additions | ✅ Done / in review | — |
| **B1** | **Contract review; freeze v0.1** | Vibhas and Sahil have approved the `foundation` PR | Their review |
| **B2** | **MCP proxy** (D14) | Real tool calls, results and tool descriptions become `Event`s; `enforced_action` is applied; `REQUIRE_APPROVAL` pauses for a human | Contract v0.1 |
| B3 | Problem 1: classifier as an advisory policy | Prompt Guard / LLM Guard result appears in the decision reasons; votes `WARN` only | Contract v0.1 (`USER_INPUT`) |
| B4 | Audit remainder: checkpoint export + replay CLI | A recorded session can be re-run through current policies and the decisions compared | O6 |
| B5 | Demo agent | Runs the flagship scenario and `DROP TABLE` end to end | B2, V1, V2, S1, S2 |

## Files you own

```
src/agentshield/model.py          contract — changes need all three reviews
src/agentshield/kernel.py         contract — changes need all three reviews
src/agentshield/audit.py
src/agentshield/input/            B3
src/agentshield/adapters/         B2
demo/                             B5
```

## B1 — contract review

The known gaps were settled before review, in the same `foundation` PR (contract v0.1, decisions D15–D19): `USER_INPUT` and `TOOL_DESCRIPTION` event kinds, labelers receive the session, `Session.current_turn()`, fixed payload shapes, and `from_dict` loaders for replay. What's left is Vibhas's and Sahil's approval.

## B2 — the MCP proxy

**Decided (D14): MCP proxy first.** It works on agents whose code nobody controls (Claude Code, Cursor) and sees everything crossing the tool boundary — enough for the flagship scenario.

What it must do:

| Agent side | AgentShield side |
|---|---|
| `tools/list` response | One `Event(TOOL_DESCRIPTION, name=tool, payload={"server", "description", "input_schema"})` per tool |
| `tools/call` request | `Event(TOOL_CALL, name=tool, payload=arguments)` → `Shield.check` |
| `tools/call` response | `Event(TOOL_RESULT, name=tool, payload={"content", "is_error"})` → labelers tag it |
| `ALLOW` / `WARN` | Forward the call |
| `REQUIRE_APPROVAL` | Hold the call; ask a human; show the **real tool trace**, not the agent's summary (component #13) |
| `BLOCK` | Return a tool error to the agent with the reasons |
| `TERMINATE` | Return an error and `end_session` |

The proxy never sees the user's message, so it emits no `USER_INPUT` events — Problem 1 (B3) needs an adapter that does, such as the LangGraph one.

The LangGraph adapter comes second: wrap the tool node, and use LangGraph's `interrupt()` for approval.

## B3 — Problem 1

- A policy that runs on `USER_INPUT` events, calls Prompt Guard or LLM Guard, and votes `WARN` with the classifier's score in the reason. Never `BLOCK` (decision D3).
- Heavy model dependency → optional extra `[input]`.
- `Components/Malicious_User_Input.md` is empty — use it, or this track, for notes on which classifier and why.

## B4 — finishing Problem 6

- **Checkpoint export (O6):** sign every N entries and on session end; write to a location the agent host can't modify. Keep the private key off the agent host.
- **Replay CLI:** read a log → rebuild `Event`s → run them through a `Shield` with the current policies → print where decisions differ. The loaders exist: `read_entries(path)` + `Event.from_dict` / `Decision.from_dict`.
- Replay is what turns every attack we see into a regression test.

## B5 — demo agent

Fixtures: a resume with a hidden instruction, a salaries table, an email tool, a database tool. Scenarios: the trifecta (external email pauses, internal passes) and `DROP TABLE` (blocked). Finish by running `verify()` on the audit log. This is milestone M1.

## Coordination points

| With | About |
|---|---|
| Vibhas | The proxy produces the `TOOL_DESCRIPTION` and `TOOL_RESULT` events his labelers tag. The demo needs V1 + V2. |
| Sahil | The proxy produces the `TOOL_CALL` events his policies check. The demo needs S1 + S2. |
| Both | Any contract change: you open the PR, both review. |

## References

- [Architecture](../2-architecture.md) — the contract you own
- [Decisions](../4-decisions.md) — open questions you own: O4, O6
- [Facts.md](../../Facts.md) — why the MCP proxy, why evidence matters to buyers
