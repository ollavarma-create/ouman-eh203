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
