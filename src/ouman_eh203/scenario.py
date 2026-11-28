"""Portable offline scenarios; never accepted as physical backups."""
from .backup import verify_file, digest, utc
from .simulator import SimulatedSerial

SCHEMA = 'ouman.eh203.scenario.v1'

def encode(source, sim):
    verify_file(source)
    if type(sim) is not SimulatedSerial:
        raise ValueError('Simulator required')
    original = SimulatedSerial.from_snapshot(source).blocks
    if sim.blocks.keys() != original.keys() or any(len(v)!=len(original[k]) for k,v in sim.blocks.items()):
        raise ValueError('Scenario block layout changed')
    if sim.blocks[1] != original[1]:
        raise ValueError('Scenario identity changed')
    payload = dict(source=source, blocks={str(k):v.hex() for k,v in sim.blocks.items()},
                   changed_ids=sorted(k for k in original if original[k]!=sim.blocks[k]))
    return dict(schema=SCHEMA, created_at=utc(), payload=payload, sha256=digest(payload))

def decode(obj):
    if obj.get('schema') != SCHEMA:
        return obj, SimulatedSerial.from_snapshot(obj), False
    payload = obj['payload']
    if digest(payload)!=obj['sha256']:
        raise ValueError('Scenario checksum mismatch')
    source = payload['source']
    sim = SimulatedSerial.from_snapshot(source)
    blocks = {int(k):bytes.fromhex(v) for k,v in payload['blocks'].items()}
    if len(blocks)!=len(payload['blocks']) or blocks.keys()!=sim.blocks.keys():
        raise ValueError('Scenario block IDs changed')
    sim.blocks = blocks
    sim.persistent = dict(blocks)
    if encode(source,sim)['payload'] != payload:
        raise ValueError('Invalid scenario payload')
    return source, sim, True
