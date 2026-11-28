#!/usr/bin/env python3
"""Read-only EH-203 firmware 2.15 raw backup and independently classified comparison.

No wire opcode other than canonical 0x81 is constructed by this program.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time

SCHEMA = 'ouman.eh203.backup.v1'
SERIAL = {'baudrate': 4800, 'bytesize': 8, 'parity': 'N', 'stopbits': 1}
# Only independently LCD-confirmed persistent fields, never live or identity bytes.
# name, ID, zero-based data offset, width, signed, multiplier, unit
from .registry import FIELDS, QUICK_IDS
from .protocol import request, classify
from .transport import read_exact

def utc():
    return datetime.now(timezone.utc).isoformat()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def digest(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(value, f, indent=2, ensure_ascii=False)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        dirfd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def exchange(ser, pid):
    tx = request(pid)
    ser.reset_input_buffer()
    started = time.monotonic()
    count = ser.write(tx)
    if count != len(tx):
        raise OSError('Short serial write of read request')
    ser.flush()
    head = read_exact(ser, 3)
    rx = head
    if len(head) == 3 and head[0] == 2:
        rx += read_exact(ser, head[2] + 1)
    status, payload, error = classify(rx, pid)
    return {'id': pid, 'tx': tx.hex(' ').upper(), 'rx': rx.hex(' ').upper(),
            'status': status, 'data': payload.hex(' ').upper() if payload is not None else None,
            'error': error, 'response_ms': round((time.monotonic() - started) * 1000, 2),
            'captured_at': utc()}


def acquire(ser, destination, delay, start=0, end=255, quick=False, *, progress=None, cancelled=None):
    """Persist every response immediately, keeping partial failures for forensics."""
    if not 0 <= start <= end <= 255:
        raise ValueError('Invalid ID range')
    if Path(destination).exists():
        raise FileExistsError(f'Capture target already exists: {destination}')
    output = {'schema': SCHEMA, 'created_at': utc(), 'finished_at': None,
              'device': {'model': 'EH-203', 'expected_firmware': '2.15', 'serial_port': getattr(ser, 'port', None),
                         'wire': SERIAL}, 'range': [start, end], 'complete': False, 'records': {}}
    ids = list(range(start, end + 1))
    if quick:
        ids = QUICK_IDS
        output['profile'] = 'eh203-2.15-bench-v1'
    atomic_json(destination, output)
    try:
        for pid in ids:
            if cancelled is not None and cancelled():
                break
            try:
                rec = exchange(ser, pid)
            except (OSError, ValueError) as exc:
                rec = {'id': pid, 'tx': request(pid).hex(' ').upper(), 'rx': '', 'status': 'invalid',
                       'data': None, 'error': str(exc), 'captured_at': utc()}
                output['records'][str(pid)] = rec
                atomic_json(destination, output)
                raise
            output['records'][str(pid)] = rec
            atomic_json(destination, output)
            if progress is None:
                print(f'ID {pid:3}: {rec["status"]}', flush=True)
            else:
                progress(len(output['records']), len(ids))
            if delay and pid != end:
                time.sleep(delay)
    finally:
        output['finished_at'] = utc()
        output['complete'] = (len(output['records']) == len(ids) and all(
            record['status'] in ('accepted', 'rejected') for record in output['records'].values()))
        output['records_sha256'] = digest(output['records'])
        atomic_json(destination, output)
    return output





def verify_file(obj, require_full=True):
    if obj.get('schema') != SCHEMA:
        raise ValueError('Unknown schema')
    a, b = obj['range']
    if require_full and [a, b] != [0, 255]:
        raise ValueError('Not a complete 0..255 capture')
    records = obj['records']
    ids = QUICK_IDS if obj.get('profile') == 'eh203-2.15-bench-v1' else list(range(a,b+1))
    if set(records) != {str(x) for x in ids}:
        raise ValueError('Missing or extra IDs')
    if obj.get('records_sha256') != digest(records):
        raise ValueError('SHA256 mismatch (raw record data modified)')
    if not obj.get('complete'):
        raise ValueError('Capture incomplete')
    for pid in ids:
        rec = records[str(pid)]
        if rec['id'] != pid or bytes.fromhex(rec['tx']) != request(pid):
            raise ValueError(f'ID {pid}: request mismatch')
        state, data, error = classify(bytes.fromhex(rec['rx']), pid)
        if state != rec['status'] or error is not None or rec['data'] != (
                data.hex(' ').upper() if data is not None else None):
            raise ValueError(f'ID {pid}: response mismatch')
    if require_full and {int(k) for k,v in records.items() if v['status']=='accepted'} != set(QUICK_IDS):
        raise ValueError('Quick profile mismatch; run full capture')
    ident = records['1']
    if require_full:
        if ident['status'] != 'accepted':
            raise ValueError('ID 1 identity unavailable')
        raw = bytes.fromhex(ident['data'])
        if len(raw) < 9 or raw[4:7] != b'203' or raw[8] != 215:
            raise ValueError('Not confirmed EH-203 firmware 2.15')
    return True


def known_fields(snapshot):
    verify_file(snapshot)
    out = {}
    for name, pid, offset, width, signed, factor, unit in FIELDS:
        r = snapshot['records'][str(pid)]
        if r['status'] != 'accepted':
            raise ValueError(f'Missing known field {name}')
        data = bytes.fromhex(r['data'])
        if len(data) < offset+width:
            raise ValueError(f'Truncated known field {name}')
        raw = int.from_bytes(data[offset:offset+width], 'big', signed=signed)
        val = Decimal(raw)*Decimal(factor)
        out[name] = {'value': str(val), 'raw': raw, 'unit': unit, 'id': pid,
                     'data_offset': offset, 'width': width, 'signed': signed,
                     'confidence': 'lcd_confirmed', 'write_authorized': False}
    return {'schema': 'ouman.eh203.known-settings.v1', 'source_records_sha256': snapshot['records_sha256'],
            'model': 'EH-203', 'firmware': '2.15', 'read_only': True, 'fields': out,
            'note': 'Selective documented observations only; not a complete portable configuration.'}


def compare(first, second):
    verify_file(first)
    verify_file(second)
    a, b = bytes.fromhex(first['records']['1']['data']), bytes.fromhex(second['records']['1']['data'])
    if a[:9] != b[:9]:
        raise ValueError('Controller identity/firmware changed; no comparison')
    f1, f2 = known_fields(first)['fields'], known_fields(second)['fields']
    field_changes = {name: {'before': f1.get(name, {}).get('value'), 'after': f2.get(name, {}).get('value')}
                     for name in sorted(set(f1) | set(f2)) if f1.get(name) != f2.get(name)}
    raw_changes = []
    raw_diffs = {}
    live_ids = {2, 3, 15, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 33, 34, 36, 38, 41, 46, 49, 50, 51, 54, 56, 58, 59, 60, 61}
    for pid in sorted(map(int, set(first['records']) & set(second['records']))):
        r1, r2 = first['records'][str(pid)], second['records'][str(pid)]
        if (r1['status'], r1['data']) != (r2['status'], r2['data']):
            raw_changes.append(pid)
            if r1['status'] == r2['status'] == 'accepted':
                x, y = bytes.fromhex(r1['data']), bytes.fromhex(r2['data'])
                offsets = [i for i in range(max(len(x), len(y))) if x[i:i+1] != y[i:i+1]]
            else:
                offsets = None
            raw_diffs[str(pid)] = {'before_status': r1['status'], 'after_status': r2['status'],
                                   'changed_data_offsets': offsets,
                                   'category': 'timestamp_candidate' if offsets and set(offsets) <= {2: set(range(7)), 3: set(range(7)), 36: set(range(6,13)), 38: set(range(6,13)), 46: {21,22}}.get(pid, set()) else 'unknown_or_configuration_review_required'}
    if field_changes:
        status = 'settings_changed'
    elif raw_changes:
        status = 'known_settings_match_raw_differs'
    else:
        status = 'exact_payload_match'
    return {'schema': 'ouman.eh203.comparison.v1', 'created_at': utc(), 'status': status,
            'same_device': True, 'compared_ids': len(set(first['records']) & set(second['records'])), 'known_fields_compared': len(f1), 'known_field_changes': field_changes,
            'raw_payload_changed_ids': raw_changes, 'raw_payload_differences': raw_diffs,
            'raw_payload_exact_match': not raw_changes,
            'warning': ('Known-field equality does not prove complete settings preservation. '
                        'Unknown and unexported configuration may change; inspect raw diffs before reset.'),
            'first_records_sha256': first['records_sha256'],
            'second_records_sha256': second['records_sha256']}


def load(path):
    with open(path, encoding='utf-8') as file:
        return json.load(file)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    cap = sub.add_parser('capture', help='Read all 256 IDs and save durable raw evidence')
    cap.add_argument('--quick', action='store_true', help='Use bench firmware 2.15 profile; full capture required for discovery')
    cap.add_argument('--port', default='/dev/ttyUSB0')
    cap.add_argument('--output', type=Path, required=True)
    cap.add_argument('--delay', type=float, default=0.25)
    export = sub.add_parser('export', help='Export confirmed known settings from a verified capture')
    export.add_argument('capture', type=Path)
    export.add_argument('--output', type=Path, required=True)
    check = sub.add_parser('verify', help='Validate a complete capture offline')
    check.add_argument('capture', type=Path)
    diff = sub.add_parser('compare', help='Compare two complete captures with the same device identity')
    diff.add_argument('first', type=Path)
    diff.add_argument('second', type=Path)
    diff.add_argument('--output', type=Path, required=True)
    args = p.parse_args(argv)
    try:
        if args.action in ('capture', 'export', 'compare') and args.output.exists():
            raise FileExistsError(f'Output already exists: {args.output}')
        if args.action == 'capture':
            if args.delay < 0:
                raise ValueError('Delay cannot be negative')
            import serial
            with serial.Serial(args.port, 4800, timeout=1.5, write_timeout=1.5,
                               exclusive=True, rtscts=False, dsrdtr=False, xonxoff=False) as ser:
                result = acquire(ser, args.output, args.delay, quick=args.quick)
            if not result['complete']:
                raise ValueError('Incomplete acquisition; preserved partial evidence')
            verify_file(result)
            print('Complete capture verified:', args.output)
        elif args.action == 'verify':
            verify_file(load(args.capture))
            print('Capture structurally verified; not yet a complete settings backup')
        elif args.action == 'export':
            atomic_json(args.output, known_fields(load(args.capture)))
            print('Selective read-only settings export:', args.output)
        else:
            report = compare(load(args.first), load(args.second))
            atomic_json(args.output, report)
            print('Comparison:', report['status'], '| changed raw IDs:', report['raw_payload_changed_ids'])
            if report['known_field_changes']:
                return 2
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print('ERROR:', exc)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
