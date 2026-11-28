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

    def test_simulation_configuration_lifecycle(self):
        from pathlib import Path
        from ouman_eh203.gui import Window
        from ouman_eh203.parameter_edit import proposal
        from ouman_eh203.scenario import encode
        from ouman_eh203.backup import atomic_json
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            window = Window(QSettings(directory + "/test.ini", QSettings.Format.IniFormat))
            source = Path(__file__).parent / 'fixtures/eh203_215/factory_reset_pass1.json'
            window.mode.setCurrentIndex(2)
            self.assertTrue(window.open_configuration_path(source))
            self.assertEqual(window.offline.table.rowCount(),82)
            self.assertFalse(window.dirty())
            pid, before, after = proposal(window.snapshot_sim,'dhw_setpoint','61.1')
            window.snapshot_sim.blocks[pid] = after
            window.reset_status()
            self.assertTrue(window.dirty())
            self.assertTrue(window.windowTitle().endswith('*'))
            self.assertIn('Unsaved changes',window.snapshot_label.text())
            self.assertEqual(window.offline.fields['dhw_setpoint']['value'],'61.1')
            self.assertFalse(window.offline.compare_button.isEnabled())
            path = Path(directory)/'scenario.json'
            atomic_json(path,encode(window.snapshot,window.snapshot_sim))
            window.saved_blocks = dict(window.snapshot_sim.blocks)
            self.assertTrue(window.open_configuration_path(path))
            self.assertEqual(window.offline.fields['dhw_setpoint']['value'],'61.1')
            self.assertFalse(window.dirty())
            window.mode.setCurrentIndex(1)
            self.assertIsNone(window.offline.snapshot)
            self.assertEqual(window.offline.table.rowCount(),0)
            window.close()
            window.deleteLater()
            from PySide6.QtCore import QCoreApplication, QEvent
            QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
