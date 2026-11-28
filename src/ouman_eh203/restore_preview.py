"""Offline assessment only; never authorizes or executes writes."""
from .backup import verify_file, known_fields
from .restore import compatibility, block_identity, plan
from .restore import IDS
from .validation import block

def preview(source, target):
    for snap in (source, target):
        verify_file(snap, structural_only=True)
    report = compatibility(block_identity(source), block_identity(target))
    report.update(steps=[], fields=[], excluded_ids=[], source_hash=source['records_sha256'],
                  target_hash=target['records_sha256'])
    if not report['compatible']:
        report['status'] = 'unvalidated_firmware'
        report['excluded_ids'] = list(range(256))
        return report
    desired = known_fields(source)['fields']
    current = known_fields(target)['fields']
    report['fields'] = [(key, current[key]['value'], desired[key]['value'], desired[key]['unit'])
                        for key in sorted(desired)]
    report['excluded_ids'] = sorted(set(range(256))-set(IDS))
    if all(block(source,i)==block(target,i) for i in IDS):
        report['status'] = 'no_changes'
        return report
    try:
        steps = plan(source, target, allow_device_mismatch=True)
    except ValueError as exc:
        report['status'] = 'blocked'
        report['reason'] = str(exc)
        return report
    report['steps'] = [pid for pid, _, _ in steps]
    report['status'] = 'preview_only'
    return report
