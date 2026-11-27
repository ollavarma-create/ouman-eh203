import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from ouman_eh203.restore import plan, execute_simulated, recovery_preview
from ouman_eh203.simulator import SimulatedSerial

ROOT=Path(__file__).parent/'fixtures'/'eh203_215'

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.source,self.factory=[json.loads((ROOT/n).read_text()) for n in ('pre_reset_pass1.json','factory_reset_pass1.json')]
        self.sim=SimulatedSerial.from_backups(self.factory,self.factory)
        self.steps=plan(self.source,self.factory)
    def test_corrupt_backup(self):
        bad=copy.deepcopy(self.source)
        bad['records_sha256']='bad'
        with self.assertRaises(ValueError):
            plan(bad,self.factory)
    def test_stale_plan(self):
        self.sim.blocks[13]=bytes(31)
        with self.assertRaises(ValueError):
            execute_simulated(self.sim,self.source,self.steps,[])
        self.assertFalse(any(t[1]==0x82 for t in self.sim.writes))
    def test_lost_ack_and_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'journal.json'
            original_write=self.sim.write
            def lose_ack(tx):
                if tx[1]==0x82:
                    journal=json.loads(path.read_text())
                    self.assertEqual(journal['entries'][-1]['status'],'write_outcome_unknown')
                    self.sim.fault='timeout'
                return original_write(tx)
            with patch.object(self.sim,'write',side_effect=lose_ack):
                with self.assertRaises(ValueError):
                    execute_simulated(self.sim,self.source,self.steps,[],journal_path=path)
            self.assertEqual(sum(t[1]==0x82 for t in self.sim.writes),1)
            self.sim.reboot()
            remaining=recovery_preview(self.sim,self.source,path)
            self.assertTrue(remaining)
            new_path=Path(d)/'recovery.json'
            execute_simulated(self.sim,self.source,remaining,[],journal_path=new_path)
            report=json.loads(new_path.read_text())
            self.assertEqual(report['status'],'complete')
            self.assertEqual(report['verification'],'readback_only')
            self.assertFalse(report['persistence_verified'])
            self.assertEqual(recovery_preview(self.sim,self.source,new_path),[])
    def test_existing_journal(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'journal.json'
            path.write_text('existing evidence')
            with self.assertRaises(FileExistsError):
                execute_simulated(self.sim,self.source,self.steps,[],journal_path=path)
            self.assertEqual(path.read_text(),'existing evidence')
            self.assertFalse(any(t[1]==0x82 for t in self.sim.writes))
