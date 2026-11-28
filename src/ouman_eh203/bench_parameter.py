"""Single-field physical bench edits; never a production write interface."""
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import time

from .backup import acquire, verify_file, load, atomic_json, utc
from .metadata import PARAMETERS
from .registry import FIELDS, QUICK_IDS
from .validation import BOUNDS, block
from .restore import IDS, authorize, block_identity
from .protocol import request, write_frame, decode
from .transport import exchange, open_serial

KEYS = ('l1_room_setpoint', 'l1_supply_max', 'dhw_setpoint')
MAP = {f[0]: f[1:] for f in FIELDS if f[0] in KEYS}


@dataclass(frozen=True)
class Preview:
    key: str
    value: Decimal
    old: Decimal
    identity: bytes
    pid: int
    before: tuple
    after: tuple
    identity_length: int


def _state(snapshot):
    verify_file(snapshot)
    # A verified firmware-specific profile covers every known readable ID.
    # Full discovery captures remain valid, but are not required for editing.
    records = snapshot['records']
    if {int(k) for k, v in records.items() if v['status'] == 'accepted'} != set(QUICK_IDS):
        raise ValueError('Complete accepted-ID backup required')
    identity = block_identity(snapshot)
    authorize(identity, identity)
    return identity, {i: block(snapshot, i) for i in IDS}


def preview(snapshot, key, value):
    if key not in MAP:
        raise ValueError('Parameter not authorized for physical bench editing')
    identity, state = _state(snapshot)
    pid, offset, width, signed, factor, _ = MAP[key]
    factor = Decimal(factor)
    value = Decimal(str(value))
    if not value.is_finite():
        raise ValueError('Non-finite value')
    low, high = PARAMETERS[key]['manual_range']
    raw = value / factor
    bench_low, bench_high = BOUNDS[key]
    if not low <= value <= high or not bench_low <= raw <= bench_high or raw != raw.to_integral_value():
        raise ValueError('Outside documented/bench range or resolution')
    data = state[pid]
    old = Decimal(int.from_bytes(data[offset:offset+width], 'big', signed=signed)) * factor
    after = data[:offset] + int(raw).to_bytes(width, 'big', signed=signed) + data[offset+width:]
    if pid == 12 and after[3] > after[4]:
        raise ValueError('Supply maximum below minimum')
    expected = dict(state)
    expected[pid] = after
    return Preview(key, value, old, identity, pid, tuple(state.items()),
                   tuple(expected.items()), len(bytes.fromhex(snapshot['records']['1']['data'])))


def _read(ser, approved):
    identity = decode(exchange(ser, request(1)), 1, approved.identity_length)[:9]
    if identity != approved.identity:
        raise ValueError('Target identity changed')
    return {i: decode(exchange(ser, request(i)), i, len(data))
            for i, data in approved.before}


def _apply(ser, approved, safety_path, journal_path, *, settle, progress=None):
    """One transaction on an exclusively held transport; no automatic retry."""
    if Path(safety_path).resolve() == Path(journal_path).resolve():
        raise ValueError('Distinct safety and journal paths required')
    if Path(safety_path).exists() or Path(journal_path).exists():
        raise FileExistsError('Evidence paths must be new')
    before, after = dict(approved.before), dict(approved.after)
    if _read(ser, approved) != before:
        raise ValueError('Stale preview')
    if before == after:
        return False
    acquire(ser, safety_path, 0.25, quick=True, progress=progress or (lambda *_: None))
    safety = load(safety_path)
    if preview(safety, approved.key, approved.value) != approved:
        raise ValueError('Target changed during safety backup')
    if _read(ser, approved) != before:
        raise ValueError('Target changed after safety backup')
    tx = write_frame(approved.pid, after[approved.pid])
    journal = dict(schema='ouman.eh203.bench-parameter.v1', created_at=utc(),
                   key=approved.key, old=str(approved.old), value=str(approved.value),
                   target_identity=approved.identity.hex(), id=approved.pid,
                   safety=str(safety_path), safety_sha256=safety['records_sha256'], safety_profile=safety['profile'],
                   before={str(i): b.hex() for i, b in before.items()},
                   expected={str(i): b.hex() for i, b in after.items()},
                   tx=tx.hex(), status='write_outcome_unknown', persistence_verified=False)
    atomic_json(journal_path, journal)
    rx = exchange(ser, tx)
    journal['rx'] = rx.hex()
    atomic_json(journal_path, journal)
    decode(rx, approved.pid, 0)
    settle()
    observed = _read(ser, approved)
    journal['observed'] = {str(i): b.hex() for i, b in observed.items()}
    atomic_json(journal_path, journal)
    if observed != after:
        raise ValueError('Unexpected readback; inspect journal, do not retry')
    journal.update(status='verified', verification='readback_only')
    atomic_json(journal_path, journal)
    return True


def execute_bench(port, snapshot, approved, safety_path, journal_path, *,
                  confirmation, progress=None):
    if confirmation != 'BENCH':
        raise ValueError('Isolated controller confirmation BENCH required')
    if preview(snapshot, approved.key, approved.value) != approved:
        raise ValueError('Modified preview')
    with open_serial(port) as ser:
        return _apply(ser, approved, safety_path, journal_path,
                      settle=lambda: time.sleep(5), progress=progress)
