"""Simulation-only restore. No physical transport accepted."""
from .backup import verify_file, known_fields
from .protocol import request, write_frame, decode
from .transport import exchange
from .simulator import SimulatedSerial
from .validation import propose, block
from .schedules import semantic_key

IDS=(4,5,6,7,8,9,12,13,14,16,17,43,44,47,65,66)
ORDER=(65,66,12,13,16,43,44,14,47,4,6,8)

def plan(source,current):
    for snap in (source,current):
        verify_file(snap)
        if set(snap['records'])!={str(i) for i in range(256)}:
            raise ValueError('Full backup required')
    if block_identity(source)!=block_identity(current):
        raise ValueError('Identity mismatch')
    return build(source,{i:block(current,i) for i in IDS})

def block_identity(s):
    return bytes.fromhex(s['records']['1']['data'])[:9]

def build(source,before):
    state=dict(before)
    steps=[]
    def add(pid,expected):
        nonlocal state
        if expected!=state:
            steps.append((pid,dict(state),dict(expected)))
            state=dict(expected)
    if state[65][0]==state[66][0]==1 and block(source,65)[0]==block(source,66)[0]==0:
        expected=dict(state)
        for i in (65,66):
            expected[i]=bytes(1)+state[i][1:]
        add(65,expected)
    for pid in ORDER:
        expected=propose(source,pid,state)
        if pid in (4,6,8):
            intermediate=dict(state)
            intermediate[pid]=expected[pid]
            add(pid,intermediate)
            add(pid+1,expected)
        else:
            add(pid,expected)
    desired={i:block(source,i) for i in IDS}
    for name,i,offset,width,*_ in __import__('ouman_eh203.registry',fromlist=['FIELDS']).FIELDS:
        if state[i][offset:offset+width]!=desired[i][offset:offset+width]:
            raise ValueError('Unrestored known field: '+name)
    if semantic_key(state)!=semantic_key(desired) or state[43]!=desired[43] or state[17][17]!=desired[17][17]:
        raise ValueError('Unrestored schedule or digital dependency')
    return steps

def execute_simulated(sim,source,steps,log):
    if type(sim) is not SimulatedSerial:
        raise TypeError('Simulation only')
    verify_file(source)
    def read():
        return {i:decode(exchange(sim,request(i)),i,len(block(source,i))) for i in IDS}
    if decode(exchange(sim,request(1)),1,len(sim.blocks[1]))[:9]!=block_identity(source):
        raise ValueError('Identity mismatch')
    if steps!=build(source,read()):
        raise ValueError('Stale or modified plan')
    for pid,before,expected in steps:
        if read()!=before:
            raise ValueError('Stale plan')
        entry={'id':pid,'status':'write_outcome_unknown','tx':write_frame(pid,expected[pid]).hex()}
        log.append(entry)
        rx=exchange(sim,bytes.fromhex(entry['tx']))
        entry['rx']=rx.hex()
        decode(rx,pid,0)
        if read()!=expected:
            raise ValueError('Unexpected readback')
        entry['status']='verified'
    return read()
