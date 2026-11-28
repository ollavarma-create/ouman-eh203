import unittest
from ouman_eh203.curves import decode_curve

class CurveTests(unittest.TestCase):
    def test_five(self):
        curve = decode_curve(bytes([0,38,34,25,22,20,244,254,10])+bytes(22))
        self.assertEqual(curve.active, ((-20,38),(-12,34),(-2,25),(10,22),(20,20)))
    def test_three(self):
        curve = decode_curve(bytes([1,38,34,25,22,20,244,254,10])+bytes(22))
        self.assertEqual(curve.active, ((-20,38),(0,25),(20,20)))
        self.assertEqual(len(curve.stored),5)
    def test_invalid(self):
        for data in (b"",bytes([2])+bytes(30),bytes(31)):
            with self.assertRaises(ValueError):
                decode_curve(data)
