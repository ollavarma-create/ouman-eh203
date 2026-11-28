import os
import unittest
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QCoreApplication, QEvent
except ImportError:
    QApplication = None

@unittest.skipIf(QApplication is None, "Install optional gui extra")
class CurveEditorTests(unittest.TestCase):
    def setUp(self):
        from ouman_eh203.curves import HeatingCurve
        from ouman_eh203.curve_gui import CurveEditor
        self.app = QApplication.instance() or QApplication([])
        self.original = HeatingCurve(0, ((-20,57),(-8,51),(2,45),(12,35),(20,25)))
        self.editor = CurveEditor(self.original, -4.1, False)

    def tearDown(self):
        self.editor.close()
        self.editor.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def test_range_and_reset(self):
        d = self.editor
        d.fields[0][1].setValue(120)
        self.assertEqual(d.plot.draft.active[0][1],120)
        self.assertGreaterEqual(d.plot.bounds[1],120)
        self.assertIn("Write restriction",d.info.text())
        d.reset()
        self.assertEqual(d.plot.draft,self.original)
        self.assertTrue(d.within_test_bounds)

    def test_rising_warning(self):
        d = self.editor
        d.fields[2][1].setValue(30)
        self.assertIn("Warning:",d.info.text())
        self.assertIn("Estimate:",d.info.text())
        self.assertFalse(d.within_test_bounds)

    def test_invalid_order(self):
        d = self.editor
        d.fields[1][0].setValue(2)
        self.assertIn("Error:",d.info.text())
        self.assertNotIn("Estimate:",d.info.text())

    def test_three_point(self):
        from ouman_eh203.curves import HeatingCurve
        from ouman_eh203.curve_gui import CurveEditor
        d = CurveEditor(HeatingCurve(1,self.original.stored),0,True)
        try:
            self.assertEqual(len(d.fields),3)
            self.assertTrue(all(not a.isEnabled() for a,b in d.fields))
            self.assertIn("Kirjoitusrajoitus",d.info.text())
            d.fields[1][1].setValue(5)
            self.assertEqual(d.plot.draft.active[1],(0,5))
            d.reset()
            self.assertEqual(d.plot.draft.active,d.original.active)
        finally:
            d.close()
            d.deleteLater()
            QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
