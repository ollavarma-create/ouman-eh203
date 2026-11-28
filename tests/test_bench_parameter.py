import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from ouman_eh203.backup import load, acquire, verify_file
from ouman_eh203.bench_parameter import (preview, execute_bench, _apply,
    draft_preview, execute_draft, _apply_draft)
from ouman_eh203.simulator import SimulatedSerial
from ouman_eh203.registry import QUICK_IDS


class BenchWire(SimulatedSerial):
    """Test double for the allowed field writes, not firmware evidence."""
    def __init__(self, blocks):
        super().__init__(blocks)
        self.write_fault = None

    def apply(self, pid, data):
        allowed = {12: {3, 4, 5, 7, 14, 27}, 13: {1, 2},
                   14: {3, 4, 5, 9, 23}, 16: {1, 2}}
        old = self.blocks[pid]
        if len(data) != len(old) or not set(i for i, (a, b) in enumerate(zip(old, data))
                                           if a != b) <= allowed.get(pid, set()):
            return False
        self.blocks[pid] = data
        self.persistent[pid] = data
        # Model only the exact observed L1 mirror and candidate L2 mirror.
        if pid in (12, 14):
            offset, mirror = {12: (27,65), 14: (23,66)}[pid]
            if old[offset] != data[offset]:
                b = bytearray(self.blocks[mirror])
                b[9] = data[offset]
                if self.write_fault == 'extra_mirror_byte':
                    b[10] ^= 1
                self.blocks[mirror] = self.persistent[mirror] = bytes(b)
        if self.write_fault == 'readback':
            self.blocks[pid] = old
        return True

    def write(self, tx):
        if tx[1] == 0x82 and self.write_fault == 'ack':
            self.fault = 'timeout'
        return super().write(tx)


class BenchParameterTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = load(Path(__file__).parent/'fixtures/eh203_215/factory_reset_pass1.json')
        self.sim = BenchWire(SimulatedSerial.from_snapshot(self.snapshot).blocks)
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.safety = self.directory/'safety.json'
        self.journal = self.directory/'journal.json'
        self.addCleanup(self.assert_no_extra_writes)
        self.allowed_writes = 0

    def assert_no_extra_writes(self):
        self.assertEqual(len([tx for tx in self.sim.writes if tx[1] == 0x82]),
                         self.allowed_writes)

    def capture(self):
        return acquire(self.sim, self.directory/'current.json', 0, progress=lambda *_: None)

    def apply(self, approved):
        with patch('ouman_eh203.backup.time.sleep'):
            return _apply(self.sim, approved, self.safety, self.journal, settle=lambda: None)

    def test_three_parameters_preserve_unknown_bytes(self):
        for key, value, pid, offsets in (
            ('l1_room_setpoint', '22.7', 13, {1, 2}),
            ('l1_supply_max', '81', 12, {4}),
            ('dhw_setpoint', '61.1', 16, {1, 2}),
        ):
            approved = preview(self.snapshot, key, value)
            before, after = dict(approved.before), dict(approved.after)
            self.assertEqual(approved.pid, pid)
            self.assertEqual({i for i in before if before[i] != after[i]}, {pid})
            self.assertTrue({i for i, (a, b) in enumerate(zip(before[pid], after[pid]))
                             if a != b} <= offsets)

    def test_three_point_mode(self):
        for pid in (65, 66):
            self.sim.blocks[pid] = bytes([1]) + self.sim.blocks[pid][1:]
        approved = preview(self.capture(), 'dhw_setpoint', '61.1')
        self.allowed_writes = 1
        self.assertTrue(self.apply(approved))
        self.assertEqual(self.sim.blocks[65][0], 1)
        self.assertEqual(self.sim.blocks[66][0], 1)
        self.assertTrue(verify_file(load(self.safety)))
        journal = load(self.journal)
        self.assertEqual(journal['status'], 'verified')
        self.assertFalse(journal['persistence_verified'])
        self.assertEqual(journal['observed'], journal['expected'])

    def test_quick_preview_and_safety_scan_only_accepted_ids(self):
        current = acquire(self.sim, self.directory/'quick.json', 0, quick=True,
                          progress=lambda *_: None)
        self.assertEqual([tx[4] for tx in self.sim.writes], list(QUICK_IDS))
        approved = preview(current, 'dhw_setpoint', '61.1')
        self.assertEqual(approved, preview(self.snapshot, 'dhw_setpoint', '61.1'))
        self.sim.writes.clear()
        self.allowed_writes = 1
        self.assertTrue(self.apply(approved))
        safety = load(self.safety)
        self.assertTrue(verify_file(safety))
        self.assertEqual(safety['profile'], 'eh203-2.15-bench-v1')
        self.assertEqual(set(map(int, safety['records'])), set(QUICK_IDS))
        self.assertTrue(all(tx[4] in QUICK_IDS for tx in self.sim.writes))
        self.assertEqual(load(self.journal)['safety_profile'], safety['profile'])

    def test_missing_accepted_id_blocks_write(self):
        approved = preview(self.snapshot, 'dhw_setpoint', '61.1')
        # A known readable ID outside the restore block set disappears.
        del self.sim.blocks[101]
        with self.assertRaises(ValueError):
            self.apply(approved)
        self.assertFalse(self.journal.exists())
        self.assertEqual(load(self.safety)['records']['101']['status'], 'rejected')

    def test_bounds_resolution_and_allowlist(self):
        for key, value in (('dhw_setpoint', '49.9'), ('dhw_setpoint', '65.1'),
                           ('dhw_setpoint', '58.01'), ('dhw_setpoint', 'NaN'),
                           ('l1_room_setpoint', '30.1'), ('l1_supply_max', 96),
                           ('l1_supply_max', '70.5'), ('dhw_boost', 5)):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                preview(self.snapshot, key, value)

    def test_dependency(self):
        b = bytearray(self.sim.blocks[12])
        b[3] = 30
        self.sim.blocks[12] = bytes(b)
        with self.assertRaises(ValueError):
            preview(self.capture(), 'l1_supply_max', 29)

    def test_wrong_firmware(self):
        b = bytearray(self.sim.blocks[1])
        b[8] = 214
        self.sim.blocks[1] = bytes(b)
        with self.assertRaises(ValueError):
            preview(self.capture(), 'dhw_setpoint', 60)

    def test_stale(self):
        approved = preview(self.snapshot, 'dhw_setpoint', 60)
        b = bytearray(self.sim.blocks[16])
        b[2] ^= 1
        self.sim.blocks[16] = bytes(b)
        with self.assertRaises(ValueError):
            self.apply(approved)

    def test_identity_change(self):
        approved = preview(self.snapshot, 'dhw_setpoint', 60)
        b = bytearray(self.sim.blocks[1])
        b[0] ^= 1
        self.sim.blocks[1] = bytes(b)
        with self.assertRaises(ValueError):
            self.apply(approved)

    def test_noop(self):
        p = preview(self.snapshot, 'dhw_setpoint', 60)
        self.assertFalse(self.apply(preview(self.snapshot, p.key, p.old)))
        self.assertFalse(self.safety.exists())

    def test_backup_failure(self):
        p = preview(self.snapshot, 'dhw_setpoint', 60)
        with patch('ouman_eh203.bench_parameter.acquire', side_effect=OSError('disk')):
            with self.assertRaises(OSError):
                self.apply(p)
        self.assertFalse(self.journal.exists())

    def test_uncertain_ack(self):
        p = preview(self.snapshot, 'dhw_setpoint', 60)
        self.sim.write_fault = 'ack'
        self.allowed_writes = 1
        with self.assertRaises(ValueError):
            self.apply(p)
        self.assertEqual(load(self.journal)['status'], 'write_outcome_unknown')

    def test_readback_mismatch(self):
        p = preview(self.snapshot, 'dhw_setpoint', 60)
        self.sim.write_fault = 'readback'
        self.allowed_writes = 1
        with self.assertRaises(ValueError):
            self.apply(p)
        self.assertEqual(load(self.journal)['status'], 'write_outcome_unknown')

    def test_confirmation_and_modified_preview(self):
        p = preview(self.snapshot, 'dhw_setpoint', 60)
        with patch('ouman_eh203.bench_parameter.open_serial') as opened:
            with self.assertRaises(ValueError):
                execute_bench('/dev/test', self.snapshot, p, self.safety, self.journal,
                              confirmation='')
            with self.assertRaises(ValueError):
                execute_bench('/dev/test', self.snapshot, replace(p, pid=12),
                              self.safety, self.journal, confirmation='BENCH')
            opened.assert_not_called()


    def apply_draft(self, approved, settle=lambda: None, phase=None):
        with patch('ouman_eh203.backup.time.sleep'):
            return _apply_draft(self.sim, approved, self.safety, self.journal,
                                settle=settle, phase=phase)

    def test_draft_groups_same_block_and_verifies_final_capture(self):
        p = draft_preview(self.snapshot, {'l1_supply_min': 20, 'l1_supply_max': 65,
                                         'dhw_setpoint': '58.9', 'l1_room_setpoint': '22.0'})
        self.assertEqual(len(p.changes), 4)
        self.assertEqual([step[0] for step in p.steps], [12,13,16])
        self.assertEqual(dict(p.after)[12][3:5], bytes([20,65]))
        self.assertEqual(dict(p.after)[12][:3], dict(p.before)[12][:3])
        self.assertEqual(dict(p.after)[12][5:], dict(p.before)[12][5:])
        self.assertFalse(self.sim.writes)
        self.allowed_writes = 3
        waits = []
        result = self.apply_draft(p, lambda: waits.append(True))
        self.assertTrue(verify_file(result))
        self.assertEqual(len(waits), 3)
        self.assertEqual([tx[4] for tx in self.sim.writes if tx[1]==0x82], [12,13,16])
        self.assertEqual(dict(p.after)[12], self.sim.blocks[12])
        self.assertEqual(dict(p.after)[16], self.sim.blocks[16])
        journal = load(self.journal)
        self.assertEqual(journal['status'], 'complete')
        self.assertEqual([e['status'] for e in journal['entries']], ['verified']*3)
        self.assertFalse(journal['persistence_verified'])
        self.assertEqual(load(journal['after_capture']), result)

    def test_draft_validates_combined_min_max(self):
        with self.assertRaises(ValueError):
            draft_preview(self.snapshot, {'l1_supply_min': 50, 'l1_supply_max': 45})
        p = draft_preview(self.snapshot, {'l1_supply_min': 65, 'l1_supply_max': 80})
        self.assertEqual(len(p.steps), 1)
        self.assertFalse(self.sim.writes)

    def test_draft_invalid_field_and_resolution(self):
        for values in ({'dhw_boost': 5}, {'dhw_setpoint': '58.01'},
                       {'l1_supply_min': 4}, {'dhw_setpoint': 'NaN'}):
            with self.assertRaises(ValueError):
                draft_preview(self.snapshot, values)

    def test_draft_partial_failure_stops_remaining_writes(self):
        p = draft_preview(self.snapshot, {'l1_supply_max': 65, 'l1_room_setpoint': 22,
                                         'dhw_setpoint': 59})
        def settle():
            self.sim.write_fault = 'ack'
        self.allowed_writes = 2
        with self.assertRaises(ValueError):
            self.apply_draft(p, settle)
        journal = load(self.journal)
        self.assertEqual(journal['status'], 'interrupted')
        self.assertEqual([e['status'] for e in journal['entries']],
                         ['verified','write_outcome_unknown','not_started'])
        self.assertEqual(self.sim.blocks[16], dict(p.before)[16])

    def test_draft_stale_and_backup_failure(self):
        p = draft_preview(self.snapshot, {'dhw_setpoint': 59})
        with patch('ouman_eh203.bench_parameter.acquire', side_effect=OSError('disk')):
            with self.assertRaises(OSError):
                self.apply_draft(p)
        self.assertFalse(self.journal.exists())
        self.sim.blocks[16] = dict(p.after)[16]
        with self.assertRaises(ValueError):
            self.apply_draft(p)

    def test_draft_noop_and_modified_preview(self):
        p = draft_preview(self.snapshot, {})
        self.assertIsNone(self.apply_draft(p))
        self.assertFalse(self.safety.exists())
        p = draft_preview(self.snapshot, {'dhw_setpoint': 59})
        with patch('ouman_eh203.bench_parameter.open_serial') as opened:
            with self.assertRaises(ValueError):
                execute_draft('/dev/test', self.snapshot, p, self.safety, self.journal,
                              confirmation='')
            with self.assertRaises(ValueError):
                execute_draft('/dev/test', self.snapshot, replace(p, steps=()),
                              self.safety, self.journal, confirmation='BENCH')
            opened.assert_not_called()


    def test_draft_reports_phases_in_write_order(self):
        p = draft_preview(self.snapshot, {'l1_supply_max': 65, 'dhw_setpoint': '58.9'})
        events = []
        self.allowed_writes = 2
        self.apply_draft(p, phase=lambda name, pid: events.append((name, pid)))
        self.assertEqual(events, [
            ('check', 0), ('backup', 0), ('check', 0),
            ('check_step', 12), ('write', 12), ('settle', 12),
            ('readback', 12), ('verified', 12),
            ('check_step', 16), ('write', 16), ('settle', 16),
            ('readback', 16), ('verified', 16),
            ('final_check', 0), ('final_capture', 0),
        ])


    def test_expanded_heating_draft_groups_and_preserves_bytes(self):
        values = {'l1_room_gain': '3.5', 'l1_night_reduction': 4,
                  'l1_parallel_shift': -2, 'l1_autumn_drying': 3,
                  'l2_supply_min': 20, 'l2_supply_max': 65,
                  'l2_night_reduction': 5, 'l2_parallel_shift': -3,
                  'l2_autumn_drying': 4}
        p = draft_preview(self.snapshot, values)
        self.assertEqual(len(p.changes), 9)
        self.assertEqual([step[0] for step in p.steps], [12, 14])
        before, after = dict(p.before), dict(p.after)
        for pid, offsets in ((12, {5: 4, 7: 35, 14: 3, 27: 254}),
                             (14, {3: 20, 4: 65, 5: 5, 9: 4, 23: 253})):
            expected = bytearray(before[pid])
            for offset, raw in offsets.items():
                expected[offset] = raw
            self.assertEqual(after[pid], bytes(expected))
        self.assertEqual({i for i in before if before[i] != after[i]}, {12, 14, 65, 66})
        for pid, raw in ((65, 254), (66, 253)):
            self.assertEqual(after[pid], before[pid][:9]+bytes([raw])+before[pid][10:])
        self.allowed_writes = 2
        result = self.apply_draft(p)
        self.assertTrue(verify_file(result))
        self.assertEqual([tx[4] for tx in self.sim.writes if tx[1] == 0x82], [12, 14])
        self.assertEqual(self.sim.blocks[12], after[12])
        self.assertEqual(self.sim.blocks[14], after[14])
        self.assertEqual(self.sim.blocks[65], after[65])
        self.assertEqual(self.sim.blocks[66], after[66])
        self.assertEqual(load(self.journal)['status'], 'complete')

    def test_expanded_heating_limits_and_resolution(self):
        for values in ({'l1_room_gain': '7.1'}, {'l1_room_gain': '3.55'},
                       {'l2_supply_min': 4}, {'l2_supply_max': 96},
                       {'l1_night_reduction': 36}, {'l2_night_reduction': -1},
                       {'l1_parallel_shift': -16}, {'l2_parallel_shift': 15.5},
                       {'l1_autumn_drying': 16}, {'l2_autumn_drying': -1},
                       {'l2_room_setpoint': 21}, {'l1_outdoor_delay': 4}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                draft_preview(self.snapshot, values)
        self.assertFalse(self.sim.writes)

    def test_l2_min_max_dependency_and_cross_circuit_order(self):
        with self.assertRaises(ValueError):
            draft_preview(self.snapshot, {'l2_supply_min': 60, 'l2_supply_max': 50})
        p = draft_preview(self.snapshot, {'l2_supply_min': 65, 'l2_supply_max': 80,
                                         'l1_room_setpoint': 22, 'dhw_setpoint': 59,
                                         'l1_parallel_shift': 2})
        self.assertEqual([s[0] for s in p.steps], [12, 13, 16, 14])
        self.assertEqual(dict(p.after)[14][3:5], bytes([65,80]))
        self.assertFalse(self.sim.writes)


    def test_shift_mirror_is_in_next_step_and_final_state(self):
        p = draft_preview(self.snapshot, {'l1_parallel_shift': -5, 'l2_parallel_shift': -4,
                                         'l1_room_setpoint': 23})
        self.assertEqual([s[0] for s in p.steps], [12,13,14])
        self.assertEqual(dict(p.steps[0][2])[65][9], 0xfb)
        self.assertEqual(dict(p.steps[1][1])[65][9], 0xfb)
        self.assertEqual(dict(p.after)[66][9], 0xfc)
        self.allowed_writes = 3
        self.apply_draft(p)
        self.assertEqual(self.sim.blocks[65][9], 0xfb)
        self.assertEqual(self.sim.blocks[66][9], 0xfc)

    def test_unexpected_mirror_byte_still_stops_transaction(self):
        p = draft_preview(self.snapshot, {'l1_parallel_shift': -5, 'dhw_setpoint': 59})
        self.sim.write_fault = 'extra_mirror_byte'
        self.allowed_writes = 1
        with self.assertRaises(ValueError):
            self.apply_draft(p)
        entries = load(self.journal)['entries']
        self.assertEqual([e['status'] for e in entries],
                         ['write_outcome_unknown', 'not_started'])
        self.assertEqual(self.sim.blocks[16], dict(p.before)[16])

    def test_initial_mirror_mismatch_blocks_shift(self):
        b = bytearray(self.sim.blocks[65])
        b[9] = 1
        self.sim.blocks[65] = bytes(b)
        with self.assertRaises(ValueError):
            draft_preview(self.capture(), {'l1_parallel_shift': -5})
