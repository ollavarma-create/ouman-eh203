import os
import tempfile
import unittest
from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QCoreApplication,QEvent
except ImportError:
    QApplication = None

@unittest.skipIf(QApplication is None,"Install optional gui extra")
class OfflineTests(unittest.TestCase):
    def test_viewer(self):
        from ouman_eh203.offline_gui import OfflinePage
        app = QApplication.instance() or QApplication([])
        page = OfflinePage(lambda n: None)
        try:
            fixture = Path(__file__).parent / "fixtures/eh203_215/factory_reset_pass1.json"
            self.assertTrue(page.open_path(fixture))
            self.assertEqual(page.raw.rowCount(),256)
            self.assertGreater(page.table.rowCount(),0)
            self.assertTrue(page.compare_path(fixture))
            self.assertEqual(page.report["known_field_changes"],{})
            self.assertEqual(page.raw_diff.rowCount(),0)
            self.assertTrue(page.diff.isRowHidden(0))
            page.only_changes.setChecked(False)
            self.assertFalse(page.diff.isRowHidden(0))
            page.translate("fi")
            self.assertEqual(page.tabs.tabText(2),"Asetuserot")
            page.search.setText("not-a-real-parameter")
            self.assertTrue(page.table.isRowHidden(0))
            page.search.clear()
            self.assertFalse(page.table.isRowHidden(0))
            with tempfile.TemporaryDirectory() as d:
                bad = Path(d)/"bad.json"
                bad.write_text("{}")
                self.assertFalse(page.compare_path(bad))
                self.assertIsNone(page.report)
                self.assertEqual(page.diff.rowCount(),0)
                self.assertFalse(page.open_path(bad))
                self.assertEqual(page.table.rowCount(),0)
                self.assertEqual(page.raw.rowCount(),0)
        finally:
            page.close()
            page.deleteLater()
            QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
