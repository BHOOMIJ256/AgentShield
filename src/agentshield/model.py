"""Core data model shared by every interception point, policy and the audit log."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class Trust(str, Enum):
    """How much authority content has, decided by where it entered — never by what it says."""

    TRUSTED = "trusted"  # system policy, internal databases
    USER = "user"  # the authenticated human driving the session
    UNTRUSTED = "untrusted"  # web pages, documents, emails, third-party tools


class Sensitivity(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    SECRET = "secret"  # credentials, keys


class EventKind(str, Enum):
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"
    AGENT_MESSAGE = "agent_message"


class Action(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    REQUIRE_APPROVAL = "require_approval"
    BLOCK = "block"
    TERMINATE = "terminate"


class Mode(str, Enum):
    SHADOW = "shadow"  # record what would have happened, let everything through
    ENFORCE = "enforce"


@dataclass(frozen=True)
class Label:
    """Provenance tag attached to content at the moment it enters the agent."""

    origin: str  # e.g. "tool:read_resume", "db:salaries", "mcp:weather/get_forecast"
    trust: Trust
    sensitivity: Sensitivity = Sensitivity.INTERNAL


@dataclass(frozen=True)
class Event:
    """One thing the agent did or received, as seen at an interception point."""

    kind: EventKind
    session_id: str
    agent_id: str
    name: str  # tool name, memory key, or target agent
    payload: Mapping[str, Any] = field(default_factory=dict)
    labels: tuple[Label, ...] = ()
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class Decision:
    """Output of the policy kernel for one event."""

    action: Action
    mode: Mode = Mode.SHADOW
    reasons: tuple[str, ...] = ()
    policy_id: str | None = None

    @property
    def enforced_action(self) -> Action:
        """What actually happens. In shadow mode everything proceeds; `action` keeps what would have."""
        return self.action if self.mode is Mode.ENFORCE else Action.ALLOW
