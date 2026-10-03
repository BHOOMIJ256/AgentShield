"""Hash-chained, append-only audit log.

Each line is a JSON entry whose hash covers its sequence number, the previous
entry's hash and its body. Editing, deleting or reordering any line breaks the
chain and is caught by `verify()`.

A chain alone cannot detect the *tail* being cut off, or the whole file being
rewritten by whoever holds it. For that, periodically sign a `Checkpoint` with a
key the agent host cannot read and store it somewhere else; `verify()` then
checks the log still contains exactly that entry.

Single writer per file: concurrent writers in separate processes are not
coordinated.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .model import Decision, Event

if TYPE_CHECKING:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )

GENESIS = "0" * 64


class AuditLogCorrupted(Exception):
    pass


def _canonical(obj: Any) -> bytes:
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    ).encode("utf-8")


def _normalize(body: Any) -> Any:
    """Round-trip through canonical JSON so the hashed form equals the form read back from disk."""
    return json.loads(_canonical(body))


def _entry_hash(seq: int, prev: str, body: Any) -> str:
    return hashlib.sha256(_canonical({"seq": seq, "prev": prev, "body": body})).hexdigest()


@dataclass(frozen=True)
class AuditEntry:
    seq: int
    prev: str
    hash: str
    body: Any


class AuditLog:
    def __init__(self, path: str | os.PathLike[str], *, fsync: bool = False) -> None:
        self.path = Path(path)
        self._fsync = fsync
        self._lock = threading.Lock()
        self._next_seq, self._head = self._load_tail()

    def _load_tail(self) -> tuple[int, str]:
        if not self.path.exists():
            return 0, GENESIS
        last = None
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last = line
        if last is None:
            return 0, GENESIS
        try:
            entry = json.loads(last)
            return entry["seq"] + 1, entry["hash"]
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise AuditLogCorrupted(f"cannot resume from last line of {self.path}: {e}") from e

    @property
    def head(self) -> tuple[int, str]:
        """(seq, hash) of the latest entry; (-1, GENESIS) when empty."""
        return self._next_seq - 1, self._head

    def append(self, body: Any) -> AuditEntry:
        body = _normalize(body)
        with self._lock:
            seq, prev = self._next_seq, self._head
            entry_hash = _entry_hash(seq, prev, body)
            line = _canonical({"seq": seq, "prev": prev, "body": body, "hash": entry_hash})
            with self.path.open("ab") as f:
                f.write(line + b"\n")
                f.flush()
                if self._fsync:
                    os.fsync(f.fileno())
            self._next_seq, self._head = seq + 1, entry_hash
        return AuditEntry(seq, prev, entry_hash, body)

    def record(self, event: Event, decision: Decision | None = None) -> AuditEntry:
        body: dict[str, Any] = {"event": dataclasses.asdict(event)}
        if decision is not None:
            body["decision"] = dataclasses.asdict(decision)
            body["enforced_action"] = decision.enforced_action
        return self.append(body)


@dataclass(frozen=True)
class Checkpoint:
    seq: int
    hash: str
    signature: str  # hex Ed25519 signature over canonical {"seq", "hash"}


def sign_checkpoint(log: AuditLog, private_key: Ed25519PrivateKey) -> Checkpoint:
    seq, head = log.head
    if seq < 0:
        raise ValueError("cannot checkpoint an empty log")
    signature = private_key.sign(_canonical({"seq": seq, "hash": head}))
    return Checkpoint(seq, head, signature.hex())


def verify_checkpoint(checkpoint: Checkpoint, public_key: Ed25519PublicKey) -> bool:
    from cryptography.exceptions import InvalidSignature

    try:
        public_key.verify(
            bytes.fromhex(checkpoint.signature),
            _canonical({"seq": checkpoint.seq, "hash": checkpoint.hash}),
        )
        return True
    except (InvalidSignature, ValueError):
        return False


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    entries: int
    bad_seq: int | None = None
    reason: str | None = None


def verify(
    path: str | os.PathLike[str],
    *,
    checkpoint: Checkpoint | None = None,
    public_key: Ed25519PublicKey | None = None,
) -> VerifyResult:
    """Walk the chain. With a checkpoint, also prove the log was not truncated or rewritten before it."""
    if checkpoint is not None:
        if public_key is None:
            raise ValueError("a checkpoint can only be trusted with the public key that signed it")
        if not verify_checkpoint(checkpoint, public_key):
            return VerifyResult(False, 0, checkpoint.seq, "checkpoint signature invalid")

    expected_seq, prev = 0, GENESIS
    checkpoint_seen = False
    with Path(path).open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                seq, entry_prev, body, entry_hash = (
                    entry["seq"], entry["prev"], entry["body"], entry["hash"],
                )
            except (json.JSONDecodeError, KeyError, TypeError):
                return VerifyResult(False, expected_seq, expected_seq, f"line {lineno} is not a valid entry")
            if seq != expected_seq:
                return VerifyResult(False, expected_seq, expected_seq, f"expected seq {expected_seq}, found {seq}")
            if entry_prev != prev:
                return VerifyResult(False, expected_seq, seq, "previous-hash link broken")
            if _entry_hash(seq, entry_prev, body) != entry_hash:
                return VerifyResult(False, expected_seq, seq, "entry contents do not match its hash")
            if checkpoint is not None and seq == checkpoint.seq:
                if entry_hash != checkpoint.hash:
                    return VerifyResult(False, expected_seq, seq, "entry differs from signed checkpoint")
                checkpoint_seen = True
            prev = entry_hash
            expected_seq += 1

    if checkpoint is not None and not checkpoint_seen:
        return VerifyResult(False, expected_seq, checkpoint.seq, "log ends before signed checkpoint (truncated)")
    return VerifyResult(True, expected_seq)
