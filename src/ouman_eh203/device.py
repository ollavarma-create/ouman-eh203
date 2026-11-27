"""Read-only device interface. Writing is not exposed yet."""
from .protocol import request, decode, classify
from .transport import exchange

class Device:
    def __init__(self, serial):
        self.serial = serial

    def read(self, pid):
        status, data, error = classify(exchange(self.serial, request(pid)), pid)
        if status != 'accepted':
            raise ValueError(f'ID {pid}: {status} {error or ""}')
        return data

    def identity(self):
        raw = self.read(1)
        if len(raw)<9 or raw[4:7]!=b'203' or raw[8]!=215:
            raise ValueError('Unsupported controller')
        return raw[:9]
