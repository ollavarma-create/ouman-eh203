import unittest
from ouman_eh203.metadata import PARAMETERS, get_metadata
from ouman_eh203.registry import FIELDS

class MetadataTests(unittest.TestCase):
    def test_coverage(self):
        self.assertEqual(set(PARAMETERS), {f[0] for f in FIELDS})
        self.assertEqual(len(PARAMETERS), len(FIELDS))

    def test_no_write_authorization(self):
        for entry in PARAMETERS.values():
            self.assertEqual(entry['write_policy'], 'restore_validator_only')

    def test_documented_ranges(self):
        for entry in PARAMETERS.values():
            limits=entry['manual_range']
            if limits is not None:
                self.assertLessEqual(limits[0], limits[1])
                self.assertLessEqual(limits[0], entry['factory_default'])
                self.assertLessEqual(entry['factory_default'], limits[1])

    def test_localization(self):
        for entry in PARAMETERS.values():
            if entry['documentation_status']=='partial':
                for lang in ('fi','en'):
                    self.assertTrue(entry['label'][lang])
                    self.assertTrue(entry['lcd_label'][lang])
                    self.assertTrue(entry['manual_page'][lang])

    def test_detached_record(self):
        entry=get_metadata('l1_supply_min')
        entry['label']['fi']='changed'
        self.assertNotEqual(get_metadata('l1_supply_min')['label']['fi'],'changed')

    def test_unknown_key(self):
        with self.assertRaises(KeyError):
            get_metadata('unknown')
