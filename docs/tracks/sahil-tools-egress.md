# Track: Tool Permissions + Egress — Sahil

**Problems:** 3 (the agent does something destructive) + 4 (sensitive data leaves the building)
**Covers components:** #3 Tool permissions, #4 Egress DLP, #5 Secrets, #8 Circuit breaker, #16 Sandbox (enforcement only)
**OWASP:** ASI02 Tool misuse, ASI05 Unexpected code execution, ASI08 Cascading failures

## Your mission

Check every tool call **before it fires**. Problem 3 stops the agent doing things it should never do; Problem 4 stops it sending things it should never send. Both are deterministic policies, and both are what make the demo work every single time.

## Tasks

| ID | Task | Done when | Depends on |
|---|---|---|---|
| **S1** | **Tool capability manifest policy** — per agent, per tool: what is allowed | A call outside the manifest votes `BLOCK` | Contract only |
| **S2** | **SQL classification with `sqlglot`** | `SELECT` passes; `DROP` / `DELETE` / `UPDATE` follow the manifest; **multi-statement and unparseable SQL vote `BLOCK`** | Contract only |
| S3 | Circuit breaker | Too many calls per session (and per turn, once O9 is decided) votes `TERMINATE`; counts come from `session.history` | O9 for per-turn |
| S4 | Egress policy | Data labeled `CONFIDENTIAL` / `SECRET`, or matching a PII pattern, going to a non-allowlisted destination is stopped — **even when no PII pattern matches** | V1, V4 helper, O11 |

S1 and S2 make the `DROP TABLE` half of milestone M1.

## Files you own

```
src/agentshield/policies/tools.py      S1, S2, S3
src/agentshield/policies/egress.py     S4
tests/test_tool_policies.py
tests/test_egress_policy.py
```

## Starting point for S1

```python
from agentshield import Action, Decision, EventKind

class ToolManifestPolicy:
    """Blocks any tool call the agent's manifest doesn't allow."""

    policy_id = "tool-manifest"

    def __init__(self, manifest: dict[str, set[str]]):
        self.manifest = manifest  # agent_id -> allowed tool names

    def evaluate(self, event, session):
        if event.kind is not EventKind.TOOL_CALL:
            return None
        if event.name not in self.manifest.get(event.agent_id, set()):
            return Decision(Action.BLOCK, reasons=(f"{event.agent_id} may not call {event.name}",))
        return None
```

## Notes for S2 — the SQL check

- Add `sqlglot` as an **optional extra** (`[sql]`) and import it inside `tools.py` only. The core package stays dependency-free.
- Classify by walking the parsed tree, not by checking the first keyword — a `WITH … DELETE` hides the delete inside a CTE.
- **Decision D7:** parse error, more than one statement, or a statement type you don't recognize (`EXEC`, `CALL`, vendor commands) → `BLOCK`.
- Which argument holds the query is per-tool config (O12) — don't hard-code `payload["query"]`.
- Map statements to operations — `READ`, `INSERT`, `UPDATE`, `DELETE`, `DDL` — and check them against the manifest from S1.

## Notes for S3 — circuit breaker

- Count `TOOL_CALL` events in `session.history`. Don't keep a counter in the policy (rule 3 — replay must give the same answer).
- "Per turn" needs a turn boundary that doesn't exist yet (O9). Ship the per-session limit first.

## Notes for S4 — egress

Three checks, any one triggers:

1. **Destination:** extract the recipient or URL from the payload (per-tool config, O12); compare against the shared internal-destinations config (O11).
2. **Labels:** has this session seen `CONFIDENTIAL` / `SECRET` content, *and* does the payload contain text from it? The "contains text from" part is Vibhas's V4 matching helper — use it, don't build a second one.
3. **Patterns:** Presidio for PII, plus simple patterns for secrets (`sk_live_…`, `AKIA…`). Presidio is heavy — optional extra `[egress]`.

The label check is what makes this better than old-style DLP: `"Band L5: 42L"` matches no pattern but came from the salary table.

## Tests to write

- `DROP TABLE`, `DELETE FROM x` without permission, `SELECT 1; DROP TABLE x`, `WITH d AS (DELETE …) SELECT …`, plain garbage → all `BLOCK`.
- `SELECT` with joins and subqueries → passes.
- A tool not in the manifest → `BLOCK`; an agent with no manifest entry → `BLOCK`.
- The 101st call in a session → `TERMINATE` (with a limit of 100).
- Confidential data to an external domain → stopped; the same data to an internal domain → passes; public data to an external domain → passes.

## Coordination points

| With | About |
|---|---|
| Vibhas | **O11** — one shared internal-destinations config. **V4 helper** — S4's label check depends on it. Until then, test with hand-written labels and a stub. |
| Bhoomi | **O12** — how the adapter passes tool arguments (per-tool argument names). **O9** — turn boundaries. |

## Pitfalls

- A keyword match is not a SQL check. `SELECT 'DROP TABLE'` is harmless; `/* */ DROP` is not.
- Don't vote `TERMINATE` for an ordinary policy violation — that ends the user's whole session. `BLOCK` the call; save `TERMINATE` for runaways.
- Every policy sees every event. Return `None` for anything that isn't a `TOOL_CALL`.

## References

- [Architecture](../2-architecture.md) — contract, rules, examples
- <../../Components/16_Components(Sahil).md> — components 3, 4, 5, 8, 16
- `sqlglot` documentation — parsing and walking the expression tree
