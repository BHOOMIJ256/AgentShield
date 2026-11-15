# AgentShield

**Provenance-aware runtime authorization and audit for AI agents.**

AgentShield tracks where every piece of an agent's context came from, stops untrusted content from combining with sensitive data into an external action, and keeps a record your compliance team can verify.

> **Status:** early development. The shared core (types, policy kernel, audit log) and an MCP proxy are built; the security policies are being built by three parallel tracks. See [docs/3-status.md](docs/3-status.md).

## Quickstart

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m pytest -q
```

```python
from agentshield import AuditLog, Event, EventKind, Mode, Shield

shield = Shield(policies=[], labelers=[], audit=AuditLog("audit.jsonl"), mode=Mode.SHADOW)
decision = shield.check(Event(kind=EventKind.TOOL_CALL, session_id="s1", agent_id="hr-agent",
                              name="send_email", payload={"to": "someone@example.com"}))
decision.enforced_action   # what to do with the call
```

Policies and labelers plug into `Shield`; see [Architecture](docs/2-architecture.md#writing-a-policy) for how to write one.

### Put an MCP server behind AgentShield

Register the proxy with your agent in place of the real server:

```bash
agentshield-mcp-proxy --agent-id hr-agent --server-name hr --audit audit.jsonl --approvals approvals/ -- python hr_server.py
```

It starts in shadow mode: nothing is blocked, everything is recorded. Approve or deny paused actions from another terminal with `agentshield-approve --dir approvals/ list`. Details: [Architecture → Adapters](docs/2-architecture.md#adapters--srcagentshieldadapters).

## Documentation

Start at the **[knowledge base](docs/README.md)**:

1. [Overview](docs/1-overview.md) — why, the six problems, what we build vs. borrow
2. [Architecture](docs/2-architecture.md) — building blocks, the shared contract, writing a policy
3. [Status](docs/3-status.md) — what's done and what's next
4. [Decisions](docs/4-decisions.md) — what we decided and why; open questions
5. [Contributing](docs/5-contributing.md) — setup, branches, PRs

## Team

| Who | Owns |
|---|---|
| Vibhas | Provenance tags + session combination (Problems 2, 5) |
| Sahil | Tool permissions + egress (Problems 3, 4) |
| Bhoomi | Input classifier, audit log, shared core and integration (Problems 1, 6) |

## License

Apache-2.0
