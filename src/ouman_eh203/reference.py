"""Read-only reference derived from the verified bench factory fixture."""
from .defaults import compare_defaults
from .metadata import get_metadata

REFERENCE_SHA256 = 'f76181a776e6b0b028a9267880a4ff65e0cc542de4c239a89e85eae8cdc4bebf'

def factory_reference(snapshot):
    """Only the recorded EH-203 2.15 bench capture is an approved reference."""
    if snapshot.get('records_sha256') != REFERENCE_SHA256:
        raise ValueError('Not the registered bench factory reference')
    report = compare_defaults(snapshot, factory_reset_confirmed=True)
    fields = {}
    for key, row in report['fields'].items():
        meta = get_metadata(key)
        meta.update(observed_factory_default=row['observed_value'],
                    observed_firmware=report['firmware'],
                    source_records_sha256=REFERENCE_SHA256,
                    default_comparison=row['status'],
                    observed_unit=row['unit'])
        fields[key] = meta
    return dict(schema='ouman.eh203.factory-reference.v1',
                firmware=report['firmware'], source_records_sha256=REFERENCE_SHA256,
                scope='single bench controller after user-confirmed manual factory reset',
                read_only=True, fields=fields)
