import unittest
from pathlib import Path
from ouman_eh203.backup import load, verify_file
from ouman_eh203.scenario import encode, decode
from ouman_eh203.parameter_edit import proposal

class ScenarioTests(unittest.TestCase):
    def setUp(self):
        self.source = load(Path(__file__).parent/'fixtures/eh203_215/factory_reset_pass1.json')
        _, self.sim, _ = decode(self.source)

    def test_roundtrip(self):
        pid, before, after = proposal(self.sim,'dhw_setpoint','61.1')
        self.sim.blocks[pid] = after
        doc = encode(self.source,self.sim)
        source, sim, scenario = decode(doc)
        self.assertTrue(scenario)
        self.assertEqual(source,self.source)
        self.assertEqual(sim.blocks,self.sim.blocks)
        self.assertEqual(sim.persistent,sim.blocks)
        self.assertEqual(doc['payload']['changed_ids'],[pid])
        self.assertEqual(bytes.fromhex(source['records'][str(pid)]['data']),before)

    def test_not_backup(self):
        with self.assertRaises(ValueError):
            verify_file(encode(self.source,self.sim))

    def test_corruption(self):
        doc = encode(self.source,self.sim)
        doc['payload']['blocks']['1']='00'
        with self.assertRaises(ValueError):
            decode(doc)
