import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"research"/"scripts"))
from write_parameter import frame, decode, patch, raw_value

class WriterTests(unittest.TestCase):
    def test_ack_headers(self):
        for s in ("020602000d15","021602000d25","022e02000c3c"):
            b=bytes.fromhex(s)
            self.assertEqual(decode(b,b[4],0),b"")
    def test_reject(self):
        with self.assertRaises(ValueError):
            decode(bytes.fromhex("02010200ff02"),12,0)
    def test_bad_checksum(self):
        with self.assertRaises(ValueError):
            decode(bytes.fromhex("022e02000c00"),12,0)
    def test_patch(self):
        b=bytes.fromhex("2619140f320000310a1e050f46fa0200640000020500010000001900000000")
        c=patch(b,7,1,49,50)
        self.assertEqual(c[:7]+c[8:],b[:7]+b[8:])
        self.assertEqual(c[7],50)
        self.assertEqual(frame(0x82,12,b).hex(),"028221000c"+b.hex()+"77")
    def test_wrong_expected(self):
        with self.assertRaises(ValueError):
            patch(bytes(31),7,1,49,50)
    def test_range(self):
        self.assertEqual(raw_value("4.9",49,50),49)
        for v in ("4.8","4.99","NaN","Infinity"):
            with self.assertRaises(ValueError):
                raw_value(v,49,50)
