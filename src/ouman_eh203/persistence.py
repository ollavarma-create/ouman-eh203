"""Offline post-reboot verification; never opens a serial port."""
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from .restore import plan, block_identity, build, IDS
from .validation import block
from .protocol import write_frame, decode
from .schedules import equivalent_readback

def verify(source, journal, reboot, *, power_cycle_confirmed=False):
    if not power_cycle_confirmed:
        raise ValueError('Manual power cycle confirmation required')
    if journal.get('schema') != 'ouman.eh203.restore-journal.v1' or journal.get('status') != 'complete' or journal.get('verification') != 'readback_only':
        raise ValueError('Completed readback journal required')
    if journal['source_sha256'] != source['records_sha256']:
        raise ValueError('Journal/source mismatch')
    if journal['target_identity'] != block_identity(reboot).hex():
        raise ValueError('Journal/target mismatch')
    if plan(source, reboot, allow_device_mismatch=True):
        raise ValueError('Post-reboot settings differ')
    entries = journal['entries']
    if not entries:
        raise ValueError('No recorded restore writes')
    previous = None
    def state(raw):
        if set(raw) != {str(i) for i in IDS}:
            raise ValueError('Incomplete journal state')
        result = {int(k): bytes.fromhex(v) for k,v in raw.items()}
        if any(len(v)!=len(block(source,k)) for k,v in result.items()):
            raise ValueError('Invalid journal block length')
        return result
    for index,e in enumerate(entries):
        pid=e['id']
        before,expected,observed=(state(e[k]) for k in ('before','expected','observed'))
        if e['status']!='verified' or pid not in IDS or (previous is not None and before!=previous):
            raise ValueError('Invalid journal chain')
        if bytes.fromhex(e['tx'])!=write_frame(pid,expected[pid]):
            raise ValueError('Invalid journal write')
        decode(bytes.fromhex(e['rx']),pid,0)
        if pid==65 and before[65][0]==1 and expected[65][0]==0:
            samples=e['mode_samples']
            if not samples or state(samples[-1]['blocks'])!=observed:
                raise ValueError('Invalid mode samples')
            for sample in samples:
                actual=state(sample['blocks'])
                allowed=dict(expected)
                for j in (65,66):
                    b=bytearray(allowed[j])
                    for k in (2,4):
                        if not b[k-1]>=actual[j][k]>=b[k+1]:
                            raise ValueError('Invalid interpolation')
                        b[k]=actual[j][k]
                    allowed[j]=bytes(b)
                if actual!=allowed:
                    raise ValueError('Unexpected mode sample')
            if [x['id'] for x in entries[index+1:index+3]]!=[65,66]:
                raise ValueError('Missing explicit curve writes')
        elif observed!=expected and not (pid==7 and equivalent_readback(observed,expected)):
            raise ValueError('Unexpected journal readback')
        previous=observed
    if build(source,previous):
        raise ValueError('Journal final state differs from source')
    if not equivalent_readback({i:block(reboot,i) for i in IDS},previous):
        raise ValueError('Post-reboot monitored state differs from journal')
    return dict(schema='ouman.eh203.persistence.v1',persistence_verified=True,
                power_cycle_user_confirmed=True,source_sha256=source['records_sha256'],
                reboot_sha256=reboot['records_sha256'],target_identity=journal['target_identity'],
                verified_writes=len(entries),planned_writes=0,
                verified_at=datetime.now(timezone.utc).isoformat())

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','journal','reboot','output'):
        p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--confirm-power-cycle',action='store_true')
    a=p.parse_args(argv)
    try:
        raw=[f.read_bytes() for f in (a.source,a.journal,a.reboot)]
        report=verify(*(json.loads(x) for x in raw),power_cycle_confirmed=a.confirm_power_cycle)
        report['journal_file_sha256']=hashlib.sha256(raw[1]).hexdigest()
        with a.output.open('x') as f:
            json.dump(report,f,indent=2)
            f.write('\n')
        print('Persistence verified; report:',a.output)
        return 0
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print('STOP:',exc)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
