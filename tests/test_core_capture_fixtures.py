import json
import unittest
from pathlib import Path
from ouman_eh203.simulator import SimulatedSerial
from ouman_eh203.protocol import request, classify
from ouman_eh203.transport import exchange

ROOT=Path(__file__).parent/'fixtures'/'eh203_215'

class CaptureFixtureTests(unittest.TestCase):
    def test_original_and_factory(self):
        paths=[ROOT/'pre_reset_pass1.json',ROOT/'factory_reset_pass1.json']
        if not all(p.is_file() for p in paths):
            self.skipTest('Real capture fixtures not installed')
        original,factory=[json.loads(p.read_text()) for p in paths]
        sim=SimulatedSerial.from_backups(original,factory)
        for obj in (original,factory):
            for pid in range(256):
                with self.subTest(pid=pid, capture=obj['created_at']):
                    status,data,error=classify(exchange(sim,request(pid)),pid)
                    rec=obj['records'][str(pid)]
                    self.assertEqual(status,rec['status'])
                    if status=='accepted':
                        self.assertEqual(data,bytes.fromhex(rec['data']))
            sim.factory_reset()
        sim.reboot()
        self.assertEqual(sim.blocks[65],bytes.fromhex(factory['records']['65']['data']))
