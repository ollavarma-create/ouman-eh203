"""Validated restore engine with explicit isolated bench entry point."""
from .backup import verify_file, known_fields, atomic_json
from pathlib import Path
import json
import os
from .protocol import request, write_frame, decode
from .transport import exchange
from .simulator import SimulatedSerial
from .validation import propose, block
from .schedules import semantic_key, equivalent_readback

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

def build(source,before,*,persist_curves=False):
    state=dict(before)
    steps=[]
    def add(pid,expected,force=False):
        nonlocal state
        if expected!=state or force:
            steps.append((pid,dict(state),dict(expected)))
            state=dict(expected)
    if state[65][0]==state[66][0]==1 and block(source,65)[0]==block(source,66)[0]==0:
        expected=dict(state)
        for i in (65,66):
            expected[i]=bytes(1)+state[i][1:]
        add(65,expected)
        persist_curves=True
    for pid in ORDER:
        expected=propose(source,pid,state)
        if pid in (4,6,8):
            intermediate=dict(state)
            intermediate[pid]=expected[pid]
            add(pid,intermediate)
            add(pid+1,expected)
        else:
            add(pid,expected,force=persist_curves and pid in (65,66))
    desired={i:block(source,i) for i in IDS}
    for name,i,offset,width,*_ in __import__('ouman_eh203.registry',fromlist=['FIELDS']).FIELDS:
        if state[i][offset:offset+width]!=desired[i][offset:offset+width]:
            raise ValueError('Unrestored known field: '+name)
    if semantic_key(state)!=semantic_key(desired) or state[43]!=desired[43] or state[17][17]!=desired[17][17]:
        raise ValueError('Unrestored schedule or digital dependency')
    return steps

def _execute(sim,source,steps,log,*,target_identity=None,allow_device_mismatch=False,allow_firmware_mismatch=False,journal_path=None,settle=lambda:None):
    verify_file(source)
    def read():
        return {i:decode(exchange(sim,request(i)),i,len(block(source,i))) for i in IDS}
    actual=decode(exchange(sim,request(1)),1,len(bytes.fromhex(source['records']['1']['data'])))[:9]
    if actual!=(target_identity if target_identity is not None else block_identity(source)):
        raise ValueError('Target differs from approved identity')
    authorize(block_identity(source),actual,allow_device_mismatch,allow_firmware_mismatch)
    if steps!=build(source,read()):
        raise ValueError('Stale or modified plan')
    journal=None
    if journal_path is not None:
        journal_path=Path(journal_path)
        journal=dict(schema='ouman.eh203.restore-journal.v1',source_sha256=source['records_sha256'],
                     target_identity=actual.hex(),status='running',persistence_verified=False,entries=[])
        with journal_path.open('x') as f:
            json.dump(journal,f)
            f.flush()
            os.fsync(f.fileno())
        atomic_json(journal_path,journal)
    def save():
        if journal is not None:
            atomic_json(journal_path,journal)
    steps=[(p,dict(b),dict(e)) for p,b,e in steps]
    for index,(pid,before,expected) in enumerate(steps):
        if decode(exchange(sim,request(1)),1,len(bytes.fromhex(source['records']['1']['data'])))[:9]!=actual:
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
        settle()
        observed=read()
        entry['observed']={str(k):v.hex() for k,v in observed.items()}
        save()
        if pid==65 and before[65][0]==1 and expected[65][0]==0:
            # Only observed intermediate Y coordinates may change during mode conversion.
            allowed=dict(expected)
            for j in (65,66):
                b=bytearray(allowed[j])
                for k in (2,4):
                    if not b[k-1]>=observed[j][k]>=b[k+1]:
                        raise ValueError('Invalid interpolated curve')
                    b[k]=observed[j][k]
                allowed[j]=bytes(b)
            if observed!=allowed:
                raise ValueError('Unexpected mode transition')
            remaining=build(source,observed,persist_curves=True)
            if any(p not in {q for q,_,_ in steps[index+1:]} for p,_,_ in remaining):
                raise ValueError('Mode transition requires new write authorization')
            entry['replanned_ids']=[p for p,_,_ in remaining]
            steps[index+1:]=remaining
        elif observed!=expected:
            # Only accept a completed shared schedule pair, with no pending shared writes.
            if pid!=7 or any(p in (4,5,6,7) for p,_,_ in steps[index+1:]) or not equivalent_readback(observed,expected):
                raise ValueError('Unexpected readback')
            # Rebase remaining steps on the observed physical layout.
            for _,b,e in steps[index+1:]:
                for j in (4,5,6,7):
                    b[j]=e[j]=observed[j]
        entry['observed']={str(k):v.hex() for k,v in observed.items()}
        entry['status']='verified'
        save()
    result=read()
    if build(source,result):
        raise ValueError('Final state still requires restore')
    if journal is not None:
        journal['status']='complete'
        journal['verification']='readback_only'
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
    actual=decode(exchange(sim,request(1)),1,len(bytes.fromhex(source['records']['1']['data'])))[:9]
    if actual.hex()!=journal['target_identity']:
        raise ValueError('Recovery target mismatch')
    authorize(block_identity(source),actual,allow_device_mismatch,allow_firmware_mismatch)
    state={i:decode(exchange(sim,request(i)),i,len(block(source,i))) for i in IDS}
    # A partial schedule may be unsupported; fail closed rather than replay.
    return build(source,state)


def execute_simulated(sim,source,steps,log,**kwargs):
    if type(sim) is not SimulatedSerial:
        raise TypeError('Simulation only')
    return _execute(sim,source,steps,log,**kwargs)

def execute_bench(port,source,current,log,*,journal_path,confirmation,allow_device_mismatch=False,allow_firmware_mismatch=False):
    """Experimental physical restore, isolated controller only."""
    from .transport import open_serial
    import time
    if confirmation!='BENCH' or journal_path is None:
        raise ValueError('Isolated bench confirmation and journal required')
    steps=plan(source,current,allow_device_mismatch=allow_device_mismatch,
               allow_firmware_mismatch=allow_firmware_mismatch)
    with open_serial(port) as ser:
        return _execute(ser,source,steps,log,target_identity=block_identity(current),
                        allow_device_mismatch=allow_device_mismatch,
                        allow_firmware_mismatch=allow_firmware_mismatch,
                        journal_path=journal_path,settle=lambda:time.sleep(5))
