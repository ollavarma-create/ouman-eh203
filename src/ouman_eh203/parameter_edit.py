"""Simulator scenario edits, not physical write authorization."""
from decimal import Decimal
from .registry import FIELDS
from .metadata import PARAMETERS
from .validation import BOUNDS
from .simulator import SimulatedSerial
from .backup import acquire, verify_file, atomic_json, exchange, utc

KEYS = tuple(k for k,*_ in FIELDS if k in ('l1_room_setpoint','dhw_setpoint','dhw_boost') or
             k.split('_',1)[0] in ('l1','l2','dhw') and k.split('_',1)[1] in
             ('supply_min','supply_max','parallel_shift','night_reduction','p_band','i_time','d_time'))
MAP = {f[0]:f[1:] for f in FIELDS if f[0] in KEYS}

def current(sim,key):
    if type(sim) is not SimulatedSerial:
        raise ValueError('Simulator only')
    pid,offset,width,signed,factor,unit = MAP[key]
    data = sim.blocks[pid]
    if len(data)!=31:
        raise ValueError('Unexpected block size')
    return Decimal(int.from_bytes(data[offset:offset+width],'big',signed=signed))*Decimal(factor)

def proposal(sim,key,value):
    old = current(sim,key)
    pid,offset,width,signed,factor,unit = MAP[key]
    value = Decimal(str(value))
    lo,hi = PARAMETERS[key]['manual_range']
    raw = value/Decimal(factor)
    if not value.is_finite() or not lo<=value<=hi or raw!=raw.to_integral_value():
        raise ValueError('Outside documented range or resolution')
    if key.endswith('supply_min') and value>current(sim,key.replace('supply_min','supply_max')):
        raise ValueError('Supply minimum exceeds maximum')
    if key.endswith('supply_max') and value<current(sim,key.replace('supply_max','supply_min')):
        raise ValueError('Supply maximum below minimum')
    before = sim.blocks[pid]
    after = before[:offset]+int(raw).to_bytes(width,'big',signed=signed)+before[offset+width:]
    return pid,before,after

def apply(sim,key,value,approved,safety_path,journal_path):
    if proposal(sim,key,value)!=approved:
        raise ValueError('Target changed; preview again')
    pid,before,after = approved
    if before==after:
        return False
    snapshot = acquire(sim,safety_path,0,progress=lambda *_:None)
    verify_file(snapshot)
    if proposal(sim,key,value)!=approved:
        raise ValueError('Target changed during capture')
    journal = dict(schema='ouman.eh203.simulator-edit.v1',created_at=utc(),key=key,
                   before=before.hex(),after=after.hex(),id=pid,safety=str(safety_path),status='pending')
    atomic_json(journal_path,journal)
    # Explicit scenario mutation: never emulate unverified physical write transitions.
    sim.blocks[pid]=after
    sim.persistent[pid]=after
    try:
        rec=exchange(sim,pid)
        if rec['status']!='accepted' or bytes.fromhex(rec['data'])!=after:
            raise ValueError('Readback mismatch')
        journal['status']='verified'
    except Exception:
        journal['status']='uncertain'
        raise
    finally:
        atomic_json(journal_path,journal)
    return True
