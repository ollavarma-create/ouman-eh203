import os
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PySide6.QtWidgets import QApplication
except ImportError:
    QApplication = None


@unittest.skipIf(QApplication is None, 'Install optional gui extra')
class BenchDraftGuiTests(unittest.TestCase):
    def test_local_edit_validation_and_discard(self):
        from ouman_eh203.backup import load
        from ouman_eh203.bench_parameter_gui import BenchParameterDialog
        app = QApplication.instance() or QApplication([])
        dialog = BenchParameterDialog('/dev/test', 'en')
        try:
            snapshot = load(Path(__file__).parent/'fixtures/eh203_215/factory_reset_pass1.json')
            dialog.set_snapshot(snapshot)
            self.assertFalse(dialog.apply_button.isEnabled())
            with patch('ouman_eh203.bench_parameter_gui.QInputDialog.getText',
                       return_value=('58.9', True)):
                dialog.edit('dhw_setpoint')
            self.assertTrue(dialog.apply_button.isEnabled())
            self.assertEqual(len(dialog.approved.steps), 1)
            self.assertIsNone(dialog.worker)
            with patch('ouman_eh203.bench_parameter_gui.QInputDialog.getText',
                       return_value=('80', True)):
                dialog.edit('l1_supply_min')
            self.assertFalse(dialog.apply_button.isEnabled())
            dialog.discard()
            self.assertFalse(dialog.dirty())
            self.assertFalse(dialog.apply_button.isEnabled())
            self.assertEqual(dialog.original, dialog.values)
        finally:
            dialog.discard()
            dialog.close()
            dialog.deleteLater()


    def test_expanded_circuit_labels_and_independent_draft(self):
        from ouman_eh203.backup import load
        from ouman_eh203.bench_parameter import DRAFT_KEYS
        from ouman_eh203.bench_parameter_gui import BenchParameterDialog
        app = QApplication.instance() or QApplication([])
        dialog = BenchParameterDialog('/dev/test', 'fi')
        try:
            snapshot = load(Path(__file__).parent/'fixtures/eh203_215/factory_reset_pass1.json')
            dialog.set_snapshot(snapshot)
            self.assertEqual(dialog.table.rowCount(), 13)
            for key, circuit in (('l1_supply_min', 'L1'), ('l2_supply_min', 'L2'),
                                 ('dhw_setpoint', 'LV')):
                row = DRAFT_KEYS.index(key)
                self.assertEqual(dialog.table.item(row, 0).text(), circuit)
                self.assertIn(circuit, dialog.pencils[key].accessibleName())
            with patch('ouman_eh203.bench_parameter_gui.QInputDialog.getText',
                       return_value=('-3', True)):
                dialog.edit('l2_parallel_shift')
            self.assertTrue(dialog.apply_button.isEnabled())
            self.assertEqual([s[0] for s in dialog.approved.steps], [14])
            self.assertEqual(dialog.original['l1_parallel_shift'], dialog.values['l1_parallel_shift'])
            self.assertIsNone(dialog.worker)
            with patch('ouman_eh203.bench_parameter_gui.QInputDialog.getText',
                       return_value=('4.5', True)):
                dialog.edit('l1_room_gain')
            self.assertTrue(dialog.apply_button.isEnabled())
            self.assertEqual([s[0] for s in dialog.approved.steps], [12,14])
        finally:
            dialog.discard()
            dialog.close()
            dialog.deleteLater()
