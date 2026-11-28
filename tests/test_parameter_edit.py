import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from ouman_eh203.backup import load
from ouman_eh203.simulator import SimulatedSerial
from ouman_eh203.parameter_edit import current,proposal,apply

class ParameterEditTests(unittest.TestCase):
    def setUp(self):
        self.sim=SimulatedSerial.from_snapshot(load(Path(__file__).parent/'fixtures/eh203_215/factory_reset_pass1.json'))

    def test_edit(self):
        before=dict(self.sim.blocks)
        p=proposal(self.sim,'dhw_setpoint','61.1')
        with TemporaryDirectory() as d:
            safety=Path(d)/'before.json'
            journal=Path(d)/'journal.json'
            self.assertTrue(apply(self.sim,'dhw_setpoint','61.1',p,safety,journal))
            self.assertEqual(load(journal)['status'],'verified')
            self.assertEqual(bytes.fromhex(load(safety)['records']['16']['data']),before[16])
        self.assertEqual(str(current(self.sim,'dhw_setpoint')),'61.1')
        self.assertEqual({k:v for k,v in self.sim.blocks.items() if k!=16},{k:v for k,v in before.items() if k!=16})
        self.assertEqual(self.sim.blocks[16][3:],before[16][3:])

    def test_limits(self):
        for value in ('96','61.15','NaN'):
            with self.assertRaises(ValueError):
                proposal(self.sim,'dhw_setpoint',value)

    def test_dependency(self):
        with self.assertRaises(ValueError):
            proposal(self.sim,'l1_supply_max',15) if current(self.sim,'l1_supply_min')>15 else proposal(self.sim,'l1_supply_min',70) if current(self.sim,'l1_supply_max')<70 else proposal(self.sim,'l1_supply_max',14)

    def test_no_physical_target(self):
        with self.assertRaises(ValueError):
            proposal(object(),'dhw_setpoint',60)

    def test_stale(self):
        p=proposal(self.sim,'dhw_setpoint',60)
        self.sim.blocks[16]=proposal(self.sim,'dhw_setpoint',62)[2]
        with self.assertRaises(ValueError):
            apply(self.sim,'dhw_setpoint',60,p,'unused','unused')
