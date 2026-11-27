import json
import unittest
from pathlib import Path
from ouman_eh203.simulator import SimulatedSerial
from ouman_eh203.restore import plan, build, execute_simulated, IDS
from ouman_eh203.validation import block
from ouman_eh203.schedules import semantic_key
from ouman_eh203.registry import FIELDS

ROOT=Path(__file__).parent/'fixtures'/'eh203_215'

class RestoreTests(unittest.TestCase):
    def test_complete_restore(self):
        original,factory=[json.loads((ROOT/n).read_text()) for n in ('pre_reset_pass1.json','factory_reset_pass1.json')]
        sim=SimulatedSerial.from_backups(original,factory)
        sim.factory_reset()
        steps=plan(original,factory)
        self.assertTrue(steps)
        self.assertFalse(sim.writes)
        log=[]
        execute_simulated(sim,original,steps,log)
        sim.reboot()
        for name,pid,offset,width,*_ in FIELDS:
            self.assertEqual(sim.blocks[pid][offset:offset+width],block(original,pid)[offset:offset+width],name)
        self.assertEqual(semantic_key(sim.blocks),semantic_key({i:block(original,i) for i in IDS}))
        self.assertEqual(sim.blocks[43],block(original,43))
        self.assertEqual(sim.blocks[95],block(factory,95))
        self.assertEqual(build(original,{i:sim.blocks[i] for i in IDS}),[])
        self.assertTrue(all(e['status']=='verified' for e in log))
        self.assertTrue(all(t[4] in IDS for t in sim.writes if t[1]==0x82))

    def test_mode_recalculation(self):
        original,factory=[json.loads((ROOT/n).read_text()) for n in ('pre_reset_pass1.json','factory_reset_pass1.json')]
        sim=SimulatedSerial.from_backups(original,factory)
        sim.factory_reset()
        sim.recalculate_curves=True
        log=[]
        execute_simulated(sim,original,plan(original,factory),log)
        self.assertIn('replanned_ids',log[0])
        self.assertEqual(build(original,{i:sim.blocks[i] for i in IDS}),[])

    def test_unexpected_mode_side_effect_stops(self):
        original,factory=[json.loads((ROOT/n).read_text()) for n in ('pre_reset_pass1.json','factory_reset_pass1.json')]
        sim=SimulatedSerial.from_backups(original,factory)
        sim.factory_reset()
        def settle():
            b=bytearray(sim.blocks[65])
            b[30]^=1
            sim.blocks[65]=bytes(b)
        log=[]
        with self.assertRaisesRegex(ValueError,'Unexpected mode transition'):
            execute_simulated(sim,original,plan(original,factory),log,settle=settle)
        self.assertEqual(sum(t[1]==0x82 for t in sim.writes),1)
        self.assertIn('observed',log[0])
