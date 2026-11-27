import unittest
from ouman_eh203.protocol import request, classify, write_frame, decode
from ouman_eh203.registry import FIELDS, QUICK_IDS

class CoreProtocolTests(unittest.TestCase):
    def test_request(self):
        self.assertEqual(request(16),bytes.fromhex('02 81 02 00 10 93'))
    def test_rejection(self):
        self.assertEqual(classify(bytes.fromhex('02 01 02 00 ff 02'),95)[0],'rejected')
    def test_ack(self):
        self.assertEqual(decode(bytes.fromhex('02 02 02 00 0c 10'),12,0),b'')
    def test_corrupt(self):
        with self.assertRaises(ValueError):
            decode(bytes.fromhex('02 02 02 00 0c 11'),12,0)
    def test_write(self):
        self.assertEqual(write_frame(43,b'\x04\x00'),bytes.fromhex('02 82 04 00 2b 04 00 b5'))
    def test_registry(self):
        self.assertEqual(len(FIELDS),82)
        self.assertEqual(len(set(QUICK_IDS)),72)
        self.assertEqual(len({f[0] for f in FIELDS}),82)
