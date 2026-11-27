#!/usr/bin/env python3
"""EH-203 offline planning and explicitly confirmed bench block restore."""
import argparse
import json
from pathlib import Path
import backup
from write_parameter import PARAMETERS

def plan(source, current):
    for snap in (source, current):
        backup.verify_file(snap)
        if snap.get('profile') or set(snap['records']) != {str(i) for i in range(256)}:
            raise ValueError('Full captures required')
        accepted = {int(k) for k,v in snap['records'].items() if v['status']=='accepted'}
        if accepted != set(backup.QUICK_IDS):
            raise ValueError('Unexpected accepted ID set')
    def data(s, pid):
        return bytes.fromhex(s['records'][str(pid)]['data'])
    if data(source,1)[:9] != data(current,1)[:9]:
        raise ValueError('Different controller identity')
    desired = backup.known_fields(source)['fields']
    actual = backup.known_fields(current)['fields']
    changes = []
    covered = {}
    for name, target in desired.items():
        old = actual[name]
        pid, offset, width = target['id'], target['data_offset'], target['width']
        covered.setdefault(pid,set()).update(range(offset,offset+width))
        prefix = name[:2]
        curve = name.startswith(('l1_curve_', 'l2_curve_'))
        mode_change = curve and desired[prefix+'_curve_type']['raw'] != actual[prefix+'_curve_type']['raw']
        if old['raw'] == target['raw'] and not (mode_change and not name.endswith('_type')):
            continue
        tested = PARAMETERS.get(name)
        in_range = bool(tested and tested[:3] == (pid,offset,width) and
                        all(tested[3] <= v <= tested[4] for v in (old['raw'],target['raw'])))
        changes.append(dict(name=name,id=pid,offset=offset,width=width,
                            current=old['value'],target=target['value'],unit=target['unit'],
                            current_raw=old['raw'],target_raw=target['raw'],
                            phase=10 if name.endswith('_curve_type') else 20 if curve else 30,
                            depends_on=[prefix+'_curve_type'] if curve and not name.endswith('_type') and mode_change else [],
                            reason='mode change requires recheck' if old['raw']==target['raw'] else 'value differs',
                            experimental_range_match=in_range,write_authorized=False))
    changes.sort(key=lambda c:(c['phase'],c['id'],c['offset']))
    unresolved = []
    for pid in backup.QUICK_IDS:
        a,b=data(source,pid),data(current,pid)
        offsets=[i for i in range(max(len(a),len(b))) if a[i:i+1]!=b[i:i+1] and i not in covered.get(pid,set())]
        if offsets:
            unresolved.append(dict(id=pid,offsets=offsets,
                category='schedule_candidate' if 4<=pid<=9 else 'unmapped_or_runtime',
                write_authorized=False))
    return dict(schema='ouman.eh203.restore-plan.v1',created_at=backup.utc(),
                source_sha256=source['records_sha256'],current_sha256=current['records_sha256'],
                dry_run=True,execution_supported=False,compared_ids=256,
                known_fields_compared=len(desired),changes=changes,unmapped_differences=unresolved,
                warning='All operations blocked. Experimental range match is not write authorization. Re-read after dependency changes. Unmapped bytes are never restored.')

# Only these bytes may be patched. Other mapped fields remain blocked.
BENCH_FIELDS = {12: ('l1_supply_max','l1_room_gain'),
                13: ('l1_room_setpoint',),
                14: (), 16: ('dhw_setpoint',)}
BOUNDS = {'l1_supply_max': (15, 95), 'l1_room_gain': (0, 100),
          'l1_room_setpoint': (100, 300), 'dhw_setpoint': (500, 650)}

def block(snapshot, pid):
    raw = bytes.fromhex(snapshot['records'][str(pid)]['data'])
    if len(raw) != 31:
        raise ValueError('Unexpected block size')
    return raw

def propose(source, pid, before):
    target = block(source, pid)
    old = before[pid]
    expected = dict(before)
    if pid in (65,66):
        if any(before[i][0] != 0 or block(source,i)[0] != 0 for i in (65,66)):
            raise ValueError('Five-point mode required; use validated mode probe first')
        ys = list(target[1:6])
        xs = [-20]+[int.from_bytes(target[j:j+1],'big',signed=True) for j in (6,7,8)]+[20]
        if not all(a<b for a,b in zip(xs,xs[1:])) or not all(a>=b for a,b in zip(ys,ys[1:])) or not all(15<=y<=70 for y in ys):
            raise ValueError('Curve outside bench bounds')
        mirror = 12 if pid==65 else 14
        if before[mirror][:3] != bytes(old[j] for j in (1,3,5)):
            raise ValueError('Initial mirror mismatch')
        expected[pid] = old[:1]+target[1:9]+old[9:]
        expected[mirror] = bytes(target[j] for j in (1,3,5))+before[mirror][3:]
    else:
        modified = bytearray(old)
        for name, i, offset, width, signed, factor, unit in backup.FIELDS:
            if i != pid or name not in BENCH_FIELDS[pid]:
                continue
            value = int.from_bytes(target[offset:offset+width],'big',signed=signed)
            low, high = BOUNDS[name]
            if not low <= value <= high:
                raise ValueError('Outside conservative bench bounds: '+name)
            modified[offset:offset+width] = target[offset:offset+width]
        if pid==12 and modified[3]>modified[4]:
            raise ValueError('Supply min exceeds max')
        expected[pid] = bytes(modified)
    return expected

def live(source, pid, path, port, execute):
    import time
    import serial
    from write_parameter import frame, decode
    backup.verify_file(source)
    if source.get('profile') or {int(k) for k,v in source['records'].items() if v['status']=='accepted'} != set(backup.QUICK_IDS):
        raise ValueError('Verified full source required')
    ids = (12,13,14,16,65,66)
    record = dict(schema='ouman.eh203.block-restore.v1', source_sha256=source['records_sha256'],
                  id=pid, status='started', created_at=backup.utc(), frames=[])
    with path.open('x') as f:
        json.dump(record,f)
    def save():
        backup.atomic_json(path,record)
    try:
        with serial.Serial(port,4800,timeout=1.5,write_timeout=1.5,exclusive=True,
                           rtscts=False,dsrdtr=False,xonxoff=False) as ser:
            def exchange(tx):
                e = dict(tx=tx.hex(' '))
                record['frames'].append(e)
                save()
                ser.reset_input_buffer()
                if ser.write(tx)!=len(tx):
                    raise OSError('Short write')
                ser.flush()
                h=backup.read_exact(ser,3)
                rx=h+backup.read_exact(ser,h[2]+1) if len(h)==3 and h[0]==2 else h
                e['rx']=rx.hex(' ')
                save()
                return rx
            ident=exchange(frame(0x81,1))
            if decode(ident,1,len(ident)-6)[:9]!=bytes.fromhex(source['records']['1']['data'])[:9]:
                raise ValueError('Controller mismatch')
            def read():
                return {i:decode(exchange(frame(0x81,i)),i,31) for i in ids}
            before=read()
            expected=propose(source,pid,before)
            record.update(before={i:v.hex(' ') for i,v in before.items()},
                          expected={i:v.hex(' ') for i,v in expected.items()})
            record['status']='preview'
            save()
            print('ID',pid,'before:',before[pid].hex(' '),'target:',expected[pid].hex(' '))
            if before==expected:
                record['status']='unchanged'
                return 0
            if not execute:
                return 0
            if input('Isolated bench, no connected loads. Type BENCH: ')!='BENCH':
                record['status']='cancelled'
                return 1
            if read()!=before:
                raise ValueError('Blocks changed since preview')
            record['status']='write_outcome_unknown'
            save()
            ack=exchange(frame(0x82,pid,expected[pid]))
            time.sleep(1)
            after=read()
            record['after']={i:v.hex(' ') for i,v in after.items()}
            save()
            decode(ack,pid,0)
            if after!=expected:
                raise ValueError('Unexpected readback; stop without retry')
            record['status']='verified_pending_final_reboot'
            return 0
    except (Exception,KeyboardInterrupt) as exc:
        record['error']=str(exc)
        if record['status']!='write_outcome_unknown':
            record['status']='failed_before_write'
        print('STOP:',exc)
        return 1
    finally:
        save()

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    m=p.add_mutually_exclusive_group(required=True)
    m.add_argument('--dry-run',action='store_true')
    m.add_argument('--live-preview',action='store_true')
    m.add_argument('--execute-bench',action='store_true')
    p.add_argument('--block',type=int,choices=(12,13,16,65,66))
    p.add_argument('--port',default='/dev/ttyUSB0')
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--current',type=Path)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(argv)
    try:
        if args.output.exists():
            raise FileExistsError('Output exists')
        if not args.dry_run:
            if args.block is None or args.current is not None:
                raise ValueError('Live mode requires --block and no --current')
            return live(backup.load(args.source),args.block,args.output,args.port,args.execute_bench)
        if args.current is None or args.block is not None:
            raise ValueError('Offline dry-run requires --current and no --block')
        result=plan(backup.load(args.source),backup.load(args.current))
        # Exclusive creation prevents accidental replacement of evidence.
        with args.output.open('x',encoding='utf-8') as f:
            json.dump(result,f,indent=2,ensure_ascii=False)
            f.write('\n')
        print('Dry-run:',len(result['changes']),'planned fields;',len(result['unmapped_differences']),'unmapped IDs; no writes')
        return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print('ERROR:',exc)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
