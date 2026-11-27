#!/usr/bin/env python3
"""EH-203 offline planning and explicitly confirmed bench block restore."""
import argparse
import json
from decimal import Decimal
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
BENCH_FIELDS = {12: ('l1_supply_max','l1_room_gain','l1_supply_min','l1_night_reduction','l1_parallel_shift','l1_autumn_drying','l1_outdoor_delay'),
                13: ('l1_room_setpoint','l1_p_band','l1_i_time','l1_d_time','l1_actuator_time','l2_p_band','l2_i_time','l2_d_time','l2_actuator_time'),
                14: ('l2_supply_min','l2_supply_max','l2_night_reduction','l2_parallel_shift','l2_autumn_drying','l2_outdoor_delay'), 16: ('dhw_setpoint','dhw_p_band','dhw_i_time','dhw_d_time','dhw_feedforward','dhw_fast_drive','dhw_alarm_delay','dhw_deviation_alarm')}
BENCH_FIELDS[44] = ('r1_config','r2_config','r1_outdoor_threshold','r1_temperature_threshold','energy_pulse_factor','district_water_pulse','consumption_water_pulse')
BENCH_FIELDS[47] = ('pressure_range','pressure_upper_alarm','pressure_filling_alarm','pressure_lower_alarm','consumption_alarm_interval')
BOUNDS = {'l1_supply_max': (15, 95), 'l1_room_gain': (0, 100),
          'l1_room_setpoint': (100, 300), 'dhw_setpoint': (500, 650)}

# Experimental bounds, not manufacturer specifications.
for prefix in ('l1','l2'):
    for suffix, bounds in {'supply_min':(0,70),'supply_max':(15,95),
        'night_reduction':(0,40),'parallel_shift':(-20,20),
        'autumn_drying':(0,20),'outdoor_delay':(0,24),
        'p_band':(1,500),'i_time':(0,1000),'d_time':(0,1000),
        'actuator_time':(10,600)}.items():
        BOUNDS[prefix+'_'+suffix]=bounds
BOUNDS.update(dhw_p_band=(1,500),dhw_i_time=(0,1000),dhw_d_time=(0,1000),
              dhw_feedforward=(0,500),dhw_fast_drive=(0,100),
              dhw_alarm_delay=(0,360),dhw_deviation_alarm=(0,50))

BOUNDS.update(district_water_pulse=(0,100),consumption_water_pulse=(0,17),energy_pulse_factor=(0,10),r1_config=(0,8),r2_config=(0,4),
              r1_outdoor_threshold=(-30,30),r1_temperature_threshold=(0,100),
              pressure_range=(1,100),pressure_upper_alarm=(0,100),
              pressure_filling_alarm=(0,100),pressure_lower_alarm=(0,100),
              consumption_alarm_interval=(0,255))
# ID47 is short; use the verified source length, not a 31-byte assumption.
def block(snapshot, pid):
    raw = bytes.fromhex(snapshot['records'][str(pid)]['data'])
    if (pid in (96,98,99)):
        if len(raw)!=(1 if pid==96 else 182):
            raise ValueError('Unexpected GSM block size')
        return raw
    if (pid == 43 and len(raw)!=2) or (pid not in (43,47) and len(raw)!=31) or (pid == 47 and not 7 <= len(raw) <= 31):
        raise ValueError('Unexpected block size')
    return raw

def schedule_rows(times, events, pair):
    if len(times)!=31 or len(events)!=31:
        raise ValueError('Invalid schedule block length')
    allowed=(0x10,0x20,0x11,0x21,0x12,0x22) if pair in (4,6) else (0x13,0x23,0x14,0x24)
    rows=[]
    for i in range(14):
        minute=int.from_bytes(times[1+2*i:3+2*i],'big')
        mask,kind=events[i],events[14+i]
        if minute>=1440 or mask>127 or kind not in (0,*allowed) or (mask and not kind):
            raise ValueError('Unsupported schedule slot')
        if kind or mask or minute:
            rows.append(dict(slot=i+1,time=f'{minute//60:02}:{minute%60:02}',
                days=[d for j,d in enumerate(('Ma','Ti','Ke','To','Pe','La','Su')) if mask & (1<<j)],
                event=f'0x{kind:02X}',mask=mask))
    return rows

def schedule_key(times, events, pair):
    # Preserve duplicates and inactive nonempty slots; ignore slot order only.
    return sorted((r['time'],r['mask'],r['event']) for r in schedule_rows(times,events,pair))

def schedule_equal(a,b,pid):
    return (a[pid][:1]==b[pid][:1] and a[pid][29:]==b[pid][29:]
        and a[pid+1][28:]==b[pid+1][28:]
        and schedule_key(a[pid],a[pid+1],pid)==schedule_key(b[pid],b[pid+1],pid))

def propose(source, pid, before):
    target = block(source, pid)
    old = before[pid]
    expected = dict(before)
    if pid in (4,6,8):
        if pid in (4,6):
            desired=dict(before)
            for j in (4,6):
                desired[j]=before[j][:1]+block(source,j)[1:29]+before[j][29:]
                desired[j+1]=block(source,j+1)[:28]+before[j+1][28:]
            def combined(d):
                return sorted(schedule_key(d[4],d[5],4)+schedule_key(d[6],d[7],6))
            if combined(before)==combined(desired):
                return dict(before)
            # Do not overwrite a populated shared table piecemeal.
            if any(schedule_key(before[j],before[j+1],j) for j in (4,6)):
                # Allow the previously tested empty second pair continuation only.
                if not (pid==6 and schedule_equal(before,desired,4) and not schedule_key(before[6],before[7],6)):
                    raise ValueError('Shared schedule differs; populated table replacement not validated')
        other=pid+1
        events=block(source,other)
        schedule_rows(target,events,pid)
        schedule_rows(old,before[other],pid)
        expected[pid]=old[:1]+target[1:29]+old[29:]
        expected[other]=events[:28]+before[other][28:]
        if schedule_equal(before,expected,pid):
            return dict(before)
    elif pid == 95:
        if old[5:]!=target[5:] or target[0]!=1 or not target[1:5].isdigit():
            raise ValueError('Unexpected GSM identity layout')
        if old[:5]!=target[:5] and old[:5]!=b'\x000000':
            raise ValueError('GSM identity transition outside bench proposal')
        expected[pid]=target[:5]+old[5:]
    elif pid == 43:
        codes=(target[1]&15,target[1]>>4,target[0]&15)
        if any(c>6 for c in codes) or codes.count(2)>1:
            raise ValueError('Unsupported digital input assignment')
        expected[pid]=bytes(((old[0]&0xf0)|codes[2],target[1]))
        if expected[pid]!=old:
            if old!=b'\x00\x00' or expected[pid]!=b'\x04\x00' or before[17][17]!=0x63:
                raise ValueError('Digital transition not yet validated')
            mirror=bytearray(before[17])
            mirror[17]=2
            expected[17]=bytes(mirror)
        elif codes[2]==4 and before[17][17]!=2:
            raise ValueError('Unexpected Dig3 energy routing')
    elif pid == 17:
        # Only individually observed routing slots and codes. Never copy unknown bytes.
        modified=bytearray(old)
        for offset in (8,9,11,12,19):
            if old[offset]==target[offset]:
                continue
            allowed={5,12} if offset in (9,19) else {5,11,12} if offset in (8,11) else {11,12}
            if old[offset] not in allowed or target[offset] not in allowed:
                raise ValueError('Unverified routing transition')
            modified[offset]=target[offset]
        if any(modified.count(c)>1 for c in (5,11)):
            raise ValueError('Potential duplicate routing; manual review required')
        expected[pid]=bytes(modified)
    elif pid in (65,66):
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
        if pid in (12,14) and modified[3]>modified[4]:
            raise ValueError('Supply min exceeds max')
        if pid == 44:
            for offset, target_value in ((4,100),(18,17)):
                if modified[offset]!=old[offset] and (before[43]!=b'\x04\x00' or before[17][17]!=2 or old[offset]!=0 or modified[offset]!=target_value):
                    raise ValueError('Water pulse transition outside bench proposal')
            if modified[2]!=old[2] and (before[43]!=b'\x04\x00' or before[17][17]!=2 or old[2]!=0 or modified[2]!=10):
                raise ValueError('Energy pulse transition outside tested bench proposal')
            pair = tuple(modified[9:11])
            if pair[0] not in (0,1,4) or pair[1] not in (0,1,4,6,7,8) or ((pair[0]==4)!=(pair[1]==4)):
                raise ValueError('Unsupported coupled relay configuration')
            if pair[1]==8 and old[10]!=8:
                raise ValueError('Burner mode requires separate dependency validation')
        if pid == 47 and not modified[3] <= modified[2] <= modified[1] <= modified[0]:
            raise ValueError('Pressure limits out of order')
        if pid == 16:
            for offset, initial, final in ((4,0,5),(6,65,72)):
                if old[offset]!=target[offset]:
                    if (old[offset],target[offset])!=(initial,final) or old[offset-1]!=0 or target[offset-1]!=0:
                        raise ValueError('DHW parameter transition outside bench proposal')
                    modified[offset]=target[offset]
        if pid == 14:
            for offset, initial, final in ((25,70,83),(26,5,9)):
                if old[offset]!=target[offset]:
                    if (old[offset],target[offset])!=(initial,final) or before[44][10]!=7:
                        raise ValueError('Burner parameter transition outside bench proposal')
                    modified[offset]=target[offset]
        if pid == 12:
            desired_delay=target[20]
            if block(source,14)[16]!=desired_delay or old[20]!=before[14][16]:
                raise ValueError('Room delay mirror mismatch')
            if old[20]!=desired_delay:
                if (old[20],desired_delay)!=(5,15):
                    raise ValueError('Room delay outside bench proposal')
                modified[20]=desired_delay
                mirror=bytearray(before[14])
                mirror[16]=desired_delay
                expected[14]=bytes(mirror)
        expected[pid] = bytes(modified)
    return expected

def live(source, pid, path, port, execute):
    import time
    import serial
    from write_parameter import frame, decode
    backup.verify_file(source)
    if source.get('profile') or {int(k) for k,v in source['records'].items() if v['status']=='accepted'} != set(backup.QUICK_IDS):
        raise ValueError('Verified full source required')
    ids = (4,5,6,7,8,9,12,13,14,16,44,47,65,66) if pid in (4,6,8) else (12,13,14,16,17,43,44,47,65,66)
    if pid == 95:
        ids = ids + (95,96,98,99)
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
                return {i:decode(exchange(frame(0x81,i)),i,len(block(source,i))) for i in ids}
            before=read()
            expected=propose(source,pid,before)
            record.update(before={i:v.hex(' ') for i,v in before.items()},
                          expected={i:v.hex(' ') for i,v in expected.items()})
            changes=[]
            for name,i,offset,width,signed,factor,unit in backup.FIELDS:
                if i not in before:
                    continue
                a=int.from_bytes(before[i][offset:offset+width],'big',signed=signed)
                b=int.from_bytes(expected[i][offset:offset+width],'big',signed=signed)
                if a!=b:
                    changes.append(dict(name=name,id=i,offset=offset,current=str(Decimal(a)*Decimal(factor)),
                                        target=str(Decimal(b)*Decimal(factor)),unit=unit))
            if pid in (4,6,8):
                record['schedule_before']=schedule_rows(before[pid],before[pid+1],pid)
                record['schedule_target']=schedule_rows(expected[pid],expected[pid+1],pid)
                print(json.dumps(record['schedule_target'],ensure_ascii=False,indent=2))
            if pid in (17,43):
                record['routing_changes']=[dict(offset=j,current=a,target=b) for j,(a,b) in enumerate(zip(before[pid],expected[pid])) if a!=b]
                print(json.dumps(record['routing_changes'],indent=2))
            record['changes']=changes
            record['status']='preview'
            save()
            for change in changes:
                print("{name}: {current} -> {target} {unit}".format(**change))
            print('ID',pid,'before:',before[pid].hex(' '),'target:',expected[pid].hex(' '))
            if before==expected:
                record['status']='unchanged'
                return 0
            if not execute:
                return 0
            if pid == 95:
                if input('GSM modem disconnected. Type GSM: ')!='GSM':
                    record['status']='cancelled'
                    return 1
            if pid == 17:
                raise ValueError('Routing writes blocked pending full dependency mapping')
            if input('Isolated bench, no connected loads. Type BENCH: ')!='BENCH':
                record['status']='cancelled'
                return 1
            if read()!=before:
                raise ValueError('Blocks changed since preview')
            record['status']='write_outcome_unknown'
            save()
            intermediate=dict(before)
            for i in ((pid,pid+1) if pid in (4,6,8) else (pid,)):
                if intermediate[i]==expected[i]:
                    continue
                ack=exchange(frame(0x82,i,expected[i]))
                time.sleep(1)
                decode(ack,i,0)
                intermediate[i]=expected[i]
                after=read()
                record['after']={k:v.hex(' ') for k,v in after.items()}
                save()
                if pid in (4,6,8) and after!=intermediate and not (i==pid+1 and schedule_equal(after,intermediate,pid) and all(after[j]==intermediate[j] for j in ids if j not in (pid,pid+1))):
                    raise ValueError('Unexpected intermediate schedule readback; stop without retry')
            after=read()
            record['after']={i:v.hex(' ') for i,v in after.items()}
            save()
            if after!=expected:
                if pid not in (4,6,8) or not schedule_equal(after,expected,pid) or any(after[i]!=expected[i] for i in ids if i not in (pid,pid+1)):
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
    p.add_argument('--block',type=int,choices=(4,6,8,12,13,14,16,17,43,44,47,65,66,95))
    p.add_argument('--all',action='store_true')
    p.add_argument('--port',default='/dev/ttyUSB0')
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--current',type=Path)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(argv)
    try:
        if args.output.exists():
            raise FileExistsError('Output exists')
        if not args.dry_run:
            if (args.block is None) == (not args.all) or args.current is not None:
                raise ValueError('Live mode requires exactly one of --block or --all, and no --current')
            source=backup.load(args.source)
            if args.all:
                ids=(65,66,12,13,14,16,43,44,47,4,6,8)
                paths=[args.output.with_name(args.output.stem+'_id'+str(i)+'.json') for i in ids]
                if any(p.exists() for p in paths):
                    raise FileExistsError('Batch log already exists')
                for i,path in zip(ids,paths):
                    result=live(source,i,path,args.port,args.execute_bench)
                    if result:
                        return result
                return 0
            return live(source,args.block,args.output,args.port,args.execute_bench)
        if args.current is None or args.block is not None or args.all:
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
