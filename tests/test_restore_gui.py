import os
import tempfile
import unittest
from unittest.mock import patch
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QCoreApplication, QEvent
except ImportError:
    QApplication = None

@unittest.skipIf(QApplication is None, "Install optional gui extra")
class RestoreGuiTests(unittest.TestCase):
    def setUp(self):
        from ouman_eh203.restore_gui import RestoreDialog
        self.app = QApplication.instance() or QApplication([])
        self.directory = tempfile.TemporaryDirectory()
        with patch("ouman_eh203.restore_gui.QStandardPaths.writableLocation", return_value=self.directory.name):
            self.dialog = RestoreDialog(None, "en")

    def tearDown(self):
        self.dialog.close()
        self.dialog.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.directory.cleanup()

    def test_filter(self):
        d = self.dialog
        d.fields = [("dhw_setpoint", 58, 60, "°C"), ("dhw_i_time", 18, 18, "s")]
        d.populate_fields()
        self.assertTrue(d.only_changes.isChecked())
        self.assertEqual(d.table.rowCount(), 1)
        d.only_changes.setChecked(False)
        self.assertEqual(d.table.rowCount(), 2)

    def test_clear_preview(self):
        d = self.dialog
        d.fields = [("dhw_setpoint", 58, 60, "°C")]
        d.technical_text = "66"
        d.technical.setEnabled(True)
        d.populate_fields()
        d.clear_preview()
        d.only_changes.setChecked(False)
        self.assertEqual(d.table.rowCount(), 0)
        self.assertFalse(d.technical.isEnabled())
        self.assertEqual(d.technical_text, "")
        self.assertEqual(d.fields, [])
