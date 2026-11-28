import os
import tempfile
import unittest
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QSettings
except ImportError:
    QApplication = None

@unittest.skipIf(QApplication is None, "Install optional gui extra")
class GuiTests(unittest.TestCase):
    def test_simulator_probe(self):
        from ouman_eh203.gui import probe
        self.assertEqual(probe("", True), "44 45 4d 4f")

    def test_window(self):
        from ouman_eh203.gui import Window
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            settings = QSettings(directory + "/test.ini", QSettings.Format.IniFormat)
            window = Window(settings)
            self.assertEqual(window.tabs.count(), 3)
            self.assertEqual(window.tabs.tabText(2), "Heating curves")
            self.assertFalse(window.port.isEnabled())
            self.assertFalse(window.backup_button.isEnabled())
            window.language.setCurrentText("fi")
            self.assertEqual(window.tabs.tabText(0), "Käytönvalvonta")
            self.assertEqual(window.tabs.tabText(2), "Lämmityskäyrät")
            window.mode.setCurrentIndex(1)
            self.assertTrue(window.port.isEnabled())
            self.assertTrue(window.backup_button.isEnabled())
            window.close()
