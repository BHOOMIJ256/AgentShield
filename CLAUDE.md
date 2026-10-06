# AgentShield

Provenance-aware runtime authorization and audit for AI agents. Three people build it in parallel; the knowledge base in `docs/` is the source of truth — read `docs/README.md` first.

## Commands

```bash
.venv/Scripts/python -m pip install -e ".[dev]"   # setup (macOS/Linux: .venv/bin/python)
.venv/Scripts/python -m pytest -q                 # tests
```

## Ownership — stay in your lane

| Owner | Files |
|---|---|
| Vibhas | `src/agentshield/provenance/`, `src/agentshield/policies/session.py` |
| Sahil | `src/agentshield/policies/tools.py`, `src/agentshield/policies/egress.py` |
| Bhoomi | `model.py`, `kernel.py`, `audit.py`, `input/`, `adapters/`, `demo/` |

`model.py` and `kernel.py` are the shared contract. Don't change them as a side effect of other work; a contract change is its own PR, updates `docs/2-architecture.md`, and needs review from all three.

## Rules for labelers and policies

- Return a `Decision` or `None`; never raise to block; never set the mode.
- Keep no state; read from `event` and `session.history` (replay depends on it).
- Return nothing for event kinds you don't handle.
- Deterministic only. Model or classifier output is an advisory signal inside a policy, never the decision itself.
- Fail closed; unparseable input means deny.

## Conventions

- Core package has no required dependencies; heavy libraries go in an optional extra and are imported inside the module that needs them.
- Frozen dataclasses for shared types; `str, Enum` enums; `from __future__ import annotations`.
- Tests use hand-written `Label`s so no track waits on another.
- Never commit to `main`. Branch `<owner>/<task>`, PR into `main`.
- When a task's state changes, update `docs/3-status.md` in the same PR. Decisions go in `docs/4-decisions.md` (append-only).
