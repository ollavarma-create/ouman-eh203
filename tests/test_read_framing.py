"""Run with: python -m unittest discover -s tests"""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research" / "scripts"))
from scan import read_request, check_response

class FramingTests(unittest.TestCase):
    def test_request(self):
        self.assertEqual(read_request(18).hex(), "028102001295")

    def test_outdoor_negative(self):
        self.assertTrue(check_response(bytes.fromhex("02 02 04 00 12 FE 66 7C")))

    def test_reject(self):
        self.assertTrue(check_response(bytes.fromhex("02 01 02 00 FF 02")))

    def test_checksum_error(self):
        self.assertFalse(check_response(bytes.fromhex("02 02 04 00 12 FE 66 00")))

if __name__ == "__main__":
    unittest.main()
