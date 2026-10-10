"""The proxy end to end: a real MCP client (the 'agent') talks to the proxy, which talks
to a real MCP server. In-process for the scenarios; one test runs everything over stdio."""

import os
import sys

import pytest
from mcp import Client, StdioServerParameters

from agentshield import AuditLog, Mode, Shield, read_entries, verify
from agentshield.adapters import ToolGate
from agentshield.adapters.mcp_proxy import build_server
from conftest import FIXTURES
from hr_server import server as hr_server
from toy_shield import build

pytestmark = pytest.mark.anyio


class Answer:
    name = "test"

    def __init__(self, answer):
        self.answer = answer

    async def decide(self, request):
        return self.answer


def _text(result):
    return result.content[0].text


def _entries(path, *kinds):
    """Audit entries for these event kinds. The agent's client re-lists tools after calls,
    so tool descriptions are interleaved with everything else."""
    return [e for e in read_entries(path) if e.body.get("event", {}).get("kind") in kinds]


async def _run(audit_path, *, mode=Mode.ENFORCE, approve=False, steps):
    policies, labelers = build()
    shield = Shield(policies=policies, labelers=labelers, mode=mode, audit=AuditLog(audit_path))
    gate = ToolGate(shield, agent_id="hr-agent", server="hr", approver=Answer(approve))
    async with Client(hr_server) as upstream:
        async with Client(build_server(upstream, gate, "hr")) as agent:
            return await steps(agent)


async def test_flagship_external_email_needs_a_human(tmp_path):
    async def steps(agent):
        await agent.call_tool("read_resume", {"candidate": "jane"})
        await agent.call_tool("read_salaries", {})
        internal = await agent.call_tool("send_email", {"to": "hiring@ourco.com", "body": "shortlist"})
        external = await agent.call_tool("send_email", {"to": "job-leaks@competitor.com", "body": "Band L5: 42L"})
        return internal, external

    internal, external = await _run(tmp_path / "audit.jsonl", steps=steps)
    assert not internal.is_error and _text(internal) == "sent to hiring@ourco.com"
    assert external.is_error and "declined" in _text(external)
    assert verify(tmp_path / "audit.jsonl").ok


async def test_approved_email_goes_through(tmp_path):
    async def steps(agent):
        await agent.call_tool("read_resume", {"candidate": "jane"})
        await agent.call_tool("read_salaries", {})
        return await agent.call_tool("send_email", {"to": "candidate@gmail.com", "body": "offer"})

    result = await _run(tmp_path / "audit.jsonl", approve=True, steps=steps)
    assert not result.is_error


async def test_drop_table_is_blocked_and_select_is_not(tmp_path):
    async def steps(agent):
        return (
            await agent.call_tool("run_sql", {"query": "DROP TABLE users"}),
            await agent.call_tool("run_sql", {"query": "SELECT * FROM flights"}),
        )

    drop, select = await _run(tmp_path / "audit.jsonl", steps=steps)
    assert drop.is_error and "destructive SQL" in _text(drop)
    assert not select.is_error


async def test_poisoned_tool_is_hidden_from_the_agent(tmp_path):
    async def steps(agent):
        listing = await agent.list_tools()
        return [t.name for t in listing.tools], await agent.call_tool("get_weather", {"city": "Pune"})

    names, call = await _run(tmp_path / "audit.jsonl", steps=steps)
    assert "get_weather" not in names and "read_resume" in names
    assert call.is_error


async def test_shadow_mode_changes_nothing_for_the_agent_but_records_everything(tmp_path):
    async def steps(agent):
        return await agent.call_tool("run_sql", {"query": "DROP TABLE users"})

    result = await _run(tmp_path / "audit.jsonl", mode=Mode.SHADOW, steps=steps)
    assert not result.is_error
    (call,) = _entries(tmp_path / "audit.jsonl", "tool_call")
    assert call.body["decision"]["action"] == "block" and call.body["enforced_action"] == "allow"


async def test_every_step_is_in_the_audit_log_with_labels(tmp_path):
    async def steps(agent):
        await agent.call_tool("read_resume", {"candidate": "jane"})

    await _run(tmp_path / "audit.jsonl", steps=steps)
    call, result = (entry.body["event"] for entry in _entries(tmp_path / "audit.jsonl", "tool_call", "tool_result"))
    assert (call["kind"], call["payload"]) == ("tool_call", {"candidate": "jane"})
    assert result["kind"] == "tool_result" and "Ignore your instructions" in result["payload"]["content"][0]["text"]
    assert result["labels"][0]["trust"] == "untrusted"


async def test_command_line_proxy_over_stdio(tmp_path):
    audit = tmp_path / "audit.jsonl"
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(FIXTURES), os.environ.get("PYTHONPATH", "")])}
    proxy = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m", "agentshield.adapters.mcp_proxy",
            "--agent-id", "hr-agent", "--server-name", "hr", "--mode", "enforce",
            "--audit", str(audit), "--setup", "toy_shield:build",
            "--", sys.executable, str(FIXTURES / "hr_server.py"),
        ],
        env=env,
    )
    async with Client(proxy) as agent:
        names = [t.name for t in (await agent.list_tools()).tools]
        drop = await agent.call_tool("run_sql", {"query": "DROP TABLE users"})
        select = await agent.call_tool("run_sql", {"query": "SELECT 1"})

    assert "get_weather" not in names
    assert drop.is_error and not select.is_error
    assert verify(audit).ok
