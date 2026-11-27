import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from ouman_eh203.restore import plan, execute_simulated, recovery_preview, IDS
from ouman_eh203.simulator import SimulatedSerial
from ouman_eh203.schedules import semantic_key, equivalent_readback
from ouman_eh203.validation import block

ROOT=Path(__file__).parent/'fixtures'/'eh203_215'

class ScheduleRestoreTests(unittest.TestCase):
    def setUp(self):
        self.source,self.factory=[json.loads((ROOT/n).read_text()) for n in ('pre_reset_pass1.json','factory_reset_pass1.json')]
        self.sim=SimulatedSerial.from_backups(self.factory,self.factory)
        self.steps=plan(self.source,self.factory)
    def test_relocation(self):
        self.sim.relocate_schedules=True
        result=execute_simulated(self.sim,self.source,self.steps,[])
        desired={i:block(self.source,i) for i in IDS}
        self.assertNotEqual(result[4],desired[4])
        self.assertEqual(semantic_key(result),semantic_key(desired))
    def test_unknown_byte_difference(self):
        desired={i:block(self.source,i) for i in IDS}
        actual=dict(desired)
        actual[4]=bytes((desired[4][0]^1,))+desired[4][1:]
        self.assertFalse(equivalent_readback(actual,desired))
    def test_unexpected_readback(self):
        original=self.sim.write
        def corrupt(tx):
            n=original(tx)
            if tx[1]==0x82:
                b=bytearray(self.sim.blocks[13]); b[-1]^=1
                self.sim.blocks[13]=bytes(b)
            return n
        with patch.object(self.sim,'write',side_effect=corrupt):
            with self.assertRaises(ValueError):
                execute_simulated(self.sim,self.source,self.steps,[])
        self.assertEqual(sum(t[1]==0x82 for t in self.sim.writes),1)
    def test_interrupted_schedule(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'journal.json'
            original=self.sim.write
            def lose(tx):
                if tx[1]==0x82 and tx[4]==4:
                    self.sim.fault='timeout'
                return original(tx)
            with patch.object(self.sim,'write',side_effect=lose):
                with self.assertRaises(ValueError):
                    execute_simulated(self.sim,self.source,self.steps,[],journal_path=path)
            self.sim.reboot()
            count=sum(t[1]==0x82 for t in self.sim.writes)
            with self.assertRaises(ValueError):
                recovery_preview(self.sim,self.source,path)
            self.assertEqual(sum(t[1]==0x82 for t in self.sim.writes),count)
