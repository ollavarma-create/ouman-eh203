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
                if entry['factory_default'] is not None:
                    self.assertLessEqual(limits[0], entry['factory_default'])
                    self.assertLessEqual(entry['factory_default'], limits[1])

    def test_localization(self):
        for entry in PARAMETERS.values():
            if entry['documentation_status']=='partial':
                for lang in ('fi','en'):
                    self.assertTrue(entry['label'][lang])
                    if '_curve_' not in entry['key']:
                        self.assertTrue(entry['lcd_label'][lang])
                    self.assertTrue(entry['manual_page'][lang])

    def test_detached_record(self):
        entry=get_metadata('l1_supply_min')
        entry['label']['fi']='changed'
        self.assertNotEqual(get_metadata('l1_supply_min')['label']['fi'],'changed')

    def test_unknown_key(self):
        with self.assertRaises(KeyError):
            get_metadata('unknown')

    def test_curve_visibility(self):
        for prefix in ('l1','l2'):
            for axis,i in [('x',3),('y',2),('y',4)]:
                self.assertEqual(get_metadata(f'{prefix}_curve_{axis}{i}')['dependencies']['visible_values'],[0])
            self.assertEqual(get_metadata(f'{prefix}_curve_y3')['dependencies']['visible_values'],[0,1])

    def test_curve_default_not_example(self):
        self.assertIsNone(get_metadata('l1_curve_y1')['factory_default'])
        self.assertEqual(get_metadata('l1_curve_type')['factory_default'],1)
