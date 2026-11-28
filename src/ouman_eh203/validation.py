from .registry import FIELDS

# Only these bytes may be patched. Other mapped fields remain blocked.
BENCH_FIELDS = {12: ('l1_supply_max','l1_room_gain','l1_supply_min','l1_night_reduction','l1_parallel_shift','l1_autumn_drying','l1_outdoor_delay'),
                13: ('l1_room_setpoint','l1_p_band','l1_i_time','l1_d_time','l1_actuator_time','l2_p_band','l2_i_time','l2_d_time','l2_actuator_time'),
                14: ('l2_supply_min','l2_supply_max','l2_night_reduction','l2_parallel_shift','l2_autumn_drying','l2_outdoor_delay'), 16: ('dhw_setpoint','dhw_p_band','dhw_i_time','dhw_d_time','dhw_feedforward','dhw_fast_drive','dhw_alarm_delay','dhw_deviation_alarm')}
BENCH_FIELDS[44] = ('r1_config','r2_config','r1_outdoor_threshold','r1_temperature_threshold','energy_pulse_factor','district_water_pulse','consumption_water_pulse')
BENCH_FIELDS[47] = ('pressure_range','pressure_upper_alarm','pressure_filling_alarm','pressure_lower_alarm','consumption_alarm_interval')
BOUNDS = {'l1_supply_max': (15, 95), 'l1_room_gain': (0, 100),
          'l1_room_setpoint': (100, 300), 'dhw_setpoint': (500, 650)}

# Experimental bounds, not manufacturer specifications.
for prefix in ('l1','l2'):
    for suffix, bounds in {'supply_min':(0,70),'supply_max':(15,95),
        'night_reduction':(0,40),'parallel_shift':(-20,20),
        'autumn_drying':(0,20),'outdoor_delay':(0,24),
        'p_band':(1,500),'i_time':(0,1000),'d_time':(0,1000),
        'actuator_time':(10,600)}.items():
        BOUNDS[prefix+'_'+suffix]=bounds
BOUNDS.update(dhw_p_band=(1,500),dhw_i_time=(0,1000),dhw_d_time=(0,1000),
              dhw_feedforward=(0,500),dhw_fast_drive=(0,100),
              dhw_alarm_delay=(0,360),dhw_deviation_alarm=(0,50))

BOUNDS.update(district_water_pulse=(0,100),consumption_water_pulse=(0,17),energy_pulse_factor=(0,10),r1_config=(0,8),r2_config=(0,4),
              r1_outdoor_threshold=(-30,30),r1_temperature_threshold=(0,100),
              pressure_range=(1,100),pressure_upper_alarm=(0,100),
              pressure_filling_alarm=(0,100),pressure_lower_alarm=(0,100),
              consumption_alarm_interval=(0,255))
# ID47 is short; use the verified source length, not a 31-byte assumption.
def block(snapshot, pid):
    raw = bytes.fromhex(snapshot['records'][str(pid)]['data'])
    if (pid in (96,98,99)):
        if len(raw)!=(1 if pid==96 else 182):
            raise ValueError('Unexpected GSM block size')
        return raw
    if (pid == 43 and len(raw)!=2) or (pid not in (43,47) and len(raw)!=31) or (pid == 47 and not 7 <= len(raw) <= 31):
        raise ValueError('Unexpected block size')
    return raw

def schedule_rows(times, events, pair):
    if len(times)!=31 or len(events)!=31:
        raise ValueError('Invalid schedule block length')
    allowed=(0x10,0x20,0x11,0x21,0x12,0x22) if pair in (4,6) else (0x13,0x23,0x14,0x24)
    rows=[]
    for i in range(14):
        minute=int.from_bytes(times[1+2*i:3+2*i],'big')
        mask,kind=events[i],events[14+i]
        if minute>=1440 or mask>127 or kind not in (0,*allowed) or (mask and not kind):
            raise ValueError('Unsupported schedule slot')
        if kind or mask or minute:
            rows.append(dict(slot=i+1,time=f'{minute//60:02}:{minute%60:02}',
                days=[d for j,d in enumerate(('Ma','Ti','Ke','To','Pe','La','Su')) if mask & (1<<j)],
                event=f'0x{kind:02X}',mask=mask))
    return rows

def schedule_key(times, events, pair):
    # Preserve duplicates and inactive nonempty slots; ignore slot order only.
    return [(r['time'],r['mask'],r['event']) for r in schedule_rows(times,events,pair)]

def schedule_equal(a,b,pid):
    return (a[pid][:1]==b[pid][:1] and a[pid][29:]==b[pid][29:]
        and a[pid+1][28:]==b[pid+1][28:]
        and schedule_key(a[pid],a[pid+1],pid)==schedule_key(b[pid],b[pid+1],pid))

# Signed parallel shifts are mirrored by firmware 2.15 after a settings write.
SHIFT_MIRRORS = {12: (27, 65), 14: (23, 66)}


def apply_shift_mirror(pid, before, expected):
    """Predict only the physically observed mirror byte; preserve every other byte."""
    if pid not in SHIFT_MIRRORS:
        return
    offset, mirror = SHIFT_MIRRORS[pid]
    old = before[pid][offset]
    new = expected[pid][offset]
    if old == new:
        return
    if before[mirror][9] != old:
        raise ValueError(f'ID {pid}: Initial parallel shift mirror mismatch')
    b = expected[mirror]
    expected[mirror] = b[:9] + bytes([new]) + b[10:]


def propose(source, pid, before):
    target = block(source, pid)
    old = before[pid]
    expected = dict(before)
    if pid in (4,6,8):
        if pid in (4,6):
            desired=dict(before)
            for j in (4,6):
                desired[j]=before[j][:1]+block(source,j)[1:29]+before[j][29:]
                desired[j+1]=block(source,j+1)[:28]+before[j+1][28:]
            def combined(d):
                from .schedules import semantic_key
                return semantic_key(d)
            if combined(before)==combined(desired):
                return dict(before)
            # Do not overwrite a populated shared table piecemeal.
            if any(schedule_key(before[j],before[j+1],j) for j in (4,6)):
                # Allow the previously tested empty second pair continuation only.
                if not (pid==6 and schedule_equal(before,desired,4) and not schedule_key(before[6],before[7],6)):
                    raise ValueError('Shared schedule differs; populated table replacement not validated')
        other=pid+1
        events=block(source,other)
        schedule_rows(target,events,pid)
        schedule_rows(old,before[other],pid)
        expected[pid]=old[:1]+target[1:29]+old[29:]
        expected[other]=events[:28]+before[other][28:]
        if schedule_equal(before,expected,pid):
            return dict(before)
    elif pid == 95:
        raise ValueError('GSM restore blocked')
    elif pid == -1:
        if old[5:]!=target[5:] or target[0]!=1 or not target[1:5].isdigit():
            raise ValueError('Unexpected GSM identity layout')
        if old[:5]!=target[:5] and old[:5]!=b'\x000000':
            raise ValueError('GSM identity transition outside bench proposal')
        expected[pid]=target[:5]+old[5:]
    elif pid == 43:
        codes=(target[1]&15,target[1]>>4,target[0]&15)
        if any(c>6 for c in codes) or codes.count(2)>1:
            raise ValueError('Unsupported digital input assignment')
        expected[pid]=bytes(((old[0]&0xf0)|codes[2],target[1]))
        if expected[pid]!=old:
            if old!=b'\x00\x00' or expected[pid]!=b'\x04\x00' or before[17][17]!=0x63:
                raise ValueError('Digital transition not yet validated')
            mirror=bytearray(before[17])
            mirror[17]=2
            expected[17]=bytes(mirror)
        elif codes[2]==4 and before[17][17]!=2:
            raise ValueError('Unexpected Dig3 energy routing')
    elif pid == 17:
        # Only individually observed routing slots and codes. Never copy unknown bytes.
        modified=bytearray(old)
        for offset in (8,9,11,12,19):
            if old[offset]==target[offset]:
                continue
            allowed={5,12} if offset in (9,19) else {5,11,12} if offset in (8,11) else {11,12}
            if old[offset] not in allowed or target[offset] not in allowed:
                raise ValueError('Unverified routing transition')
            modified[offset]=target[offset]
        if any(modified.count(c)>1 for c in (5,11)):
            raise ValueError('Potential duplicate routing; manual review required')
        expected[pid]=bytes(modified)
    elif pid in (65,66):
        if any(before[i][0] != 0 or block(source,i)[0] != 0 for i in (65,66)):
            raise ValueError('Five-point mode required; use validated mode probe first')
        ys = list(target[1:6])
        xs = [-20]+[int.from_bytes(target[j:j+1],'big',signed=True) for j in (6,7,8)]+[20]
        if not all(a<b for a,b in zip(xs,xs[1:])) or not all(a>=b for a,b in zip(ys,ys[1:])) or not all(15<=y<=70 for y in ys):
            raise ValueError('Curve outside bench bounds')
        mirror = 12 if pid==65 else 14
        if before[mirror][:3] != bytes(old[j] for j in (1,3,5)):
            raise ValueError('Initial mirror mismatch')
        expected[pid] = old[:1]+target[1:9]+old[9:]
        expected[mirror] = bytes(target[j] for j in (1,3,5))+before[mirror][3:]
    else:
        modified = bytearray(old)
        for name, i, offset, width, signed, factor, unit in FIELDS:
            if i != pid or name not in BENCH_FIELDS[pid]:
                continue
            value = int.from_bytes(target[offset:offset+width],'big',signed=signed)
            low, high = BOUNDS[name]
            if not low <= value <= high:
                raise ValueError('Outside conservative bench bounds: '+name)
            modified[offset:offset+width] = target[offset:offset+width]
        if pid in (12,14) and modified[3]>modified[4]:
            raise ValueError('Supply min exceeds max')
        if pid == 44:
            for offset, target_value in ((4,100),(18,17)):
                if modified[offset]!=old[offset] and (before[43]!=b'\x04\x00' or before[17][17]!=2 or old[offset]!=0 or modified[offset]!=target_value):
                    raise ValueError('Water pulse transition outside bench proposal')
            if modified[2]!=old[2] and (before[43]!=b'\x04\x00' or before[17][17]!=2 or old[2]!=0 or modified[2]!=10):
                raise ValueError('Energy pulse transition outside tested bench proposal')
            pair = tuple(modified[9:11])
            if pair[0] not in (0,1,4) or pair[1] not in (0,1,4,6,7,8) or ((pair[0]==4)!=(pair[1]==4)):
                raise ValueError('Unsupported coupled relay configuration')
            if pair[1]==8 and old[10]!=8:
                raise ValueError('Burner mode requires separate dependency validation')
        if pid == 47 and not modified[3] <= modified[2] <= modified[1] <= modified[0]:
            raise ValueError('Pressure limits out of order')
        if pid == 16:
            for offset, initial, final in ((4,0,5),(6,65,72)):
                if old[offset]!=target[offset]:
                    if (old[offset],target[offset])!=(initial,final) or old[offset-1]!=0 or target[offset-1]!=0:
                        raise ValueError('DHW parameter transition outside bench proposal')
                    modified[offset]=target[offset]
        if pid == 14:
            for offset, initial, final in ((25,70,83),(26,5,9)):
                if old[offset]!=target[offset]:
                    if (old[offset],target[offset])!=(initial,final) or before[44][10]!=7:
                        raise ValueError('Burner parameter transition outside bench proposal')
                    modified[offset]=target[offset]
        if pid == 12:
            desired_delay=target[20]
            if block(source,14)[16]!=desired_delay or old[20]!=before[14][16]:
                raise ValueError('Room delay mirror mismatch')
            if old[20]!=desired_delay:
                if (old[20],desired_delay)!=(5,15):
                    raise ValueError('Room delay outside bench proposal')
                modified[20]=desired_delay
                mirror=bytearray(before[14])
                mirror[16]=desired_delay
                expected[14]=bytes(mirror)
        expected[pid] = bytes(modified)
        if pid in SHIFT_MIRRORS:
            offset, mirror = SHIFT_MIRRORS[pid]
            if block(source, mirror)[9] != target[offset]:
                raise ValueError(f'ID {pid}: Source parallel shift mirror mismatch')
            apply_shift_mirror(pid, before, expected)
    return expected

