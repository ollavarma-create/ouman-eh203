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
from .transaction import write_and_observe

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
    observed = write_and_observe(journal, send=lambda tx: exchange(ser, tx),
        acknowledge=lambda rx: decode(rx, approved.pid, 0), settle=settle,
        read=lambda: _read(ser, approved), save=lambda: atomic_json(journal_path, journal))
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


# The draft path keeps the same isolated-bench authorization as single edits.
# L1 minimum is an additional candidate already mapped by the restore validator;
# its physical acceptance remains pending.
DRAFT_KEYS = ('l1_room_setpoint', 'l1_supply_min', 'l1_supply_max', 'dhw_setpoint')
DRAFT_MAP = {f[0]: f[1:] for f in FIELDS if f[0] in DRAFT_KEYS}


@dataclass(frozen=True)
class Draft:
    identity: bytes
    identity_length: int
    before: tuple
    after: tuple
    changes: tuple  # (key, old, new), Decimal values
    steps: tuple    # (pid, before state, expected state)


def draft_preview(snapshot, values):
    """Validate the combined final state and group changes by wire block."""
    identity, state = _state(snapshot)
    if set(values) - set(DRAFT_KEYS):
        raise ValueError('Parameter not authorized for physical bench editing')
    target = dict(state)
    changes = []
    for key in DRAFT_KEYS:
        if key not in values:
            continue
        pid, offset, width, signed, factor, _ = DRAFT_MAP[key]
        factor = Decimal(factor)
        value = Decimal(str(values[key]))
        if not value.is_finite():
            raise ValueError('Non-finite value: ' + key)
        old = Decimal(int.from_bytes(state[pid][offset:offset+width], 'big', signed=signed))*factor
        if old == value:
            continue
        lo, hi = PARAMETERS[key]['manual_range']
        raw = value / factor
        bench_lo, bench_hi = BOUNDS[key]
        if not lo <= value <= hi or not bench_lo <= raw <= bench_hi or raw != raw.to_integral_value():
            raise ValueError('Outside documented/bench range or resolution: ' + key)
        data = target[pid]
        target[pid] = data[:offset]+int(raw).to_bytes(width,'big',signed=signed)+data[offset+width:]
        changes.append((key, old, value))
    if target[12] != state[12] and target[12][3] > target[12][4]:
        raise ValueError('Supply minimum exceeds maximum')
    current = dict(state)
    steps = []
    for pid in (12, 13, 16):
        if current[pid] != target[pid]:
            expected = dict(current)
            expected[pid] = target[pid]
            steps.append((pid, tuple(current.items()), tuple(expected.items())))
            current = expected
    return Draft(identity, len(bytes.fromhex(snapshot['records']['1']['data'])),
                 tuple(state.items()), tuple(target.items()), tuple(changes), tuple(steps))


def _apply_draft(ser, approved, safety_path, journal_path, *, settle, progress=None, phase=None):
    notify = phase or (lambda *_: None)
    notify('check', 0)
    if Path(safety_path).resolve() == Path(journal_path).resolve():
        raise ValueError('Distinct safety and journal paths required')
    if Path(safety_path).exists() or Path(journal_path).exists():
        raise FileExistsError('Evidence paths must be new')
    if _read(ser, approved) != dict(approved.before):
        raise ValueError('Stale preview')
    if not approved.steps:
        return None
    notify('backup', 0)
    acquire(ser, safety_path, 0.25, quick=True, progress=progress or (lambda *_: None))
    notify('check', 0)
    safety = load(safety_path)
    values = {key: new for key, _, new in approved.changes}
    if draft_preview(safety, values) != approved or _read(ser, approved) != dict(approved.before):
        raise ValueError('Target changed during safety backup')
    entries = [dict(id=pid, status='not_started', tx=write_frame(pid, dict(after)[pid]).hex(),
                    before={str(i): b.hex() for i,b in before},
                    expected={str(i): b.hex() for i,b in after})
               for pid,before,after in approved.steps]
    journal = dict(schema='ouman.eh203.bench-draft.v1', created_at=utc(),
                   target_identity=approved.identity.hex(), safety=str(safety_path),
                   safety_sha256=safety['records_sha256'], safety_profile=safety['profile'],
                   changes=[dict(key=k, old=str(o), new=str(n)) for k,o,n in approved.changes],
                   entries=entries, status='running', persistence_verified=False)
    def save():
        atomic_json(journal_path, journal)
    save()
    try:
        for entry, (pid, before, after) in zip(entries, approved.steps):
            notify('check_step', pid)
            if _read(ser, approved) != dict(before):
                raise ValueError('Stale plan before next write')
            entry['status'] = 'write_outcome_unknown'
            def send(tx):
                notify('write', pid)
                return exchange(ser, tx)
            def wait():
                notify('settle', pid)
                settle()
            def readback():
                notify('readback', pid)
                return _read(ser, approved)
            observed = write_and_observe(entry, send=send,
                acknowledge=lambda rx: decode(rx,pid,0), settle=wait,
                read=readback, save=save)
            if observed != dict(after):
                raise ValueError('Unexpected readback; inspect journal, do not retry')
            entry['status'] = 'verified'
            save()
            notify('verified', pid)
        notify('final_check', 0)
        if _read(ser, approved) != dict(approved.after):
            raise ValueError('Final state mismatch')
        # Fresh observed capture for display; not a synthetic or modified backup.
        post_path = Path(str(journal_path) + '.after.json')
        notify('final_capture', 0)
        result = acquire(ser, post_path, 0.05, quick=True, progress=progress or (lambda *_: None))
        _, final_state = _state(result)
        if block_identity(result) != approved.identity or final_state != dict(approved.after):
            raise ValueError('Final capture mismatch')
        journal.update(status='complete', verification='readback_only',
                       after_capture=str(post_path), after_sha256=result['records_sha256'])
        save()
        return result
    except Exception as exc:
        journal.update(status='interrupted', error=str(exc))
        save()
        raise


def execute_draft(port, snapshot, approved, safety_path, journal_path, *,
                  confirmation, progress=None, phase=None):
    if confirmation != 'BENCH':
        raise ValueError('Isolated controller confirmation BENCH required')
    if draft_preview(snapshot, {k: n for k, _, n in approved.changes}) != approved:
        raise ValueError('Modified preview')
    with open_serial(port) as ser:
        return _apply_draft(ser, approved, safety_path, journal_path,
                            settle=lambda: time.sleep(5), progress=progress, phase=phase)
