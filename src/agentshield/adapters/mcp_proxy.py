"""MCP proxy: sits between an agent and one MCP server and runs every tool listing,
call and result through AgentShield.

    agent ──stdio──▶ agentshield-mcp-proxy ──stdio──▶ real MCP server

Register the proxy with the agent in place of the real server, e.g.

    agentshield-mcp-proxy --agent-id hr-agent --server-name hr \\
        --audit audit.jsonl --approvals approvals/ --setup myshield:build \\
        -- python hr_server.py

Requires the `mcp` extra: pip install "agentshield[mcp]".
"""

from __future__ import annotations

import argparse
import importlib
import logging
import os
import sys
from typing import Any, Callable, Sequence

import anyio
import mcp_types as types
from mcp import Client, StdioServerParameters
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

from ..audit import AuditLog
from ..kernel import Labeler, Policy, Shield
from ..model import Mode
from .approval import DenyAll, FileApprover
from .gate import ToolGate

logger = logging.getLogger("agentshield.mcp_proxy")


def build_server(upstream: Client, gate: ToolGate, name: str) -> Server[Any]:
    """An MCP server that forwards to `upstream`, with every step passing through `gate`."""

    async def on_list_tools(ctx: Any, params: types.PaginatedRequestParams | None) -> types.ListToolsResult:
        listing = await upstream.list_tools(cursor=params.cursor if params else None, cache_mode="refresh")
        tools = [t for t in listing.tools if gate.describe_tool(t.name, t.description, t.input_schema)]
        return types.ListToolsResult(tools=tools, next_cursor=listing.next_cursor)

    async def on_call_tool(ctx: Any, params: types.CallToolRequestParams) -> types.CallToolResult:
        arguments = params.arguments or {}
        before = await gate.before_call(params.name, arguments)
        if not before.proceed:
            return _error(before.message)
        try:
            result = await upstream.call_tool(params.name, arguments)
        except Exception as e:  # the upstream failing is still a result the policies should see
            logger.warning("upstream call to %s failed: %r", params.name, e)
            result = _error(f"upstream server error: {e}")
        content = [block.model_dump(mode="json", by_alias=True, exclude_none=True) for block in result.content]
        after = await gate.after_call(params.name, content, result.is_error)
        if not after.proceed:
            return _error(after.message)
        return result

    return Server(name, on_list_tools=on_list_tools, on_call_tool=on_call_tool)


def _error(message: str) -> types.CallToolResult:
    return types.CallToolResult(content=[types.TextContent(type="text", text=message)], is_error=True)


def load_setup(spec: str) -> tuple[list[Policy], list[Labeler]]:
    """Load `module:function`; the function takes no arguments and returns (policies, labelers)."""
    module_name, _, attr = spec.partition(":")
    if not attr:
        raise ValueError(f"--setup must look like module:function, got {spec!r}")
    factory: Callable[[], tuple[Sequence[Policy], Sequence[Labeler]]] = getattr(
        importlib.import_module(module_name), attr
    )
    policies, labelers = factory()
    return list(policies), list(labelers)


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="agentshield-mcp-proxy",
        description="Run an MCP server behind AgentShield. Put the real server's command after --.",
    )
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--server-name", required=True, help="name for the real server, used in labels and logs")
    parser.add_argument("--mode", choices=[m.value for m in Mode], default=Mode.SHADOW.value)
    parser.add_argument("--audit", help="append the hash-chained audit log to this file")
    parser.add_argument("--setup", help="module:function returning (policies, labelers)")
    parser.add_argument("--approvals", help="directory for approval requests; without it, approvals are denied")
    parser.add_argument("--approval-timeout", type=float, default=300.0, help="seconds to wait for a human")
    parser.add_argument("upstream", nargs=argparse.REMAINDER, help="-- command [args...] for the real server")
    args = parser.parse_args(argv)
    if args.upstream and args.upstream[0] == "--":
        args.upstream = args.upstream[1:]
    if not args.upstream:
        parser.error("give the real server's command after --")
    return args


def build_gate(args: argparse.Namespace) -> ToolGate:
    policies, labelers = load_setup(args.setup) if args.setup else ([], [])
    shield = Shield(
        policies=policies,
        labelers=labelers,
        audit=AuditLog(args.audit) if args.audit else None,
        mode=Mode(args.mode),
    )
    approver = FileApprover(args.approvals, timeout=args.approval_timeout) if args.approvals else DenyAll()
    return ToolGate(shield, agent_id=args.agent_id, server=args.server_name, approver=approver)


async def serve(args: argparse.Namespace) -> None:
    gate = build_gate(args)
    command, *command_args = args.upstream
    # The real server gets the proxy's full environment: its credentials are configured on the proxy.
    upstream_params = StdioServerParameters(command=command, args=command_args, env=dict(os.environ))
    async with Client(upstream_params) as upstream:
        server = build_server(upstream, gate, args.server_name)
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())


def main(argv: Sequence[str] | None = None) -> None:
    # stdout carries the MCP protocol; anything human-readable goes to stderr.
    logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="agentshield: %(message)s")
    anyio.run(serve, parse_args(argv))


if __name__ == "__main__":
    main()
