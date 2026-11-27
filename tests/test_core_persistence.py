import copy
import json
import tempfile
import unittest
from pathlib import Path
from ouman_eh203.persistence import verify
from ouman_eh203.restore import plan, execute_simulated
from ouman_eh203.simulator import SimulatedSerial
from ouman_eh203.backup import digest, exchange, verify_file

ROOT=Path(__file__).parent/'fixtures'/'eh203_215'

class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.source,self.factory=[json.loads((ROOT/n).read_text()) for n in ('pre_reset_pass1.json','factory_reset_pass1.json')]
        sim=SimulatedSerial.from_backups(self.source,self.factory)
        sim.factory_reset()
        sim.recalculate_curves=True
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'journal.json'
            execute_simulated(sim,self.source,plan(self.source,self.factory),[],journal_path=p)
            self.journal=json.loads(p.read_text())
        sim.reboot()
        self.reboot=copy.deepcopy(self.source)
        for k in self.reboot['records']:
            self.reboot['records'][k]=exchange(sim,int(k))
        self.reboot['records_sha256']=digest(self.reboot['records'])
        verify_file(self.reboot)

    def check(self):
        return verify(self.source,self.journal,self.reboot,power_cycle_confirmed=True)

    def test_success(self):
        self.assertTrue(self.check()['persistence_verified'])

    def test_confirmation_required(self):
        with self.assertRaises(ValueError):
            verify(self.source,self.journal,self.reboot)

    def test_incomplete_journal(self):
        self.journal['status']='running'
        with self.assertRaises(ValueError):
            self.check()

    def test_wrong_identity(self):
        self.journal['target_identity']='00'*9
        with self.assertRaises(ValueError):
            self.check()

    def test_bad_ack(self):
        self.journal['entries'][0]['rx']='00'
        with self.assertRaises(ValueError):
            self.check()

    def test_bad_digest(self):
        self.reboot['records_sha256']='0'*64
        with self.assertRaises(ValueError):
            self.check()

    def test_factory_state_rejected(self):
        self.reboot=self.factory
        with self.assertRaises(ValueError):
            self.check()
