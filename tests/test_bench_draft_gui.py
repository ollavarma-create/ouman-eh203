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
