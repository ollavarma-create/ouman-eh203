import copy
import json
import unittest
from pathlib import Path
from ouman_eh203.defaults import compare_defaults

class DefaultsTests(unittest.TestCase):
    def setUp(self):
        self.factory=json.loads((Path(__file__).parent/'fixtures'/'eh203_215'/'factory_reset_pass1.json').read_text())

    def test_comparison(self):
        before=copy.deepcopy(self.factory)
        report=compare_defaults(self.factory,factory_reset_confirmed=True)
        self.assertEqual(len(report['fields']),82)
        self.assertEqual(sum(report['counts'].values()),82)
        self.assertEqual(report['source_records_sha256'],self.factory['records_sha256'])
        self.assertTrue(report['read_only'])
        self.assertEqual(self.factory,before)
        self.assertEqual(report['fields']['l1_curve_y1']['status'],'undocumented')

    def test_confirmation(self):
        with self.assertRaises(ValueError):
            compare_defaults(self.factory)

    def test_bad_digest(self):
        self.factory['records_sha256']='0'*64
        with self.assertRaises(ValueError):
            compare_defaults(self.factory,factory_reset_confirmed=True)

    def test_documented_conflict(self):
        report=compare_defaults(self.factory,factory_reset_confirmed=True)
        self.assertIn('manual_default_conflict',report['fields']['dhw_high_alarm']['dependencies'])
