import copy
import json
import unittest
from pathlib import Path
from ouman_eh203.backup import digest
from ouman_eh203.restore import plan, execute_simulated, compatibility, authorize, block_identity
from ouman_eh203.simulator import SimulatedSerial

ROOT=Path(__file__).parent/'fixtures'/'eh203_215'

class ReplacementTests(unittest.TestCase):
    def setUp(self):
        self.source,self.factory=[json.loads((ROOT/n).read_text()) for n in ('pre_reset_pass1.json','factory_reset_pass1.json')]
        self.target=copy.deepcopy(self.factory)
        rec=self.target['records']['1']
        raw=bytearray.fromhex(rec['data'])
        raw[0]^=1
        rec['data']=raw.hex(' ').upper()
        rx=bytearray.fromhex(rec['rx'])
        rx[5:-1]=raw
        rx[-1]=sum(rx[1:-1])&255
        rec['rx']=rx.hex(' ').upper()
        self.target['records_sha256']=digest(self.target['records'])
    def test_replacement_requires_confirmation(self):
        with self.assertRaises(ValueError):
            plan(self.source,self.target)
    def test_confirmed_replacement(self):
        steps=plan(self.source,self.target,allow_device_mismatch=True)
        sim=SimulatedSerial.from_backups(self.target,self.target)
        identity=block_identity(self.target)
        execute_simulated(sim,self.source,steps,[],target_identity=identity,allow_device_mismatch=True)
        self.assertEqual(sim.blocks[1][:9],identity)
    def test_unapproved_target(self):
        steps=plan(self.source,self.target,allow_device_mismatch=True)
        sim=SimulatedSerial.from_backups(self.target,self.target)
        with self.assertRaises(ValueError):
            execute_simulated(sim,self.source,steps,[],allow_device_mismatch=True)
        self.assertFalse(any(t[1]==0x82 for t in sim.writes))
    def test_unknown_firmware(self):
        a=block_identity(self.source)
        b=a[:8]+bytes((218,))
        self.assertTrue(compatibility(a,b)['firmware_mismatch'])
        with self.assertRaises(ValueError):
            authorize(a,b,allow_firmware_mismatch=True)
