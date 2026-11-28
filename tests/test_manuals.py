import os
import tempfile
import unittest
from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QPdfWriter, QPainter
    from ouman_eh203.manuals import ManualManager, validate_url
except ImportError:
    QApplication = None

@unittest.skipIf(QApplication is None, "Install optional gui extra")
class ManualTests(unittest.TestCase):
    def test_urls(self):
        self.assertEqual(validate_url("https://example.org/a.pdf"), "https://example.org/a.pdf")
        for url in ("http://example.org/a.pdf", "file:///tmp/a.pdf", "https://user@example.org"):
            with self.assertRaises(ValueError):
                validate_url(url)

    def test_install_preserves_valid_copy(self):
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.pdf"
            writer = QPdfWriter(str(source))
            painter = QPainter(writer)
            painter.drawText(100, 100, "Test manual")
            painter.end()
            del painter, writer
            manager = ManualManager(Path(directory) / "manuals")
            data = source.read_bytes()
            pages, digest = manager.install("fi", data)
            self.assertEqual(pages, 1)
            self.assertEqual(len(digest), 64)
            with self.assertRaises(ValueError):
                manager.install("fi", b"invalid")
            self.assertEqual(manager.path("fi").read_bytes(), data)
            self.assertEqual(manager.inspect(manager.path("fi")), (pages, digest))

    def test_acquisition_worker_lifecycle(self):
        from PySide6.QtCore import QSettings, QEventLoop, QTimer
        from ouman_eh203.manual_gui import ManualSettings
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.pdf"
            writer = QPdfWriter(str(source))
            painter = QPainter(writer)
            painter.drawText(100, 100, "Test manual")
            painter.end()
            del painter, writer
            settings = QSettings(str(Path(directory) / "settings.ini"), QSettings.Format.IniFormat)
            dialog = ManualSettings(settings, "en", directory=Path(directory) / "manuals")
            dialog.start("en", str(source), False)
            worker = dialog.worker
            loop = QEventLoop()
            worker.finished.connect(loop.quit)
            QTimer.singleShot(5000, loop.quit)
            loop.exec()
            if dialog.worker is not None:
                worker.wait()
                app.processEvents()
            self.assertIsNone(dialog.worker)
            self.assertTrue(all(widget.isEnabled() for widget in dialog.controls))
            self.assertEqual(dialog.manager.path("en").read_bytes(), source.read_bytes())
            self.assertEqual(dialog.status.text(), "Saved.")
            dialog.close()
