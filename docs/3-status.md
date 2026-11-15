# 3. Status

**Last updated:** 2026-11-15 · **Phase:** first real policies built on branches; nothing merged into `main` yet

> Update this file in the same PR that changes a task's state. Status values: `Done`, `Built — not merged`, `In review`, `In progress`, `Blocked`, `Not started`.

## At a glance

| Track | Owner | Done / built | Gaps found in review | Next up |
|---|---|---|---|---|
| Shared core + Problems 1, 6 | Bhoomi | Types, kernel, audit log, contract v0.1, MCP proxy + approvals | PR #1 still open — `main` has no code | Merge PR #1; demo agent (B5) |
| Problems 2, 5 | Vibhas | Source tagging (V1), trifecta rule (V2), MCP description tagging (V3) | Internal email is wrongly stopped; no tests; files outside the agreed folders | Fix V2 by destination; tests; PR |
| Problems 3, 4 | Sahil | AI-model review policies (S5), LangGraph node (S6) — outside the original plan | The hard rules (S1, S2) aren't built, so `DROP TABLE` is not truly blocked; LangGraph node skips tool results | PR; then SQL check (S2) |

**Tests:** 44 passing on `foundation`; 59 passing on Vibhas's branch, which contains everyone's work.

## Where the code is

Nothing has reached `main` yet. Every branch is stacked on the one before it:

```
main (documents only)
 └─ foundation ................ PR #1 → main, open since 2026-10-03
     ├─ bhoomi/mcp-proxy ...... PR #2 → foundation, merged 2026-10-10
     └─ sahil/tools-egress .... def01e8 · 2026-11-08 · no PR yet
         └─ vibhas/provenance-tags-&-lethal3 ... 30f678f · 2026-11-15 · no PR yet
```

Because Vibhas's branch was made from Sahil's, merging Vibhas's work also merges Sahil's. Merge order matters — see [Next steps](#next-steps).

## Task board

### Bhoomi — Problems 1 + 6 + shared core · [track](tracks/bhoomi-input-audit-core.md)

| ID | Task | Status | Where |
|---|---|---|---|
| B0a | Shared types (`model.py`) | Done | `main` · `ec745d7` |
| B0b | Audit log: hash chain, signed checkpoints, `verify()` | Done | `main` · `ec745d7` |
| B0c | Policy kernel + plug-in interfaces (`kernel.py`) | In review — PR #1 | `foundation` · `b89933f` |
| B0d | Knowledge base (`docs/`) | In review — PR #1 | `foundation` · `1539516` |
| B0e | Contract v0.1 additions (D15–D19) | In review — PR #1 | `foundation` · `e65cb01` |
| B1 | Team review of the shared contract; freeze v0.1 | In progress — both teammates have now built on it; needs their approval on PR #1 | PR #1 |
| B2 | MCP proxy (D14): `ToolGate`, out-of-band approvals (D20), hidden poisoned tools (D21), `agentshield-mcp-proxy`, `agentshield-approve` | Done — merged into `foundation` | PR #2 · `7cd66e9` |
| B3 | Problem 1: jailbreak classifier as an advisory policy | Not started — needs an adapter that emits `USER_INPUT` (B6) | |
| B4 | Checkpoint export + replay CLI | Not started — must reuse recorded decisions for AI-model policies (see S5) | |
| B5 | Demo agent | Not started | |
| B6 | One LangGraph adapter built on `ToolGate` (calls **and** results), replacing S6 | Not started — agree with Sahil | |

### Vibhas — Problems 2 + 5 · [track](tracks/vibhas-provenance-session.md)

| ID | Task | Status | Where |
|---|---|---|---|
| V1 | Source-config labeler (`SourceLabeler`) | Built — not merged. Matches the contract; unknown sources default to untrusted. No tests. | `30f678f` · `src/agentshield/vibhas/sources.py` |
| V2 | Session combination policy (`SessionCombinationPolicy`) | Built — not merged. **Too strict:** treats every call to a listed tool as external, so an email to `hiring@ourco.com` is stopped too. No tests. | `30f678f` · `src/agentshield/vibhas/session.py` |
| V3 | MCP tool-description labeler (`MCPLabeler`) | Built — not merged. No tests. | `30f678f` · `src/agentshield/vibhas/mcp.py` |
| V4 | Argument matching (labels on outbound calls) | Not started — Sahil's deterministic egress check (S4) needs it | |

### Sahil — Problems 3 + 4 · [track](tracks/sahil-tools-egress.md)

| ID | Task | Status | Where |
|---|---|---|---|
| S1 | Tool capability manifest policy | Not started | |
| S2 | SQL classification with `sqlglot` (unparseable → `BLOCK`) | Not started — **needed for M1** | |
| S3 | Circuit breaker | Not started | |
| S4 | Deterministic egress policy (labels + destinations + patterns) | Not started — needs V4 and the shared destination list (O11) | |
| S5 | AI-model review policies: `LLMToolGuardPolicy` (P3), `LLMEgressPolicy` (P4) — *added outside the original plan* | Built — not merged. 16 tests with a fake model; **never run against a real model**. Follows D3/D4: votes at most `REQUIRE_APPROVAL`, fails closed. | `def01e8` · `src/agentshield/policies/llm.py` |
| S6 | LangGraph node `make_shield_node` — *added outside the original plan* | Built — not merged. **Checks tool calls only; tool results never pass through the shield**, so nothing gets tagged and the trifecta can't fire on this path. Sits in `adapters/` (Bhoomi's area). | `def01e8` · `src/agentshield/adapters/langgraph.py` |

## Review findings — 2026-11-15

What was checked: every teammate commit read; full test suite run on the combined branch (59 pass); the flagship scenario run through the MCP proxy with **Vibhas's real code** instead of the test stand-ins.

**Working**

- The core idea works end to end with real code: resume tagged untrusted → salary table tagged confidential → email to `job-leaks@competitor.com` paused for a human, refused, recorded; the audit log verified.
- Sahil's AI-model policies keep to the agreed rules: they never block on their own, a model failure asks a human, and confidential tags are given to the model as facts.

**Needs fixing before M1**

| # | Finding | Owner |
|---|---|---|
| F1 | PR #1 has been open six weeks. `main` has no code and every branch stacks on `foundation`. | Bhoomi (merge) · Vibhas + Sahil (approve) |
| F2 | The trifecta rule decides "external" by tool name, not recipient, so the internal email in M1 is stopped. Decide by destination using one shared internal-destinations list (O11). | Vibhas, with Sahil |
| F3 | No deterministic `DROP TABLE` check exists. The AI-model guard can only ask for approval, and needs a real model to run at all. | Sahil (S2) |
| F4 | The LangGraph node only sees tool calls. Results must go through the shield too, or provenance tagging does nothing on LangGraph. Two adapters doing the same job should become one, on `ToolGate`. | Bhoomi + Sahil (B6) |
| F5 | Vibhas's files are in `src/agentshield/vibhas/` instead of `provenance/` and `policies/session.py`; the folder has no `__init__.py`; there are no tests. | Vibhas |
| F6 | Replay can't re-ask an AI model and expect the same answer. Replay must reuse the recorded decision for those policies — needs a decision entry. | Sahil + Bhoomi |
| F7 | AI-model policies were added without a decision entry or a status update; Sahil's notes are in `sahil_knowledge.md` at the repo root instead of his track doc. | Sahil |
| F8 | Vibhas's branch contains Sahil's unmerged commit. Rebase onto `main` once Sahil's work is merged. | Vibhas |

## Milestone M1 — flagship demo

A real agent reads a malicious resume, reads salaries, and tries to email an outside address.

| Must be true | Depends on | Status |
|---|---|---|
| The external email pauses for human approval | V1, V2, B2 | ✅ Works with Vibhas's real code (not merged) |
| An internal email goes through | V2 | ❌ Real code stops it too (F2) |
| `DROP TABLE` is blocked | S1, S2, B2 | ❌ Only with test stand-ins (F3) |
| The agent runs end to end through the hook | B2, B5 | 🟡 Proxy works; demo agent not started |
| `verify()` passes on the audit log | B0b | ✅ Done |

From M1 on, measure latency (p50/p99) and false-positive rate against AgentDojo plus our own attack cases.

## Next steps

### Phase A — get a stable `main` (this week)

Order matters: each step needs the one before it.

| # | Who | Step | Done when |
|---|---|---|---|
| A1 | Vibhas, Sahil | Approve PR #1 on GitHub. You have both built on it, so the review is mostly done; raise anything you'd change in the contract now. | Two approvals on PR #1 |
| A2 | Bhoomi | Merge PR #1 into `main`; delete `foundation`. | `main` has the core, proxy and docs |
| A3 | Sahil | Rebase `sahil/tools-egress` onto `main`. Move `sahil_knowledge.md` into `docs/tracks/sahil-tools-egress.md`; add a decision entry for AI-model policies and how replay handles them (F6, F7); update this file. Open a PR into `main`. | PR open, tests pass |
| A4 | Bhoomi, Sahil | Agree what happens to the LangGraph node (F4): merge S6 as-is and replace it in B6, or hold it back. | Decided in the PR |
| A5 | Vibhas | After Sahil's PR merges, rebase onto `main`. Move files: `vibhas/sources.py` → `provenance/sources.py`, `vibhas/mcp.py` → `provenance/mcp.py`, `vibhas/session.py` → `policies/session.py`. Add tests (see the list in your track doc). Update this file. Open a PR. | PR open, tests pass |

### Phase B — reach M1

| # | Who | Step | Done when |
|---|---|---|---|
| B-1 | Vibhas + Sahil | Agree one shared internal-destinations config (O11) — one module both policies import. | Decision entry; module merged |
| B-2 | Vibhas | Fix V2: "external" means the recipient/URL is outside the internal list, not just the tool name (F2). | Internal email passes, external pauses — with tests |
| B-3 | Sahil | S2: SQL check with `sqlglot`; unparseable, multi-statement or unknown statements → `BLOCK` (D7). Then S1 manifest. | `DROP TABLE` blocked by a deterministic policy |
| B-4 | Bhoomi | B5: demo agent through the MCP proxy using the real V1, V2, S1, S2. | All five M1 rows ✅ |
| B-5 | Vibhas | V4: tag outbound calls whose arguments contain text from untrusted or confidential results. | Outbound email carries the salary table's label |
| B-6 | Sahil | S4: deterministic egress check reading V4's labels; run S5 once against a real model and record results. | Salary text to an outside address stopped without the model |
| B-7 | Bhoomi | B6: one LangGraph adapter on `ToolGate` (calls and results), then B3 on top of it. | Trifecta fires on LangGraph too |

### Every week

30-minute sync: walk the M1 table and the findings above; each person updates their rows here in their own PR.

## Waiting on

| What | Blocks | Who |
|---|---|---|
| Approvals on PR #1 | Every merge into `main` | Vibhas, Sahil |
| Shared internal-destinations config (O11) | V2 fix, S4 | Vibhas + Sahil |
| Decision on the LangGraph node (F4) | B6, B3 | Bhoomi + Sahil |

## Done log

Newest first. One line per merged PR or significant commit.

| Date | What | Who | Ref |
|---|---|---|---|
| 2026-11-15 | Review of all branches; status, findings and next steps | Bhoomi | `foundation` |
| 2026-11-15 | Source tagging, trifecta rule, MCP description tagging (V1–V3) — not merged | Vibhas | `30f678f` |
| 2026-11-08 | AI-model review policies, LangGraph node (S5, S6) — not merged | Sahil | `def01e8` |
| 2026-10-10 | MCP proxy merged into `foundation` | Bhoomi | PR #2 · `991a32f` |
| 2026-10-10 | MCP proxy, approval channel; decisions D20–D21 | Bhoomi | `7cd66e9` |
| 2026-10-10 | Contract v0.1 additions; decisions D14–D19 | Bhoomi | `e65cb01` |
| 2026-10-06 | Knowledge base | Bhoomi | `1539516` |
| 2026-10-03 | Policy kernel, plug-in interfaces, team plan; PR #1 opened | Bhoomi | `b89933f` |
| 2026-10-02 | Shared types, audit log, six problems | Bhoomi | `ec745d7` |
| — | Initial commit: research documents | Bhoomi | `fe6c797` |
