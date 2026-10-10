"""Adapters connect AgentShield to real agents.

`gate` and `approval` don't depend on MCP (only on `anyio`), so other adapters can reuse
them; `mcp_proxy` needs the `mcp` extra, which also brings `anyio`.
"""

from .approval import ApprovalRequest, Approver, DenyAll, FileApprover
from .gate import Outcome, ToolGate

__all__ = ["ApprovalRequest", "Approver", "DenyAll", "FileApprover", "Outcome", "ToolGate"]
