import unittest
from ouman_eh203.monitoring import OperationManager, demo_serial, temperature, decode_samples

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
            if len(samples) == 13:
                manager.stop()
        manager.run(identity.append, sample)
        self.assertEqual(identity, ["44 45 4d 4f"])
        self.assertEqual(samples, [(18, -5), (20, 28), (21, 21), ('l1_target', 30), ('dhw_target', 58), ('l1_mode', 1), ('l2_mode', 2), ('dhw_mode', 0), ('r1', True), ('r2', False), ('dhw_valve', 26), ('l1_room_setpoint', 21.5), ('l2_room', 20)])
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

    def test_control_decoding(self):
        self.assertEqual(decode_samples(42, bytes.fromhex("0521")), [("l1_mode", 1), ("l2_mode", 2), ("dhw_mode", 5)])
        self.assertEqual(decode_samples(45, bytes.fromhex("0010")), [("r1", False), ("r2", True)])
        self.assertEqual(decode_samples(51, bytes([100])), [("dhw_valve", 100)])
        with self.assertRaises(ValueError):
            decode_samples(51, bytes([101]))
        with self.assertRaises(ValueError):
            decode_samples(16, b"\x00")
