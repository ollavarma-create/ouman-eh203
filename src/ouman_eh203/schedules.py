"""Read-only schedule decoding. Preserve ordering, including conflicting events."""
def decode_pair(times, events, pair):
    if len(times)!=31 or len(events)!=31 or pair not in (4,6,8):
        raise ValueError('Invalid schedule block')
    allowed = {0,0x13,0x23,0x14,0x24} if pair==8 else {0,0x10,0x20,0x11,0x21,0x12,0x22}
    rows=[]
    for i in range(14):
        minute=int.from_bytes(times[1+2*i:3+2*i],'big')
        mask,kind=events[i],events[14+i]
        if minute>=1440 or mask>127 or kind not in allowed or (mask and not kind):
            raise ValueError('Invalid schedule slot')
        if minute or mask or kind:
            rows.append((minute,mask,kind))
    return rows

def semantic_key(blocks):
    # Compare per circuit, preserving relative order within each circuit.
    rows=decode_pair(blocks[4],blocks[5],4)+decode_pair(blocks[6],blocks[7],6)+decode_pair(blocks[8],blocks[9],8)
    return tuple(tuple(r for r in rows if r[2]&15==c) for c in range(5))

def equivalent_readback(actual, expected):
    if actual.keys()!=expected.keys():
        return False
    for pid in actual:
        a,b=actual[pid],expected[pid]
        if pid in (4,6):
            if a[:1]!=b[:1] or a[29:]!=b[29:]:
                return False
        elif pid in (5,7):
            if a[28:]!=b[28:]:
                return False
        elif a!=b:
            return False
    return semantic_key(actual)==semantic_key(expected)

def relocate_shared(blocks):
    """Model observed grouping by circuit, preserving within-circuit order."""
    rows=decode_pair(blocks[4],blocks[5],4)+decode_pair(blocks[6],blocks[7],6)
    rows=sorted(rows,key=lambda r: {1:0,2:1,0:2}.get(r[2]&15,3))
    result=dict(blocks)
    for pair,subset in ((4,rows[:14]),(6,rows[14:])):
        times=bytearray(blocks[pair]); events=bytearray(blocks[pair+1])
        times[1:29]=bytes(28); events[:28]=bytes(28)
        for i,(minute,mask,kind) in enumerate(subset):
            times[1+2*i:3+2*i]=minute.to_bytes(2,'big')
            events[i]=mask; events[14+i]=kind
        result[pair]=bytes(times); result[pair+1]=bytes(events)
    return result
