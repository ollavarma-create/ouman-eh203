import unittest
from ouman_eh203.schedules import decode_pair, semantic_key

class ScheduleTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(decode_pair(bytes(31),bytes(31),4),[])
    def test_midnight(self):
        e=bytearray(31); e[0]=1; e[14]=16
        self.assertEqual(decode_pair(bytes(31),e,4),[(0,1,16)])
    def test_cross_pair(self):
        a={i:bytes(31) for i in range(4,10)}
        e=bytearray(31); e[0]=1; e[14]=16
        b=dict(a); a[5]=bytes(e); b[7]=bytes(e)
        self.assertEqual(semantic_key(a),semantic_key(b))
    def test_conflict_order(self):
        a={i:bytes(31) for i in range(4,10)}
        e=bytearray(31); e[:2]=b'\x01\x01'; e[14:16]=b'\x10\x20'
        a[5]=bytes(e); b=dict(a); e[14:16]=b'\x20\x10'; b[5]=bytes(e)
        self.assertNotEqual(semantic_key(a),semantic_key(b))
