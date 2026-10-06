# 3. Status

**Last updated:** 2026-10-06 · **Phase:** foundation — shared core under team review

> Update this file in the same PR that changes a task's state. Status values: `Done`, `In review`, `In progress`, `Blocked`, `Not started`.

## At a glance

| Track | Owner | Done | In progress | Next up |
|---|---|---|---|---|
| Shared core + Problems 1, 6 | Bhoomi | Types, kernel, audit core | B1 contract review | B2 agent hook |
| Problems 2, 5 | Vibhas | — | — | V1 source labeler |
| Problems 3, 4 | Sahil | — | — | S1 tool manifest |

**Tests:** 22 passing (`tests/test_model.py`, `tests/test_audit.py`, `tests/test_kernel.py`).

## Task board

### Bhoomi — Problems 1 + 6 + shared core · [track](tracks/bhoomi-input-audit-core.md)

| ID | Task | Status | Where |
|---|---|---|---|
| B0a | Shared types (`model.py`) | Done | `main` · `ec745d7` |
| B0b | Audit log: hash chain, signed checkpoints, `verify()` | Done | `main` · `ec745d7` |
| B0c | Policy kernel + plug-in interfaces (`kernel.py`) | In review | `foundation` · `b89933f` |
| B0d | Knowledge base (`docs/`) | In review | `foundation` |
| B1 | Team review of the shared contract; freeze v0.1 | In progress | `foundation` PR |
| B2 | Agent hook (MCP proxy or LangGraph adapter) | Not started — waiting on O1 | |
| B3 | Problem 1: classifier as an advisory policy | Not started — needs O5 | |
| B4 | Checkpoint export + replay CLI | Not started | |
| B5 | Demo agent | Not started | |

### Vibhas — Problems 2 + 5 · [track](tracks/vibhas-provenance-session.md)

| ID | Task | Status | Where |
|---|---|---|---|
| V1 | Source-config labeler | Not started | |
| V2 | Session combination policy | Not started | |
| V3 | MCP tool-description labeler | Not started — needs O10 | |
| V4 | Argument matching | Not started — needs O8 | |

### Sahil — Problems 3 + 4 · [track](tracks/sahil-tools-egress.md)

| ID | Task | Status | Where |
|---|---|---|---|
| S1 | Tool capability manifest policy | Not started | |
| S2 | SQL classification with `sqlglot` | Not started | |
| S3 | Circuit breaker | Not started — "per turn" needs O9 | |
| S4 | Egress policy | Not started — best after V1, V4 | |

## Milestone M1 — flagship demo

A real agent reads a malicious resume, reads salaries, and tries to email an outside address.

| Must be true | Depends on | Status |
|---|---|---|
| The external email pauses for human approval | V1, V2, B2 | |
| An internal email goes through | V2 | |
| `DROP TABLE` is blocked | S1, S2, B2 | |
| The agent runs end to end through the hook | B2, B5 | |
| `verify()` passes on the audit log | B0b ✅ | Done |

From M1 on, measure latency (p50/p99) and false-positive rate against AgentDojo plus our own attack cases.

## Waiting on

| What | Blocks | Who |
|---|---|---|
| Vibhas + Sahil review the `foundation` PR | B1, and therefore everyone's first merge | Vibhas, Sahil |
| Decide first form factor (O1) | B2, B5, M1 | Bhoomi, with the team |
| Contract additions O5, O8, O9, O10 | B3, V4, S3, V3 | Raise in the `foundation` PR review |

## Done log

Newest first. One line per merged PR or significant commit.

| Date | What | Who | Ref |
|---|---|---|---|
| 2026-10-06 | Knowledge base | Bhoomi | `foundation` |
| 2026-10-03 | Policy kernel, plug-in interfaces, team plan | Bhoomi | `b89933f` |
| 2026-10-02 | Shared types, audit log, six problems | Bhoomi | `ec745d7` |
| — | Initial commit: research documents | Bhoomi | `fe6c797` |
