"""Single-owner polling session. Only canonical reads, no write API."""
from datetime import datetime, timezone
from threading import Event
from .protocol import request, classify
from .transport import open_serial, exchange
from .simulator import SimulatedSerial
from .curves import decode_curve

POLL_IDS = (18, 20, 21, 15, 16, 42, 45, 51, 13, 17, 27, 23, 24, 25, 26, 33, 65, 66)
ACTIVE_KEYS = {18, 20, 21, "l1_target", "dhw_target", "dhw_valve",
               "l1_mode", "l2_mode", "dhw_mode", "r1", "r2", "l1_room_setpoint", "l2_room", 23, 24, 25, 26, 33}

def decode_samples(pid, data):
    if pid in (65, 66):
        try:
            return [(pid, decode_curve(data))]
        except ValueError:
            return [(pid, None)]
    if pid in (18, 20, 21, 23, 24, 25, 26, 33):
        return [(pid, temperature(data))]
    if pid == 13:
        if len(data) < 3:
            raise ValueError('Short room setpoint response')
        return [('l1_room_setpoint', int.from_bytes(data[1:3], 'big') / 10)]
    minimum = {15: 15, 16: 3, 42: 2, 45: 2, 51: 1}[pid]
    if len(data) < minimum:
        raise ValueError(f"Short response for ID {pid}")
    if pid == 15:
        return [("l1_target", data[14])]
    if pid == 16:
        return [("dhw_target", int.from_bytes(data[1:3], "big") / 10)]
    if pid == 42:
        return [("l1_mode", data[1] & 15), ("l2_mode", data[1] >> 4),
                ("dhw_mode", data[0] & 15)]
    if pid == 45:
        return [("r1", bool(data[1] & 8)), ("r2", bool(data[1] & 16))]
    if data[0] > 100:
        raise ValueError("Invalid DHW command percentage")
    return [("dhw_valve", data[0])]

def demo_serial():
    return SimulatedSerial({1: b"DEMO", 18: bytes.fromhex("fe0c"),
                            20: bytes.fromhex("0af0"), 21: bytes.fromhex("0834"), 15: bytes(14)+bytes([30]),
                            16: bytes.fromhex("000244"), 42: bytes.fromhex("0021"),
                            45: bytes.fromhex("0008"), 51: bytes([26]), 13: bytes.fromhex('0000d7'),
                            17: bytes([12]*8+[5]+[12]*11), 27: bytes.fromhex('07d0'), 23: bytes.fromhex('0974'), 24: bytes.fromhex('09ce'), 25: bytes.fromhex('1482'), 26: bytes.fromhex('1036'), 33: bytes.fromhex('085c'), 65: bytes([0,38,34,25,22,20,244,0,10])+bytes(22), 66: bytes([1,62,52,42,31,20,246,0,10])+bytes(22)})

def read_block(ser, pid):
    status, data, error = classify(exchange(ser, request(pid)), pid)
    if status != "accepted" or not data:
        raise ValueError(f"ID {pid}: {error or status}")
    return data

def temperature(data):
    if len(data) < 2:
        raise ValueError("Short temperature response")
    raw = data[:2]
    return None if raw == bytes.fromhex("865a") else int.from_bytes(raw, "big", signed=True) / 100

class OperationManager:
    def __init__(self, port, simulated, interval=3, factory=None, snapshot=False):
        self.port, self.simulated, self.interval = port, simulated, interval
        self.factory = factory
        self.snapshot = snapshot
        self.stop_event = Event()

    def stop(self):
        self.stop_event.set()

    def run(self, identity, sample):
        if self.stop_event.is_set():
            return
        ser = self.factory() if self.factory else (demo_serial() if self.simulated else open_serial(self.port))
        try:
            identity(read_block(ser, 1).hex(" "))
            while not self.stop_event.is_set():
                routing = None
                for pid in POLL_IDS:
                    if self.stop_event.is_set():
                        break
                    try:
                        data = read_block(ser, pid)
                    except ValueError:
                        if not self.snapshot:
                            raise
                        continue
                    stamp = datetime.now(timezone.utc).isoformat()
                    if pid == 17:
                        if len(data) < 20 and self.snapshot:
                            continue
                        if len(data) < 20:
                            raise ValueError('Short routing response')
                        routing = data
                        continue
                    if pid == 27:
                        # Only the independently observed physical input 6 route.
                        # Do not interpret bus, pressure or wind data as temperature.
                        value = temperature(data) if routing is not None and routing[8] == 5 and all(routing[i] != 5 for i in (9, 11, 12, 19)) else None
                        sample('l2_room', value, stamp)
                        continue
                    try:
                        decoded = decode_samples(pid, data)
                    except ValueError:
                        if not self.snapshot:
                            raise
                        continue
                    for key, value in decoded:
                        sample(key, value, stamp)
                self.stop_event.wait(self.interval)
        finally:
            close = getattr(ser, "close", None)
            if close:
                close()
