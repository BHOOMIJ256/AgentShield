import datetime
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agentshield import (
    Action,
    AuditLog,
    AuditLogCorrupted,
    Checkpoint,
    Decision,
    Event,
    EventKind,
    Label,
    Mode,
    Sensitivity,
    Trust,
    sign_checkpoint,
    verify,
)


def _event(name="send_email", **payload):
    return Event(
        kind=EventKind.TOOL_CALL,
        session_id="s1",
        agent_id="hr-agent",
        name=name,
        payload=payload,
        labels=(Label("tool:read_resume", Trust.UNTRUSTED), Label("db:salaries", Trust.TRUSTED, Sensitivity.CONFIDENTIAL)),
    )


def _fill(path, n=3):
    log = AuditLog(path)
    for i in range(n):
        log.record(_event(to=f"user{i}@example.com"), Decision(Action.BLOCK, reasons=("trifecta",)))
    return log


def _lines(path):
    return path.read_text(encoding="utf-8").splitlines()


def _write_lines(path, lines):
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_clean_log_verifies(tmp_path):
    path = tmp_path / "audit.jsonl"
    _fill(path)
    result = verify(path)
    assert result.ok and result.entries == 3


def test_record_keeps_labels_and_shadow_outcome(tmp_path):
    path = tmp_path / "audit.jsonl"
    entry = AuditLog(path).record(_event(), Decision(Action.BLOCK, mode=Mode.SHADOW))
    assert entry.body["decision"]["action"] == "block"
    assert entry.body["enforced_action"] == "allow"
    assert entry.body["event"]["labels"][0] == {"origin": "tool:read_resume", "trust": "untrusted", "sensitivity": "internal"}


def test_reopening_continues_the_chain(tmp_path):
    path = tmp_path / "audit.jsonl"
    _fill(path, 2)
    log = AuditLog(path)
    assert log.head[0] == 1
    log.record(_event())
    assert verify(path).ok and verify(path).entries == 3


def test_edited_entry_is_detected(tmp_path):
    path = tmp_path / "audit.jsonl"
    _fill(path)
    lines = _lines(path)
    entry = json.loads(lines[1])
    entry["body"]["decision"]["action"] = "allow"
    lines[1] = json.dumps(entry)
    _write_lines(path, lines)
    result = verify(path)
    assert not result.ok and result.bad_seq == 1


def test_deleted_entry_is_detected(tmp_path):
    path = tmp_path / "audit.jsonl"
    _fill(path)
    lines = _lines(path)
    del lines[1]
    _write_lines(path, lines)
    assert not verify(path).ok


def test_reordered_entries_are_detected(tmp_path):
    path = tmp_path / "audit.jsonl"
    _fill(path)
    lines = _lines(path)
    lines[0], lines[1] = lines[1], lines[0]
    _write_lines(path, lines)
    assert not verify(path).ok


def test_truncation_is_only_caught_with_a_checkpoint(tmp_path):
    path = tmp_path / "audit.jsonl"
    log = _fill(path)
    key = Ed25519PrivateKey.generate()
    checkpoint = sign_checkpoint(log, key)

    _write_lines(path, _lines(path)[:-1])

    assert verify(path).ok  # the chain alone cannot see a cut tail
    result = verify(path, checkpoint=checkpoint, public_key=key.public_key())
    assert not result.ok and "truncated" in result.reason


def test_rewritten_log_fails_against_checkpoint(tmp_path):
    path = tmp_path / "audit.jsonl"
    log = _fill(path)
    key = Ed25519PrivateKey.generate()
    checkpoint = sign_checkpoint(log, key)

    # An attacker with file access rebuilds a fully consistent chain from scratch.
    path.unlink()
    forged = AuditLog(path)
    for _ in range(3):
        forged.record(_event(to="nobody@example.com"), Decision(Action.ALLOW))

    assert verify(path).ok
    result = verify(path, checkpoint=checkpoint, public_key=key.public_key())
    assert not result.ok and "checkpoint" in result.reason


def test_forged_checkpoint_is_rejected(tmp_path):
    path = tmp_path / "audit.jsonl"
    log = _fill(path)
    real = sign_checkpoint(log, Ed25519PrivateKey.generate())
    other_key = Ed25519PrivateKey.generate()

    assert not verify(path, checkpoint=real, public_key=other_key.public_key()).ok
    tampered = Checkpoint(real.seq, "f" * 64, real.signature)
    assert not verify(path, checkpoint=tampered, public_key=other_key.public_key()).ok


def test_checkpoint_requires_public_key(tmp_path):
    path = tmp_path / "audit.jsonl"
    checkpoint = sign_checkpoint(_fill(path), Ed25519PrivateKey.generate())
    with pytest.raises(ValueError):
        verify(path, checkpoint=checkpoint)


def test_empty_log_cannot_be_checkpointed(tmp_path):
    with pytest.raises(ValueError):
        sign_checkpoint(AuditLog(tmp_path / "audit.jsonl"), Ed25519PrivateKey.generate())


def test_non_json_payload_values_still_verify(tmp_path):
    path = tmp_path / "audit.jsonl"
    AuditLog(path).record(_event(when=datetime.datetime(2026, 10, 2, 9, 30), amount=10_000.5, ids={3, 1}))
    assert verify(path).ok


def test_corrupt_tail_refuses_to_resume(tmp_path):
    path = tmp_path / "audit.jsonl"
    _fill(path)
    with path.open("a", encoding="utf-8") as f:
        f.write('{"seq": 3, "prev": "trunc')
    with pytest.raises(AuditLogCorrupted):
        AuditLog(path)
