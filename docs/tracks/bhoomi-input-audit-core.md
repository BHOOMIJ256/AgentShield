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
| B0 | Shared types, kernel, audit core, knowledge base | ✅ Done / in review | — |
| **B1** | **Contract review; freeze v0.1** | Vibhas and Sahil have approved the `foundation` PR | Their review |
| **B2** | **Agent hook** (MCP proxy or LangGraph adapter) | Real tool calls and results become `Event`s; `enforced_action` is applied; `REQUIRE_APPROVAL` pauses for a human | O1 |
| B3 | Problem 1: classifier as an advisory policy | Prompt Guard / LLM Guard result appears in the decision reasons; votes `WARN` only | O5 |
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

## B1 — what to raise in the contract review

Collect the known gaps (see [Architecture](../2-architecture.md#known-gaps-in-the-current-core)) and settle as many as possible in the same PR, before anyone builds on the contract:

- **O5** `EventKind.USER_INPUT` — needed by B3, and gives S3 its turn boundary (O9).
- **O8** should labelers see the session?
- **O10** how MCP tool listings appear as events.
- **O12** how tool arguments are named in `payload`.

## B2 — the agent hook

**Recommendation (O1): MCP proxy first.** It works on agents whose code nobody controls (Claude Code, Cursor) and sees everything crossing the tool boundary — enough for the flagship scenario.

What it must do:

| Agent side | AgentShield side |
|---|---|
| `tools/call` request | `Event(TOOL_CALL, name=tool, payload=arguments)` → `Shield.check` |
| `tools/call` response | `Event(TOOL_RESULT, name=tool, payload=result)` → labelers tag it |
| `tools/list` response | Decide with Vibhas (O10) |
| `ALLOW` / `WARN` | Forward the call |
| `REQUIRE_APPROVAL` | Hold the call; ask a human; show the **real tool trace**, not the agent's summary (component #13) |
| `BLOCK` | Return a tool error to the agent with the reasons |
| `TERMINATE` | Return an error and `end_session` |

The LangGraph adapter comes second: wrap the tool node, and use LangGraph's `interrupt()` for approval.

## B3 — Problem 1

- A policy that runs on `USER_INPUT` events (after O5), calls Prompt Guard or LLM Guard, and votes `WARN` with the classifier's score in the reason. Never `BLOCK` (decision D3).
- Heavy model dependency → optional extra `[input]`.
- `Components/Malicious_User_Input.md` is empty — use it, or this track, for notes on which classifier and why.

## B4 — finishing Problem 6

- **Checkpoint export (O6):** sign every N entries and on session end; write to a location the agent host can't modify. Keep the private key off the agent host.
- **Replay CLI:** read a log → rebuild `Event`s → run them through a `Shield` with the current policies → print where decisions differ. Needs an `Event`-from-dict loader (not built yet).
- Replay is what turns every attack we see into a regression test.

## B5 — demo agent

Fixtures: a resume with a hidden instruction, a salaries table, an email tool, a database tool. Scenarios: the trifecta (external email pauses, internal passes) and `DROP TABLE` (blocked). Finish by running `verify()` on the audit log. This is milestone M1.

## Coordination points

| With | About |
|---|---|
| Vibhas | O8, O10 — contract changes for V3/V4. The demo needs V1 + V2. |
| Sahil | O9, O12 — turn boundaries and tool argument naming. The demo needs S1 + S2. |
| Both | Any contract change: you open the PR, both review. |

## References

- [Architecture](../2-architecture.md) — the contract you own
- [Decisions](../4-decisions.md) — open questions you own: O1, O4, O5, O6
- [Facts.md](../../Facts.md) — why the MCP proxy, why evidence matters to buyers
