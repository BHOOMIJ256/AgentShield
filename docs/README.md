# AgentShield Knowledge Base

The single place to understand what AgentShield is, how it is built, what is done, and what each of us is working on. If something here is wrong or stale, fixing it is part of your PR.

## Read in this order

| # | Doc | Read it to learn | Changes when |
|---|---|---|---|
| 1 | [Overview](1-overview.md) | Why this exists, the six problems, what we build vs. borrow, how we got here | Scope changes |
| 2 | [Architecture](2-architecture.md) | The four building blocks, the shared contract, how to write a labeler or policy | The contract changes (needs all three reviews) |
| 3 | [Status](3-status.md) | What is done, in progress, blocked; milestone M1 | **Every PR that moves a task** |
| 4 | [Decisions](4-decisions.md) | Every decision we made and why; open questions and who owns them | A decision is made or a question is raised |
| 5 | [Contributing](5-contributing.md) | Setup, branches, PRs, reviews, definition of done | The way we work changes |
| — | [Glossary](glossary.md) | Every term we use: label, trust, trifecta, shadow mode, checkpoint… | A new term appears |

Then read **your own track**:

| Owner | Track | Problems |
|---|---|---|
| Vibhas | [Provenance + session combination](tracks/vibhas-provenance-session.md) | 2 + 5 |
| Sahil | [Tool permissions + egress](tracks/sahil-tools-egress.md) | 3 + 4 |
| Bhoomi | [Input, audit + shared core](tracks/bhoomi-input-audit-core.md) | 1 + 6 + core |

Reading the other two tracks is worth ten minutes — the "Coordination points" section of each one lists where your work touches theirs.

## Keeping it alive

- **Status** is updated in the same PR that changes a task's state. The PR template has a checkbox for it.
- **Decisions** are appended, never rewritten. If a decision is reversed, add a new entry that supersedes the old one.
- **Architecture** only changes together with a change to `model.py` or `kernel.py`, and both need review from all three of us.
- **Tracks** are owned by their owner. Edit your own freely; suggest changes to others' in review.

## Background research

These are the inputs that shaped the plan. They are not kept up to date — the docs above are.

- <../AgentShield — An Open-Source Runtime Security SDK for AI Agents (1).pdf> — the original design doc
- [Facts.md](../Facts.md) — market and commercial review of the original design
- [Simpler_Idea.md](../Simpler_Idea.md) — the same review in plain English
- <../Components/16_Components(Sahil).md> — the 16 attack scenarios and components
- [6_Catgeories.md](../Components/6_Catgeories.md) — the 16 reduced to six problems
