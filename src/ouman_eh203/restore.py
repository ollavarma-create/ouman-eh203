"""Simulation-only restore. No physical transport accepted."""
from .backup import verify_file, known_fields, atomic_json
from pathlib import Path
import json
import os
from .protocol import request, write_frame, decode
from .transport import exchange
from .simulator import SimulatedSerial
from .validation import propose, block
from .schedules import semantic_key

IDS=(4,5,6,7,8,9,12,13,14,16,17,43,44,47,65,66)
ORDER=(65,66,12,13,16,43,44,14,47,4,6,8)

def compatibility(source_identity, target_identity):
    if len(source_identity)!=9 or len(target_identity)!=9:
        raise ValueError('Incomplete identity')
    if source_identity[4:7]!=b'203' or target_identity[4:7]!=b'203':
        raise ValueError('Unsupported model')
    return dict(device_mismatch=source_identity[:4]!=target_identity[:4],
                firmware_mismatch=source_identity[8]!=target_identity[8],
                source_firmware=source_identity[8],target_firmware=target_identity[8],
                compatible=(source_identity[8],target_identity[8])==(215,215))

def authorize(source_identity,target_identity,allow_device_mismatch=False,allow_firmware_mismatch=False):
    report=compatibility(source_identity,target_identity)
    if report['device_mismatch'] and not allow_device_mismatch:
        raise ValueError('Different controller: explicit device confirmation required')
    if report['firmware_mismatch'] and not allow_firmware_mismatch:
        raise ValueError('Different firmware: explicit firmware confirmation required')
    if not report['compatible']:
        raise ValueError('No validated firmware migration profile')
    return report

def plan(source,current,*,allow_device_mismatch=False,allow_firmware_mismatch=False):
    for snap in (source,current):
        verify_file(snap)
        if set(snap['records'])!={str(i) for i in range(256)}:
            raise ValueError('Full backup required')
    authorize(block_identity(source),block_identity(current),allow_device_mismatch,allow_firmware_mismatch)
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

def execute_simulated(sim,source,steps,log,*,target_identity=None,allow_device_mismatch=False,allow_firmware_mismatch=False,journal_path=None):
    if type(sim) is not SimulatedSerial:
        raise TypeError('Simulation only')
    verify_file(source)
    def read():
        return {i:decode(exchange(sim,request(i)),i,len(block(source,i))) for i in IDS}
    actual=decode(exchange(sim,request(1)),1,len(sim.blocks[1]))[:9]
    if actual!=(target_identity if target_identity is not None else block_identity(source)):
        raise ValueError('Target differs from approved identity')
    authorize(block_identity(source),actual,allow_device_mismatch,allow_firmware_mismatch)
    if steps!=build(source,read()):
        raise ValueError('Stale or modified plan')
    journal=None
    if journal_path is not None:
        journal_path=Path(journal_path)
        journal=dict(schema='ouman.eh203.restore-journal.v1',source_sha256=source['records_sha256'],
                     target_identity=actual.hex(),status='running',entries=[])
        with journal_path.open('x') as f:
            json.dump(journal,f)
            f.flush()
            os.fsync(f.fileno())
        atomic_json(journal_path,journal)
    def save():
        if journal is not None:
            atomic_json(journal_path,journal)
    for pid,before,expected in steps:
        if decode(exchange(sim,request(1)),1,len(sim.blocks[1]))[:9]!=actual:
            raise ValueError('Target identity changed')
        if read()!=before:
            raise ValueError('Stale plan')
        entry={'id':pid,'status':'write_outcome_unknown','tx':write_frame(pid,expected[pid]).hex()}
        log.append(entry)
        if journal is not None:
            journal['entries'].append(entry)
            entry['before']={str(k):v.hex() for k,v in before.items()}
            entry['expected']={str(k):v.hex() for k,v in expected.items()}
        save()
        rx=exchange(sim,bytes.fromhex(entry['tx']))
        entry['rx']=rx.hex()
        save()
        decode(rx,pid,0)
        if read()!=expected:
            raise ValueError('Unexpected readback')
        entry['status']='verified'
        save()
    result=read()
    if journal is not None:
        journal['status']='complete'
        save()
    return result

def recovery_preview(sim,source,journal_path,*,allow_device_mismatch=False,allow_firmware_mismatch=False):
    """Read actual state, never replay a logged command. No writes."""
    if type(sim) is not SimulatedSerial:
        raise TypeError('Simulation only')
    verify_file(source)
    journal=json.loads(Path(journal_path).read_text())
    if journal.get('schema')!='ouman.eh203.restore-journal.v1' or journal.get('source_sha256')!=source['records_sha256']:
        raise ValueError('Journal/source mismatch')
    actual=decode(exchange(sim,request(1)),1,len(sim.blocks[1]))[:9]
    if actual.hex()!=journal['target_identity']:
        raise ValueError('Recovery target mismatch')
    authorize(block_identity(source),actual,allow_device_mismatch,allow_firmware_mismatch)
    state={i:decode(exchange(sim,request(i)),i,len(block(source,i))) for i in IDS}
    # A partial schedule may be unsupported; fail closed rather than replay.
    return build(source,state)

