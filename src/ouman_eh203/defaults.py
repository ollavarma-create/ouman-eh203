"""Offline comparison; a valid backup alone does not prove a factory reset."""
from decimal import Decimal
from .backup import known_fields
from .metadata import get_metadata

def compare_defaults(snapshot, *, factory_reset_confirmed=False):
    if not factory_reset_confirmed:
        raise ValueError('Manual factory reset confirmation required')
    known = known_fields(snapshot)
    if set(snapshot['records']) != {str(i) for i in range(256)}:
        raise ValueError('Full 256-ID capture required')
    rows = {}
    counts = dict(match=0, differs=0, undocumented=0)
    for key, observed in known['fields'].items():
        meta = get_metadata(key)
        default = meta['factory_default']
        value = observed['value']
        status = ('undocumented' if default is None else
                  'match' if Decimal(str(default)) == Decimal(value) else 'differs')
        counts[status] += 1
        rows[key] = dict(documented_default=default, observed_value=value,
                         unit=observed['unit'], status=status,
                         manual_page=meta['manual_page'],
                         documentation_status=meta['documentation_status'],
                         dependencies=meta['dependencies'])
    return dict(schema='ouman.eh203.factory-comparison.v1',
                source_records_sha256=known['source_records_sha256'],
                firmware=known['firmware'], factory_reset_user_confirmed=True,
                read_only=True, counts=counts, fields=rows)
