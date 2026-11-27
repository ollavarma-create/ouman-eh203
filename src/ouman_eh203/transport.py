"""Serial transport with exclusive access and no automatic retries."""
def read_exact(ser, size):
    parts = bytearray()
    while len(parts) < size:
        chunk = ser.read(size - len(parts))
        if not chunk:
            break
        parts.extend(chunk)
    return bytes(parts)


def open_serial(port):
    import serial
    return serial.Serial(port,4800,timeout=1.5,write_timeout=1.5,exclusive=True,rtscts=False,dsrdtr=False,xonxoff=False)

def exchange(ser,tx):
    ser.reset_input_buffer()
    if ser.write(tx)!=len(tx):
        raise OSError("Short serial write")
    ser.flush()
    h=read_exact(ser,3)
    return h+read_exact(ser,h[2]+1) if len(h)==3 and h[0]==2 else h
