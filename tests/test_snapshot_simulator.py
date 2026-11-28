import copy
import unittest
from pathlib import Path
from ouman_eh203.backup import load
from ouman_eh203.simulator import SimulatedSerial
from ouman_eh203.monitoring import read_block

class SnapshotSimulatorTests(unittest.TestCase):
    def test_snapshot(self):
        path = Path(__file__).parent / "fixtures/eh203_215/factory_reset_pass1.json"
        snapshot = load(path)
        original = copy.deepcopy(snapshot)
        sim = SimulatedSerial.from_snapshot(snapshot)
        for key, record in snapshot["records"].items():
            if record["status"] == "accepted":
                self.assertEqual(read_block(sim, int(key)), bytes.fromhex(record["data"]))
        with self.assertRaises(ValueError):
            sim.factory_reset()
        sim.blocks[1] = b"changed"
        sim.reboot()
        self.assertEqual(sim.blocks[1], bytes.fromhex(snapshot["records"]["1"]["data"]))
        self.assertEqual(snapshot, original)
        snapshot["complete"] = False
        with self.assertRaises(ValueError):
            SimulatedSerial.from_snapshot(snapshot)
