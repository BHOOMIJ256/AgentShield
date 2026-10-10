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

### D14 · 2026-10-10 · The first agent hook is an MCP proxy (closes O1)
**Why:** A proxy between the agent and its MCP servers works on agents whose code nobody controls (Claude Code, Cursor), can be mandated by a security team without changing agent code, and sees every tool call, result and tool description — enough for the flagship scenario.
**Means:** B2 builds `adapters/mcp_proxy`. The LangGraph adapter comes second, on the same core.

### D15 · 2026-10-10 · Add `EventKind.USER_INPUT` (closes O5)
**Why:** Problem 1 needs an event to run the input classifier on, and turn boundaries need a marker.
**Means:** Adapters that can see the user's message emit `USER_INPUT` with `{"text": ...}`.

### D16 · 2026-10-10 · A turn starts at the latest `USER_INPUT` (closes O9)
**Why:** The simplest boundary every adapter that sees user input can produce.
**Means:** `Session.current_turn()`. With no user input seen (e.g. behind an MCP proxy), it returns the whole session.

### D17 · 2026-10-10 · Labelers receive the session: `label(event, session)` (closes O8)
**Why:** Argument matching (V4) needs to compare a tool call's arguments with earlier untrusted results. Passing the session keeps all tagging in labelers, and the change is free now because no labeler exists yet.
**Means:** Labelers see the session as it was before the current event, same as policies. Labelers must stay stateless like policies.

### D18 · 2026-10-10 · Tool descriptions are events: `EventKind.TOOL_DESCRIPTION` (closes O10)
**Why:** A tool description is content the agent reads and trusts; a poisoned description is Problem 2. As events, they get labeled and recorded like everything else, and a policy can compare them against a pinned version (component #10).
**Means:** The MCP proxy emits one `TOOL_DESCRIPTION` per tool from each `tools/list` response, with `{"server", "description", "input_schema"}`.

### D19 · 2026-10-10 · Fixed payload shape per event kind (closes O12)
**Why:** Policies must read events the same way no matter which adapter produced them.
**Means:** The table in [Architecture](2-architecture.md#data-model--srcagentshieldmodelpy). `TOOL_CALL` payload is the tool's arguments verbatim; which argument holds a SQL query, recipient or URL is per-tool config inside each policy.

## Open questions

| ID | Question | Owner | Blocks | Recommendation |
|---|---|---|---|---|
| O2 | Which vertical for design partners: coding agents or finance-ops? | Team | Go-to-market | Pick one; find 2–3 partners |
| O3 | Does a *blocked* external action count toward the session tally? | Vibhas | V2 | — |
| O4 | Per-policy shadow/enforce, so one policy can be enforced while others stay in shadow? | Bhoomi | Moving partners from shadow to enforce | Yes, after M1 |
| O6 | Where are signed checkpoints stored, and how often are they made? | Bhoomi | B4 | Separate directory/bucket the agent host can't write; every N entries and on session end |
| O7 | Confirm the kill criterion: no partner moves a policy to enforce within six months → pivot | Team | — | Keep |
| O11 | One shared config for "internal destinations", used by both V2 and S4? | Vibhas + Sahil | V2, S4 | Yes — define it once |

### Closed

| ID | Question | Closed by |
|---|---|---|
| O1 | First form factor | D14 — MCP proxy first |
| O5 | Event kind for user input | D15 — `USER_INPUT` |
| O8 | Should labelers receive the session? | D17 — yes |
| O9 | Where does a turn start? | D16 — latest `USER_INPUT` |
| O10 | How do tool descriptions appear as events? | D18 — `TOOL_DESCRIPTION` |
| O12 | Which tool argument holds the query or recipient? | D19 — per-tool config in each policy |
