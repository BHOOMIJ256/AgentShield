# 4. Decisions

Append-only. To reverse a decision, add a new entry that says which one it supersedes. Each entry: what we decided, why, and what it means for the code.

## Decided

### D1 · 2026-10-02 · Scope is six problems, not sixteen components
**Why:** The 16 components overlap heavily. Building 16 separate systems means building nothing well, and buyers read broad scope as "no wedge chosen."
**Means:** New ideas get mapped onto one of the six problems or parked. See [Overview](1-overview.md).

### D2 · 2026-10-02 · Track where content came from instead of guessing what it means
**Why:** Text classifiers are a guessing game with no ceiling; the same sentence is malicious in a resume and innocent in a blog post. Origin is a fact, not a guess. It is also the part a classifier vendor can't copy by swapping in a better model.
**Means:** Problem 2 is labelers, not detectors. `Trust` is set by source, never by content.

### D3 · 2026-10-02 · Borrow Problem 1; classifiers are advisory only
**Why:** Jailbreak detection is free and mature elsewhere. We add nothing by rebuilding it.
**Means:** Problem 1 is a policy wrapping Prompt Guard or LLM Guard that votes `WARN` at most.

### D4 · 2026-10-02 · The policy kernel is deterministic
**Why:** Nobody lets a nondeterministic model be the thing that blocks a payment, and no auditor accepts "the model decided." Also keeps latency low.
**Means:** LLM or classifier outputs may feed a policy as a signal, but the final `Decision` comes from deterministic code.

### D5 · 2026-10-02 · Shadow mode is the default
**Why:** One wrongly blocked production action and we get uninstalled. Watching first is also how we learn what policies to propose.
**Means:** `Mode.SHADOW` is the default everywhere. Decisions are always recorded, with `enforced_action = ALLOW` in shadow.

### D6 · 2026-10-02 · Three flags means ask a human, never block
**Why:** The untrusted + sensitive + external combination is sometimes legitimate (a recruiter emailing an offer). Blocking it would be a false positive on real work.
**Means:** The session combination policy (V2) votes `REQUIRE_APPROVAL`. Watch approval volume for approval fatigue.

### D7 · 2026-10-02 · If the SQL parser can't fully classify a statement, deny
**Why:** "Deterministic, never wrong" is only true if the unknown case is closed. Dialect quirks, multi-statement payloads, `EXEC` and CTEs hiding a `DELETE` all exist.
**Means:** S2 votes `BLOCK` on parse failure, multiple statements, and any statement type it doesn't recognize.

### D8 · 2026-10-02 · Hash chain plus signed checkpoints
**Why:** A chain alone is tamper-*evident*: it catches edits, deletions and reordering, but not a truncated end or a fully rebuilt file. An Ed25519 signature from a key the agent host can't read closes that gap, and verifying needs only the public key.
**Means:** `audit.py` as built. Where checkpoints are stored is O6.

### D9 · 2026-10-03 · Ownership: Vibhas 2+5, Sahil 3+4, Bhoomi 1+6+core
**Why:** 2 and 5 are one mechanism, so one owner. 3 and 4 both inspect a tool call before it fires. 1 is mostly integration and 6's core was already built, leaving room for the shared kernel and agent hook that no problem owns.
**Means:** See the [tracks](README.md#read-in-this-order) and the code layout in [Architecture](2-architecture.md#code-layout).

### D10 · 2026-10-03 · Policies keep no state; they read `session.history`
**Why:** Stateless policies give the same decision when a recorded session is replayed, which makes replay and regression testing possible.
**Means:** Rule 3 in [Architecture](2-architecture.md#rules-for-anything-you-plug-in).

### D11 · 2026-10-03 · Most severe vote wins
**Why:** Simple, predictable, and explainable; one policy's `BLOCK` is never silently outvoted.
**Means:** `kernel.combine`. Reasons from every non-`ALLOW` vote are kept.

### D12 · 2026-10-03 · Fail closed
**Why:** A security layer that fails open turns every bug into a bypass.
**Means:** A crashing policy votes `BLOCK`. A crashing labeler marks the content `UNTRUSTED`.

### D13 · 2026-10-03 · `main` changes only through reviewed PRs; contract changes need all three
**Why:** Three people building against one shared contract; a silent change to it breaks the other two.
**Means:** See [Contributing](5-contributing.md).

## Open questions

| ID | Question | Owner | Blocks | Recommendation |
|---|---|---|---|---|
| O1 | First form factor: MCP proxy or LangGraph adapter? | Bhoomi + team | B2, B5, M1 | MCP proxy first: it works on agents whose code we don't control (Claude Code, Cursor) and sees everything crossing the tool boundary. LangGraph adapter second. |
| O2 | Which vertical for design partners: coding agents or finance-ops? | Team | Go-to-market | Pick one; find 2–3 partners |
| O3 | Does a *blocked* external action count toward the session tally? | Vibhas | V2 | — |
| O4 | Per-policy shadow/enforce, so one policy can be enforced while others stay in shadow? | Bhoomi | Moving partners from shadow to enforce | Yes, after M1 |
| O5 | Add `EventKind.USER_INPUT` for Problem 1? | Bhoomi | B3, S3 | Yes — contract change, all three review |
| O6 | Where are signed checkpoints stored, and how often are they made? | Bhoomi | B4 | Separate directory/bucket the agent host can't write; every N entries and on session end |
| O7 | Confirm the kill criterion: no partner moves a policy to enforce within six months → pivot | Team | — | Keep |
| O8 | Should `Labeler.label` receive the session? | Vibhas + Bhoomi | V4 | Or write argument matching as a policy instead — decide when V4 starts |
| O9 | How do we know where a "turn" starts? | Sahil + Bhoomi | S3 per-turn limit | Count calls since the last `USER_INPUT` event (needs O5) |
| O10 | How do MCP tool listings (tool descriptions) appear as events? | Vibhas + Bhoomi | V3 | Decide with B2 |
| O11 | One shared config for "internal destinations", used by both V2 and S4? | Vibhas + Sahil | V2, S4 | Yes — define it once |
| O12 | How does a policy know which tool argument holds the SQL query, recipient or URL? | Sahil + Bhoomi | S2, S4 | Per-tool config mapping tool name → argument name |
