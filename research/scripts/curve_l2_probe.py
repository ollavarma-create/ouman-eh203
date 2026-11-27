#!/usr/bin/env python3
"""Bench-only L2 coordinate restore experiment; default is offline preview, no writes."""
import argparse
import json
from pathlib import Path
import backup
from write_parameter import frame, decode

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--current',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--port',default='/dev/ttyUSB0')
    p.add_argument('--execute-bench',action='store_true')
    a=p.parse_args()
    try:
        from restore import plan
        s,c=backup.load(a.source),backup.load(a.current)
        plan(s,c)
        def block(s,i):
            return bytes.fromhex(s['records'][str(i)]['data'])
        ids=(65,66,12,14)
        old={i:block(c,i) for i in ids}
        if any(len(v)!=31 for v in old.values()):
            raise ValueError('Unexpected block size')
        if any(old[i][0]!=0 or block(s,i)[0]!=0 for i in (65,66)):
            raise ValueError('Require both curves in five-point mode')
        target=block(s,66)
        if len(target)!=31:
            raise ValueError('Unexpected source size')
        ys=list(target[1:6])
        xs=[-20]+[int.from_bytes(target[j:j+1],'big',signed=True) for j in (6,7,8)]+[20]
        if not all(x<y for x,y in zip(xs,xs[1:])) or not all(x>=y for x,y in zip(ys,ys[1:])) or not all(15<=y<=70 for y in ys):
            raise ValueError('Curve outside conservative bench bounds')
        if old[14][:3]!=bytes(old[66][j] for j in (1,3,5)):
            raise ValueError('Unexpected initial mirror')
        proposed=old[66][:1]+target[1:9]+old[66][9:]
        if proposed==old[66]:
            raise ValueError('Already restored')
        record=dict(status='preview',source_sha256=s['records_sha256'],current_sha256=c['records_sha256'],
                    before={i:v.hex(' ') for i,v in old.items()},proposed=proposed.hex(' '),frames=[])
        with a.output.open('x') as f:
            json.dump(record,f)
        def save():
            backup.atomic_json(a.output,record)
        if not a.execute_bench:
            print('Offline preview only:',a.output)
            return 0
        if input('Isolated bench controller, no connected loads. Type BENCH to attempt ID66 coordinate write: ')!='BENCH':
            return 1
        import serial
        import time
        with serial.Serial(a.port,4800,timeout=1.5,write_timeout=1.5,exclusive=True,
                           rtscts=False,dsrdtr=False,xonxoff=False) as ser:
            def exchange(tx):
                e={'tx':tx.hex(' ')}
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
            if decode(ident,1,len(ident)-6)[:9]!=block(c,1)[:9]:
                raise ValueError('Controller mismatch')
            for i in ids:
                if decode(exchange(frame(0x81,i)),i,31)!=old[i]:
                    raise ValueError('Current block differs from snapshot; capture again')
            record['status']='write_outcome_unknown'
            save()
            ack=exchange(frame(0x82,66,proposed))
            time.sleep(1)
            after={i:decode(exchange(frame(0x81,i)),i,31) for i in ids}
            record['after']={i:v.hex(' ') for i,v in after.items()}
            record['changed_offsets']={i:[j for j in range(31) if old[i][j]!=after[i][j]] for i in ids}
            save()
            decode(ack,66,0)
            expected_mirror=bytes(proposed[j] for j in (1,3,5))+old[14][3:]
            if after[66]!=proposed or after[14]!=expected_mirror or any(after[i]!=old[i] for i in (65,12)):
                raise ValueError('Unexpected readback or mirror; stop without retry')
            record['status']='verified_pending_reboot'
            save()
            print('Observation saved; inspect LCD and log. No further writes.')
        return 0
    except (Exception,KeyboardInterrupt) as e:
        print('STOP:',e)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
