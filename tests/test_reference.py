import contextlib
import io
import json
import unittest
from pathlib import Path
from ouman_eh203.reference import factory_reference, REFERENCE_SHA256
from ouman_eh203.cli import main

FIXTURE=Path(__file__).parent/'fixtures'/'eh203_215'/'factory_reset_pass1.json'

class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.snapshot=json.loads(FIXTURE.read_text())

    def test_reference(self):
        r=factory_reference(self.snapshot)
        self.assertEqual(len(r['fields']),82)
        self.assertEqual(r['source_records_sha256'],REFERENCE_SHA256)
        self.assertEqual(r['firmware'],'2.15')
        self.assertTrue(r['read_only'])
        row=r['fields']['valve_center_close']
        self.assertIsNone(row['factory_default'])
        self.assertEqual(row['observed_factory_default'],'19')
        self.assertEqual(row['documentation_status'],'unresolved')

    def test_unregistered_reference(self):
        self.snapshot['records_sha256']='0'*64
        with self.assertRaises(ValueError):
            factory_reference(self.snapshot)

    def test_tampered_reference(self):
        self.snapshot['records']['1']['data']='00'
        with self.assertRaises(ValueError):
            factory_reference(self.snapshot)

    def test_cli_reference(self):
        out=io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(['metadata','--reference',str(FIXTURE),'--key','dhw_high_alarm']),0)
        row=json.loads(out.getvalue())['fields']['dhw_high_alarm']
        self.assertEqual(row['observed_factory_default'],'65')
        self.assertEqual(row['factory_default'],65)
        self.assertEqual(row['default_comparison'],'match')
