#!/usr/bin/env python3
"""Offline EH-203 restore planning. No serial access or write execution."""
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

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dry-run',action='store_true',required=True)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--current',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(argv)
    try:
        if args.output.exists():
            raise FileExistsError('Output exists')
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
