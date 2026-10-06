# Track: Provenance + Session Combination — Vibhas

**Problems:** 2 (something the agent reads contains instructions) + 5 (the combination no single check can see)
**Covers components:** #2 Provenance, #6 Memory, #9 Trifecta, #10 MCP tool descriptions, #11 Delegation, #12 Cascading
**OWASP:** ASI01 Goal hijack, ASI06 Memory poisoning, ASI07 Inter-agent communication

## Your mission

This is the product's differentiator and the critical path. Problem 2 **tags** content by where it came from; Problem 5 **reads** those tags across the whole session and stops the dangerous combination. Neither is useful without the other, which is why both are yours.

You never judge what text *says*. You record where it *came from*, and write rules over that.

## Tasks

| ID | Task | Done when | Depends on |
|---|---|---|---|
| **V1** | **Source-config labeler** — config maps each source to `Trust` + `Sensitivity` | Every `TOOL_RESULT`, `MEMORY_READ` and `AGENT_MESSAGE` event carries a label; **unknown sources default to `UNTRUSTED`** | Contract only |
| **V2** | **Session combination policy** | Untrusted + sensitive + external action in one session → `REQUIRE_APPROVAL`; any two of the three → no vote | V1 (or hand-written labels in tests) |
| V3 | MCP tool-description labeler | Tool descriptions are labeled by the server's trust, so a poisoned description is untrusted content | O10, B2 |
| V4 | Argument matching | A tool-call argument containing text from an untrusted result is flagged — finer than whole-session tagging | O8 |

**Do V1 and V2 first** — Sahil's egress check (S4) and the flagship demo (M1) both wait on them.

## Files you own

```
src/agentshield/provenance/__init__.py
src/agentshield/provenance/sources.py      V1
src/agentshield/provenance/mcp.py          V3
src/agentshield/policies/session.py        V2
tests/test_provenance.py
tests/test_session_policy.py
```

## Starting point for V1

```python
from agentshield import EventKind, Label, Sensitivity, Trust

LABELED_KINDS = {EventKind.TOOL_RESULT, EventKind.MEMORY_READ, EventKind.AGENT_MESSAGE}

class SourceLabeler:
    """Labels incoming content by its source. Anything not in the config is untrusted."""

    def __init__(self, sources: dict[str, tuple[Trust, Sensitivity]]):
        self.sources = sources

    def label(self, event):
        if event.kind not in LABELED_KINDS:
            return
        trust, sensitivity = self.sources.get(event.name, (Trust.UNTRUSTED, Sensitivity.INTERNAL))
        yield Label(f"{event.kind.value}:{event.name}", trust, sensitivity)
```

Agree on an **origin naming convention** early and write it in the [Glossary](../glossary.md) — e.g. `tool:<name>`, `db:<table>`, `memory:<key>`, `agent:<id>`, `mcp:<server>/<tool>`.

## Starting point for V2

The kernel test `tests/test_kernel.py::ToyTrifecta` is a working sketch. To make it real:

- **"External action"** must come from config (which tools send things out, which domains are internal), not a hard-coded `@ourco.com`. Share this config with Sahil (O11).
- **"Sensitive"** = any label with `CONFIDENTIAL` or `SECRET` seen earlier in `session.history`.
- **"Untrusted"** = any `UNTRUSTED` label seen earlier in the session.
- Read everything from `session.history` — keep no state in the policy (rule 3).
- Vote `REQUIRE_APPROVAL`, never `BLOCK` (decision D6).
- Answer O3: should an external action that was *blocked* earlier count toward the tally? `session.history` gives you each event's decision, so either is possible.

## Tests to write

- Each pair of flags alone → no vote. All three → `REQUIRE_APPROVAL`.
- Order doesn't matter: sensitive first, then untrusted, then external.
- Two different sessions don't mix tallies.
- An unknown source is labeled `UNTRUSTED`.
- A labeler that returns nothing for `TOOL_CALL` events.
- The legitimate recruiter case: confirm it goes to approval, not block.

## Coordination points

| With | About |
|---|---|
| Sahil | **O11** — one shared "internal destinations" config for V2 and S4. **V4 ↔ S4** — Sahil's egress check needs "does this payload contain text from a confidential result?" That is the same matching as V4; build it once as a shared helper. |
| Bhoomi | **O8** — does `Labeler.label` need the session for V4? **O10** — how MCP tool listings arrive as events (for V3). Both are contract changes. |

## Pitfalls

- Every labeler sees **every** event. Return nothing for kinds you don't handle.
- Labels are added, never removed. A later trusted read does not "clean" an earlier untrusted one.
- Don't sneak a text classifier into a labeler. If content needs judging, that is a policy voting `WARN`, not a label.

## References

- [Architecture](../2-architecture.md) — contract, rules, examples
- <../../Components/16_Components(Sahil).md> — components 2, 6, 9, 10, 11, 12
- Prior research to read before V4: Google DeepMind's CaMeL; Microsoft's FIDES
