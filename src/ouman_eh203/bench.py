"""Experimental isolated EH-203 bench restore CLI."""
import argparse
import json
from pathlib import Path
from .restore import plan, execute_bench, compatibility, block_identity

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True,type=Path)
    p.add_argument('--current',required=True,type=Path)
    p.add_argument('--port',default='/dev/ttyUSB0')
    p.add_argument('--execute-bench',action='store_true')
    p.add_argument('--journal',type=Path)
    p.add_argument('--allow-device-mismatch',action='store_true')
    p.add_argument('--allow-firmware-mismatch',action='store_true')
    a=p.parse_args(argv)
    try:
        source,current=[json.loads(f.read_text()) for f in (a.source,a.current)]
        opts=dict(allow_device_mismatch=a.allow_device_mismatch,allow_firmware_mismatch=a.allow_firmware_mismatch)
        steps=plan(source,current,**opts)
        print(json.dumps(compatibility(block_identity(source),block_identity(current)),indent=2))
        for pid,b,e in steps:
            print('ID',pid,b[pid].hex(' '),'->',e[pid].hex(' '))
        print('Planned writes:',len(steps))
        if not a.execute_bench:
            return 0
        if a.journal is None or a.journal.exists():
            raise ValueError('New journal path required')
        print('WARNING: isolated test controller only; disconnect all controlled loads.')
        if a.allow_device_mismatch and input('Confirm replacement controller: type REPLACE: ')!='REPLACE':
            return 1
        confirmation=input('Type BENCH to execute displayed plan: ')
        execute_bench(a.port,source,current,[],journal_path=a.journal,confirmation=confirmation,**opts)
        print('Readback verified; final reboot verification still required.')
        return 0
    except (ValueError,OSError,KeyError,KeyboardInterrupt) as exc:
        print('STOP:',exc)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
