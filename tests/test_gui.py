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

    def test_configuration_workflow_modes(self):
        from pathlib import Path
        from ouman_eh203.gui import Window
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            window = Window(QSettings(directory + "/test.ini", QSettings.Format.IniFormat))
            try:
                self.assertTrue(window.backup_group.isHidden())
                self.assertTrue(window.write_group.isHidden())
                self.assertTrue(window.use_backup_button.isHidden())
                window.mode.setCurrentIndex(1)
                self.assertFalse(window.backup_group.isHidden())
                self.assertFalse(window.write_group.isHidden())
                self.assertTrue(window.edit_button.isHidden())
                self.assertFalse(window.bench_edit_button.isHidden())
                self.assertTrue(window.bench_edit_button.isEnabled())
                self.assertIn('automatically', window.config.text())
                self.assertEqual(window.live_button.text(), 'Start monitoring')
                window.language.setCurrentText('fi')
                self.assertEqual(window.live_button.text(), 'Käynnistä valvonta')
                self.assertIn('automaattisesti', window.config.text())
                window.port.clear()
                self.assertFalse(window.backup_button.isEnabled())
                self.assertFalse(window.bench_edit_button.isEnabled())
                self.assertFalse(window.offline.restore_button.isEnabled())
                window.port.setText('/dev/ttyUSB0')
                fixture = Path(__file__).parent / 'fixtures/eh203_215/factory_reset_pass1.json'
                self.assertTrue(window.open_configuration_path(fixture))
                self.assertFalse(window.use_backup_button.isHidden())
                self.assertTrue(window.load_snapshot(fixture))
                self.assertTrue(window.backup_group.isHidden())
                self.assertTrue(window.bench_edit_button.isHidden())
                self.assertFalse(window.edit_button.isHidden())
                self.assertTrue(window.edit_button.isEnabled())
                self.assertTrue(window.use_backup_button.isHidden())
            finally:
                window.close()
                window.deleteLater()

    def test_configuration_blocked_while_monitoring(self):
        from pathlib import Path
        from ouman_eh203.gui import Window
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            window = Window(QSettings(directory + "/test.ini", QSettings.Format.IniFormat))
            try:
                window.mode.setCurrentIndex(1)
                fixture = Path(__file__).parent / 'fixtures/eh203_215/factory_reset_pass1.json'
                self.assertTrue(window.open_configuration_path(fixture))
                # Simulate ownership without starting a real serial worker.
                window.session = object()
                window.backup_enabled()
                self.assertFalse(window.backup_button.isEnabled())
                self.assertFalse(window.bench_edit_button.isEnabled())
                self.assertFalse(window.offline.restore_button.isEnabled())
                self.assertIn('Stop monitoring', window.config.text())
                self.assertTrue(window.offline.compare_path(fixture))
                self.assertFalse(window.offline.restore_button.isEnabled())
                window.session = None
                window.backup_enabled()
                self.assertTrue(window.bench_edit_button.isEnabled())
                self.assertTrue(window.offline.restore_button.isEnabled())
            finally:
                window.session = None
                window.close()
                window.deleteLater()

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
