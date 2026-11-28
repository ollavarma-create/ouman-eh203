"""Read-only curve representation; endpoint X values follow manual conventions."""
from dataclasses import dataclass

@dataclass(frozen=True)
class HeatingCurve:
    mode: int
    stored: tuple

    @property
    def active(self):
        if self.mode == 1:
            return ((-20, self.stored[0][1]), (0, self.stored[2][1]), (20, self.stored[4][1]))
        return self.stored

def decode_curve(data):
    if len(data) != 31 or data[0] not in (0, 1):
        raise ValueError("Unsupported curve block")
    xs = (-20, *(int.from_bytes(data[i:i+1], "big", signed=True) for i in (6, 7, 8)), 20)
    curve = HeatingCurve(data[0], tuple(zip(xs, data[1:6])))
    if any(a[0] >= b[0] for a, b in zip(curve.active, curve.active[1:])):
        raise ValueError("Non-increasing active curve coordinates")
    return curve
