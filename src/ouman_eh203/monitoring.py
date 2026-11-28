"""Single-owner polling session. Only canonical reads, no write API."""
from datetime import datetime, timezone
from threading import Event
from .protocol import request, classify
from .transport import open_serial, exchange
from .simulator import SimulatedSerial

POLL_IDS = (18, 20, 21)

def demo_serial():
    return SimulatedSerial({1: b"DEMO", 18: bytes.fromhex("fe0c"),
                            20: bytes.fromhex("0af0"), 21: bytes.fromhex("0834")})

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
    def __init__(self, port, simulated, interval=3, factory=None):
        self.port, self.simulated, self.interval = port, simulated, interval
        self.factory = factory
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
                for pid in POLL_IDS:
                    if self.stop_event.is_set():
                        break
                    data = read_block(ser, pid)
                    sample(pid, temperature(data), datetime.now(timezone.utc).isoformat())
                self.stop_event.wait(self.interval)
        finally:
            close = getattr(ser, "close", None)
            if close:
                close()
