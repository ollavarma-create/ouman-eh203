"""Two-write curve timing experiment on isolated EH-203 firmware 2.15."""
import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from .protocol import request, write_frame, decode
from .transport import open_serial, exchange
from .backup import verify_file

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port',default='/dev/ttyUSB0')
    p.add_argument('--source',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args()
    source=json.loads(a.source.read_text())
    verify_file(source)
    if set(source['records'])!={str(i) for i in range(256)}:
        raise ValueError('Full source required')
    def block(i):
        return bytes.fromhex(source['records'][str(i)]['data'])
    target=block(65)
    if len(target)!=31 or target[0]!=0:
        raise ValueError('Expected five-point source')
    if input('Isolated controller, loads disconnected, factory reset completed? Type BENCH: ')!='BENCH':
        return
    with a.output.open('x') as f, open_serial(a.port) as ser:
        start=time.monotonic()
        def record(**fields):
            row=dict(utc=datetime.now(timezone.utc).isoformat(),elapsed_s=round(time.monotonic()-start,3),**fields)
            f.write(json.dumps(row)+'\n')
            f.flush()
            os.fsync(f.fileno())
        def read(i,size):
            tx=request(i)
            rx=exchange(ser,tx)
            record(action='read',id=i,tx=tx.hex(),rx=rx.hex())
            return decode(rx,i,size)
        def snapshot():
            return {i:read(i,31) for i in (65,66,12,14)}
        def write(payload):
            tx=write_frame(65,payload)
            record(action='write_intent',id=65,tx=tx.hex())
            rx=exchange(ser,tx)
            record(action='ack',id=65,rx=rx.hex())
            decode(rx,65,0)
        def observe():
            t=time.monotonic()
            previous=None
            while True:
                state=snapshot()
                if state!=previous:
                    print(round(time.monotonic()-t,2),{i:v[:9].hex(' ') for i,v in state.items()},flush=True)
                previous=state
                if time.monotonic()-t>=60:
                    return state
                time.sleep(1)
        if read(1,len(block(1)))[:9]!=block(1)[:9]:
            raise ValueError('Identity mismatch')
        before=snapshot()
        if before[65][0]!=1 or before[66][0]!=1:
            raise ValueError('Expected three-point factory state')
        write(bytes(1)+before[65][1:])
        settled=observe()
        if settled[65][0]!=0 or settled[66][0]!=0:
            raise ValueError('Mode transition failed')
        if any(settled[i][9:]!=before[i][9:] for i in (65,66)) or any(settled[i][3:]!=before[i][3:] for i in (12,14)):
            raise ValueError('Unexpected non-curve change; stopping')
        if read(1,len(block(1)))[:9]!=block(1)[:9] or snapshot()!=settled:
            raise ValueError('State changed before second write')
        write(settled[65][:1]+target[1:9]+settled[65][9:])
        final=observe()
        record(action='finished',l1_matches=final[65][1:9]==target[1:9])
        print('Finished; inspect log before further writes.')

if __name__=='__main__':
    main()
