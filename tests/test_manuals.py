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
