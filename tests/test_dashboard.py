import os
import unittest
from datetime import datetime, timezone, timedelta
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QCoreApplication, QEvent
    from ouman_eh203.dashboard import Dashboard, reading_state
except ImportError:
    QApplication = None

@unittest.skipIf(QApplication is None, "Install optional gui extra")
class DashboardTests(unittest.TestCase):
    def test_states(self):
        now = datetime.now(timezone.utc)
        self.assertEqual(reading_state(None, True, now), "waiting")
        self.assertEqual(reading_state((0, now.isoformat()), True, now), "live")
        self.assertEqual(reading_state((None, now.isoformat()), True, now), "missing")
        self.assertEqual(reading_state((20, now.isoformat()), False, now), "stale")
        self.assertEqual(reading_state((20, (now-timedelta(seconds=11)).isoformat()), True, now), "stale")

    def test_dashboard(self):
        app = QApplication.instance() or QApplication([])
        widget = Dashboard()
        try:
            widget.translate("fi")
            widget.begin()
            widget.update_sample(18, -4.1, datetime.now(timezone.utc).isoformat())
            self.assertEqual(widget.rows[18][1].text(), "-4.10 °C")
            self.assertEqual(widget.rows[18][2].text(), "Ajantasainen")
            self.assertEqual(widget.rows["dhw_temp"][2].text(), "Ei toteutettu")
            widget.end()
            self.assertEqual(widget.rows[18][2].text(), "Vanhentunut")
        finally:
            widget.close()
            widget.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            app.processEvents()
