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

## 5. Build order

Each step is a thin end-to-end slice that the next one depends on.

| Step | Problem | Deliverable | Done when | Status |
|---|---|---|---|---|
| 1 | 6 | Core types (`Event`, `Label`, `Decision`, `Mode`) + hash-chained audit log + signed checkpoints | Editing, deleting or reordering any log line is detected by `verify()`; checkpoint signatures verify with the public key only | **Done** — `src/agentshield/`, 15 tests |
| 2 | 3 | Tool-call interception, per-tool capability manifest, SQL classification via `sqlglot` | `DROP TABLE`, multi-statement and unparseable SQL are denied; `SELECT` passes; shadow mode logs "would have blocked" | |
| 3 | 2 | Labels attached at every entry point (tool results, documents, memory reads, MCP tool descriptions) | Every event in the log carries the labels of the content that produced it | |
| 4 | 5 | Per-session tally + human-approval pause | **Flagship demo:** resume → salaries → external email pauses for approval; any two of the three pass | |
| 5 | 4 | Egress check using labels + Presidio + destination allowlist | Tagged-confidential data to a non-allowlisted domain is stopped even when no PII regex matches | |
| 6 | 1 | Plug-in slot for an external input classifier | Prompt Guard result appears as an advisory signal in the decision record | |

Shadow mode is on from step 2. Latency (p50/p99) and false-positive rate are measured from step 4 against AgentDojo plus our own attack cases, and published.

---

## 6. Open decisions

1. **First form factor.** Recommendation: core library behind an **MCP proxy** first (works on agents whose code we don't control — Claude Code, Cursor), thin LangGraph adapter second. Both sit on the same core.
2. **Vertical.** Pick one (coding agents or finance-ops) and find 2–3 design partners there.
3. **Kill criterion.** If no design partner has moved a policy from shadow to enforce within six months, pivot to the assessment-services or compliance-evidence business ([Facts.md](Facts.md)).

---

## 7. Parallel track

Offer the two-week agent security assessment against OWASP ASI01–ASI10 while building. Every engagement produces attack cases for the replay suite and a draft policy pack.
