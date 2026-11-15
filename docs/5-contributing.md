# 5. Contributing

## Setup

```bash
git clone https://github.com/BHOOMIJ256/AgentShield.git
cd AgentShield
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m pytest -q
```

On macOS/Linux use `.venv/bin/python` instead of `.venv/Scripts/python`. Python 3.10 or newer.

## Branches

```
main ──●─────────●─────────●──      the official version; changes only through PRs
        \       / \       /
         vibhas/labelers   sahil/tool-manifest   …
```

- `main` is never committed to directly.
- One branch per task, named `<you>/<short-task-name>`: `vibhas/source-labeler`, `sahil/sql-policy`, `bhoomi/mcp-proxy`.
- Always start from an up-to-date `main`:

```bash
git switch main
git pull
git switch -c vibhas/source-labeler
```

## Pull requests

1. Push your branch and open a PR into `main`. The template asks for the task ID (e.g. `V1`) and a checklist.
2. **Review:** at least one other member. If the PR touches `model.py` or `kernel.py`, **both** others.
3. Merge when approved and tests pass. Delete the branch afterwards.
4. Before starting your next task, `git switch main && git pull`.

Keep PRs to one task. Small PRs get reviewed the same day; big ones wait.

## Definition of done

A task is done when:

- [ ] The "done when" line in your track is true
- [ ] Tests cover it, including the failure cases (what must be blocked, not just what passes)
- [ ] `pytest` passes
- [ ] [Status](3-status.md) is updated: task status, done log, "Waiting on" if relevant
- [ ] Any decision you made is in [Decisions](4-decisions.md)
- [ ] Any new term is in the [Glossary](glossary.md)

## Code conventions

Match the existing code:

- `from __future__ import annotations` at the top; type hints on public functions.
- Shared data types are frozen `dataclass`es; enums subclass `str, Enum` so they serialize as plain strings.
- Labelers and policies are small classes following the rules in [Architecture](2-architecture.md#rules-for-anything-you-plug-in).
- Comments say *why*, not *what*. A short module docstring explaining the module's job.
- Tests are plain `pytest` functions named for the behavior: `test_unparseable_sql_is_blocked`.
- **The core package has no required dependencies.** Heavy libraries (`sqlglot`, `presidio-analyzer`, an MCP SDK) go in an optional extra in `pyproject.toml`, e.g. `pip install -e ".[sql]"`, and are imported inside the module that needs them. Mention a new dependency in the PR description.

## Changing the shared contract

`model.py` and `kernel.py` are what all three of us build against.

1. Open a PR that changes the contract **and** [Architecture](2-architecture.md) together.
2. Add a decision entry to [Decisions](4-decisions.md).
3. Tag both other members for review. Don't merge until both approve.

## Commit messages

First line: what changed, imperative, under ~70 characters (`Add SQL classification policy`). Then a blank line and the why, if it isn't obvious.

## Weekly sync — 30 minutes

1. Each person: what merged, what's next, what's blocking (5 min each).
2. Walk the "Waiting on" table in [Status](3-status.md).
3. Decide any open questions in [Decisions](4-decisions.md) that are now blocking.
