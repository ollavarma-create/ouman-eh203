import json
import unittest
from ouman_eh203.metadata import PARAMETERS, get_metadata
from ouman_eh203.registry import FIELDS

class MetadataIntegrityTests(unittest.TestCase):
    def test_schema(self):
        for key, row in PARAMETERS.items():
            with self.subTest(key=key):
                self.assertEqual(row['key'],key)
                for name in ('label','lcd_label','description','menu_path','manual_page'):
                    self.assertEqual(set(row[name]),{'fi','en'})
                for page in row['manual_page'].values():
                    self.assertTrue(page is None or type(page) is int and 1 <= page <= 48)
                self.assertIn(row['access_level'],(None,'user','service','special_service'))
                json.dumps(row,allow_nan=False)

    def test_dependency_references(self):
        for key,row in PARAMETERS.items():
            deps=row['dependencies'] or {}
            for name in ('curve_type_key','motor_type_key','shared_with','delay_key','used_by','automatic_limit_increase'):
                if name in deps:
                    self.assertIn(deps[name],PARAMETERS)
                    self.assertNotEqual(deps[name],key)
            if 'visible_values' in deps:
                self.assertLessEqual(set(deps['visible_values']),set(PARAMETERS[deps['curve_type_key']]['choices']))
            if 'shared_with' in deps:
                self.assertEqual(PARAMETERS[deps['shared_with']]['dependencies']['shared_with'],key)

    def test_enum_defaults(self):
        for key,row in PARAMETERS.items():
            if 'choices' in row:
                self.assertIn(row['factory_default'],row['choices'])
                for choice in row['choices'].values():
                    self.assertEqual(set(choice),{'fi','en'})

    def test_unresolved_not_promoted(self):
        row=get_metadata('valve_center_close')
        self.assertEqual(row['documentation_status'],'unresolved')
        for field in ('factory_default','manual_range','access_level'):
            self.assertIsNone(row[field])
        self.assertEqual(row['write_policy'],'restore_validator_only')
