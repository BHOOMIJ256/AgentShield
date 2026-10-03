# Phase 2 — From 16 Components to a Buildable Plan

Source documents: the original design PDF, [Facts.md](Facts.md), [Simpler_Idea.md](Simpler_Idea.md), [16 Components](Components/16_Components(Sahil).md), [6 Problems](Components/6_Catgeories.md).

---

## 1. The decision

AgentShield is **not** sixteen components. It is six problems, of which:

- **two are ours to win** — Problem 2 (provenance tags) and Problem 5 (session combination), which are one engine seen from two sides;
- **three are table stakes** — Problem 3 (destructive actions), Problem 4 (data leaving), Problem 6 (audit);
- **one we borrow** — Problem 1 (nasty user input).

Pitch:

> AgentShield tracks where every piece of an agent's context came from, stops untrusted content from combining with sensitive data into an external action, and keeps a record your compliance team can verify.

---

## 2. Where the 16 components went

| Problem | Components | Note |
|---|---|---|
| 1. Someone types something nasty | #1 | Plug in Prompt Guard / LLM Guard. Do not build. |
| 2. Something the agent reads contains instructions | #2, #6, #10, #11, #12 | Memory, MCP tool descriptions and inter-agent messages are all *content the agent reads*. One tagging system covers all of them. |
| 3. The agent does something destructive | #3, #8, #16 | Runaway loops and generated code are destructive actions too. Sandbox is integrated (E2B / gVisor / Firecracker), not built. |
| 4. Sensitive data leaves the building | #4, #5 | A leaked secret is just another sensitive payload. |
| 5. The combination no single check can see | #9, #11 | Delegation is Problem 5 across agents — the tally must follow the task across a handoff. |
| 6. Nobody can prove what happened | #7, #13 | Cheap #13: the approval UI shows the real tool trace, not the agent's own summary. |
| Out of scope for now | #14, #15 | Not runtime problems for this product. Drift returns later on top of shadow-mode data. |

---

## 3. Four building blocks

Every problem above is a rule running on the same four primitives:

1. **Interception points** — tool call, tool result, MCP, memory read/write, agent-to-agent message.
2. **Labels** — trust, sensitivity and origin attached to content when it enters, carried forward.
3. **Deterministic policy kernel** — `Event + Labels → Decision` (`ALLOW / WARN / REQUIRE_APPROVAL / BLOCK / TERMINATE`), with **shadow mode as the default**. LLM or classifier output is only ever an advisory input to this function, never the decision itself.
4. **Hash-chained audit log** — every event and decision, tamper-evident, with signed checkpoints.

---

## 4. Corrections to the six-problem framing

These are the places where the framing will get challenged. Build them in from day one.

- **Problems 2 and 5 are one differentiator, not two.** A tag blocks nothing on its own; the session tally is what consumes it. Sell them together.
- **Tags move false positives, they don't remove them.** A recruiter emailing a candidate an offer with a salary band is untrusted input + sensitive data + external action — and legitimate. Mitigations: three flags → `REQUIRE_APPROVAL`, never `BLOCK`; shadow mode by default; per-agent destination allowlists; track approval volume to catch approval fatigue.
- **"Never wrong" for SQL is false unless parse failure means deny.** Dialect quirks, multi-statement payloads, `EXEC`, stored procedures and CTEs hiding a `DELETE` all exist. Rule: *if the parser cannot fully classify a statement, deny.*
- **Problem 4 is more than a port because of Problem 2.** Regex DLP misses `"Band L5: 42L"`. A value that came from the salary table carries a `CONFIDENTIAL` tag regardless of its shape. Presidio handles the pattern-matching half only.
- **A hash chain is tamper-evident, not tamper-proof.** Whoever holds the file can rewrite the whole chain. Periodically sign a checkpoint `(seq, hash)` with a key the agent host cannot read, and ship it to separate storage.

---

## 5. Team and ownership

| Owner | Problems | Owns in code |
|---|---|---|
| **Vibhas** | 2 (provenance tags) + 5 (session combination) | `src/agentshield/provenance/` (labelers), `src/agentshield/policies/session.py` |
| **Sahil** | 3 (destructive actions) + 4 (data leaving) | `src/agentshield/policies/tools.py`, `src/agentshield/policies/egress.py` |
| **Bhoomi** | 1 (nasty input) + 6 (audit) + shared core and integration | `model.py`, `kernel.py`, `audit.py`, `src/agentshield/input/`, `src/agentshield/adapters/`, `demo/` |

Why this split: 2 and 5 are one mechanism (5 counts the tags 2 creates), so one owner. 3 and 4 both inspect a tool call before it fires. 1 is mostly integration and 6's core is done, which leaves room for the shared kernel and the agent hook that no single problem owns.

### The shared contract

Everyone builds against these. Changes need review from all three.

- **`model.py`** — `Label`, `Event`, `Decision`, `Action`, `Mode`, `Trust`, `Sensitivity`.
- **`kernel.py`** — the two plug-in points and the session:
  - `Labeler.label(event) -> Iterable[Label]` — Vibhas's tagging plugs in here.
  - `Policy.evaluate(event, session) -> Decision | None` — every rule (Problems 1, 3, 4, 5) plugs in here.
  - `Session.history` — every earlier `(event, decision)` in the conversation.
- **`Shield.check(event)`** runs labelers → policies → combines votes (most severe wins) → applies shadow/enforce → records to the audit log.

Rules for anything plugged in: return a `Decision` (or `None`), never raise to block, never set the mode, keep no state of your own (read it from `session.history` — that is what makes replay work). The kernel fails closed: a crashing policy votes `BLOCK`, a crashing labeler marks content untrusted.

---

## 6. Status (2026-10-03)

| Area | Owner | Status |
|---|---|---|
| Shared types (`model.py`) | Bhoomi | **Done**, pending team review |
| Kernel + plug-in interfaces (`kernel.py`) | Bhoomi | **Done**, pending team review |
| Problem 6 — hash chain, signed checkpoints, `verify()` | Bhoomi | **Core done** |
| Contract check — flagship scenario through toy labeler + toy trifecta policy | — | **Passing** (`tests/test_kernel.py`) |
| Problem 1 | Bhoomi | Not started |
| Problems 2, 5 | Vibhas | Not started |
| Problems 3, 4 | Sahil | Not started |
| Agent hook (MCP proxy / LangGraph) | Bhoomi | Not started — form factor undecided |

22 tests passing. Code is on branch `foundation`, not yet merged.

---

## 7. Tracks

Each person can start immediately: tests use hand-written `Label`s, so nobody waits on anyone else's code.

### Vibhas — Problems 2 + 5 (critical path)

| # | Task | Done when |
|---|---|---|
| V1 | Source-config labeler: map tool/source → `Trust` + `Sensitivity`; unknown sources default `UNTRUSTED` | Every `TOOL_RESULT`, `MEMORY_READ` and `AGENT_MESSAGE` event carries labels |
| V2 | Session combination policy | Untrusted + sensitive + external action → `REQUIRE_APPROVAL`; any two of the three pass. Decide whether a blocked external action counts toward the tally. |
| V3 | MCP tool-description labeler | Tool descriptions are labeled by server trust, so a poisoned description is untrusted content |
| V4 | Argument matching | A tool-call argument containing text from an untrusted result is flagged — finer than whole-session tagging |

Sahil's egress check (S4) and the flagship demo depend on V1 + V2, so these go first.

### Sahil — Problems 3 + 4

| # | Task | Done when |
|---|---|---|
| S1 | Tool capability manifest policy (per agent, per tool: allowed operations) | A call outside the manifest votes `BLOCK` |
| S2 | SQL classification with `sqlglot` | `SELECT` passes; `DROP`/`DELETE`/`UPDATE` follow the manifest; multi-statement and **unparseable SQL vote `BLOCK`** |
| S3 | Circuit breaker | Too many calls per turn or per session votes `TERMINATE` (counts read from `session.history`) |
| S4 | Egress policy: destination allowlist + Presidio + labels | Data labeled `CONFIDENTIAL`/`SECRET` going to a non-allowlisted domain is stopped even when no PII pattern matches |

### Bhoomi — Problems 1 + 6 + core

| # | Task | Done when |
|---|---|---|
| B1 | Team review of the shared contract; freeze v0.1 | All three have approved `model.py` and `kernel.py` |
| B2 | Agent hook (MCP proxy or LangGraph adapter) | Real tool calls and results become `Event`s; `enforced_action` is applied; `REQUIRE_APPROVAL` pauses for a human |
| B3 | Problem 1: Prompt Guard / LLM Guard as an advisory policy | Classifier result appears in the decision reasons; votes `WARN` only |
| B4 | Problem 6 remainder: checkpoint export to separate storage; replay CLI | A recorded session can be re-run through current policies and the decisions diffed |
| B5 | Demo agent | Runs the flagship scenario and `DROP TABLE` end to end |

### Milestone M1 — flagship demo

Needs **V1, V2, S1, S2, B2, B5**. A real agent reads a malicious resume, reads salaries, and tries to email an outside address: the email pauses for approval, an internal email passes, `DROP TABLE` is blocked, and `verify()` passes on the audit log. Measure latency (p50/p99) and false positives from here on, against AgentDojo plus our own attack cases.

---

## 8. Working agreement

- `main` only changes through pull requests. Branches: `vibhas/…`, `sahil/…`, `bhoomi/…`.
- Every PR gets at least one review from another member; PRs touching the shared contract get both.
- Every labeler and policy ships with tests. `pytest` must pass before merge.
- Stay inside your own files where possible — the layout above is designed so three people rarely edit the same file.
- Weekly 30-minute sync: show what merged, raise contract changes, update the status table above.

Setup:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m pytest -q
```

---

## 9. Open decisions

1. **First form factor.** Recommendation: core library behind an **MCP proxy** first (works on agents whose code we don't control — Claude Code, Cursor), thin LangGraph adapter second. Both sit on the same core.
2. **Vertical.** Pick one (coding agents or finance-ops) and find 2–3 design partners there.
3. **Kill criterion.** If no design partner has moved a policy from shadow to enforce within six months, pivot to the assessment-services or compliance-evidence business ([Facts.md](Facts.md)).

---

## 10. Parallel track

Offer the two-week agent security assessment against OWASP ASI01–ASI10 while building. Every engagement produces attack cases for the replay suite and a draft policy pack.
