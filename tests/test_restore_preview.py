import copy
import unittest
from pathlib import Path
from unittest.mock import patch
from ouman_eh203.backup import load
from ouman_eh203.restore_preview import preview

class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.snap = load(Path(__file__).parent / "fixtures/eh203_215/factory_reset_pass1.json")

    def test_identical(self):
        original = copy.deepcopy(self.snap)
        report = preview(self.snap,self.snap)
        self.assertEqual(report["steps"],[])
        self.assertEqual(len(report["fields"]),82)
        self.assertEqual(self.snap,original)

    def test_unvalidated_profile(self):
        with patch("ouman_eh203.restore_preview.block_identity",side_effect=[b"abcd203\x00\xd7",b"abcd203\x00\xd8"]), patch("ouman_eh203.restore_preview.plan") as planner:
            report = preview(self.snap,self.snap)
            self.assertTrue(report["firmware_mismatch"])
            self.assertEqual(report["steps"],[])
            self.assertEqual(len(report["excluded_ids"]),256)
            planner.assert_not_called()

    def test_incomplete(self):
        bad = copy.deepcopy(self.snap)
        bad["complete"] = False
        with self.assertRaises(ValueError):
            preview(self.snap,bad)
