"""Pure wire codec; no serial side effects."""
def request(pid):
    if not isinstance(pid, int) or not 0 <= pid <= 255:
        raise ValueError('Invalid ID')
    body = bytes((0x81, 2, 0, pid))
    return b'\x02' + body + bytes((sum(body) & 255,))


def classify(rx, pid):
    if len(rx) < 6 or rx[0] != 2 or len(rx) != rx[2] + 4:
        return 'invalid', None, 'framing/length'
    if sum(rx[1:-1]) & 255 != rx[-1]:
        return 'invalid', None, 'checksum'
    if rx[2] == 2 and rx[3:5] == b'\x00\xff':
        return 'rejected', None, None
    if rx[3:5] != bytes((0, pid)):
        return 'invalid', None, 'ID echo'
    return 'accepted', rx[5:-1], None


def write_frame(pid, payload):
    if not 0 <= pid < 255 or not 0 < len(payload) <= 253:
        raise ValueError("Invalid write frame")
    body = bytes((0x82,len(payload)+2,0,pid))+payload
    return b'\x02'+body+bytes((sum(body)&255,))

def decode(rx,pid,size):
    status,data,error=classify(rx,pid)
    if status!='accepted' or len(data)!=size:
        raise ValueError("Invalid or rejected response")
    return data
