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
                    self.assertIn(lang, entry['lcd_label'])
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

    def test_pid_defaults(self):
        for prefix,p,i in [('l1',140,50),('l2',140,50),('dhw',70,18)]:
            self.assertEqual(get_metadata(prefix+'_p_band')['factory_default'],p)
            self.assertEqual(get_metadata(prefix+'_i_time')['factory_default'],i)
            self.assertEqual(get_metadata(prefix+'_d_time')['manual_range'],[0,10])
            self.assertEqual(get_metadata(prefix+'_p_band')['access_level'],'service')

    def test_motor_choices(self):
        for prefix in ('l1','l2'):
            self.assertEqual(set(get_metadata(prefix+'_motor_type')['choices']),{0,1,2})
            self.assertEqual(get_metadata(prefix+'_actuator_time')['factory_default'],150)

    def test_special_service_settings(self):
        self.assertEqual(get_metadata('room_delay')['manual_range'],[0,2])
        self.assertEqual(get_metadata('power_limit')['factory_default'],999)
        self.assertEqual(get_metadata('dhw_alarm_delay')['manual_range'],[0,700])
        self.assertEqual(get_metadata('l2_deviation_alarm')['dependencies']['delay_key'],'deviation_alarm_delay')
        self.assertEqual(get_metadata('room_delay')['access_level'],'special_service')

    def test_manual_conflicts_preserved(self):
        self.assertIn('manual_default_conflict',get_metadata('dhw_high_alarm')['dependencies'])
        self.assertIn('manual_label_conflict',get_metadata('r1_outdoor_threshold')['dependencies'])

    def test_all_fields_reviewed(self):
        self.assertEqual(len(PARAMETERS),82)
        self.assertFalse(any(e['documentation_status']=='pending' for e in PARAMETERS.values()))
        self.assertEqual(get_metadata('valve_center_close')['documentation_status'],'unresolved')

    def test_pressure_defaults(self):
        self.assertIsNone(get_metadata('pressure_range')['factory_default'])
        self.assertEqual([get_metadata('pressure_'+k+'_alarm')['factory_default']
                          for k in ('upper','filling','lower')],[2.2,0.7,0.5])

    def test_consumption_alarm(self):
        self.assertEqual(get_metadata('consumption_alarm_interval')['manual_range'],[0,99])
        self.assertEqual(get_metadata('consumption_alarm_interval')['factory_default'],0)
