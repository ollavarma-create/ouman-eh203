import unittest
from ouman_eh203.monitoring import OperationManager, demo_serial, temperature

class MonitoringTests(unittest.TestCase):
    def test_temperature(self):
        self.assertEqual(temperature(bytes.fromhex("fe0c")), -5)
        self.assertIsNone(temperature(bytes.fromhex("865a")))
        with self.assertRaises(ValueError):
            temperature(b"\x00")

    def test_session(self):
        ser = demo_serial()
        closed = []
        ser.close = lambda: closed.append(True)
        manager = OperationManager("", True, factory=lambda: ser)
        samples = []
        identity = []
        def sample(pid, value, stamp):
            samples.append((pid, value))
            if len(samples) == 3:
                manager.stop()
        manager.run(identity.append, sample)
        self.assertEqual(identity, ["44 45 4d 4f"])
        self.assertEqual(samples, [(18, -5), (20, 28), (21, 21)])
        self.assertTrue(all(tx[1] == 0x81 for tx in ser.writes))
        self.assertEqual(closed, [True])

    def test_failure_closes(self):
        ser = demo_serial()
        ser.fault = "checksum"
        closed = []
        ser.close = lambda: closed.append(True)
        manager = OperationManager("", True, factory=lambda: ser)
        with self.assertRaises(ValueError):
            manager.run(lambda x: None, lambda *x: None)
        self.assertEqual(closed, [True])
