import unittest
from ouman_eh203.simulator import SimulatedSerial
from ouman_eh203.protocol import request, write_frame, decode
from ouman_eh203.transport import exchange

def fixture():
    curve=bytes((1,58,50,41,28,18,246,0,10))+bytes(22)
    a=bytearray(31); a[20]=5
    b=bytearray(31); b[16]=5
    routing=bytearray(31); routing[17]=99
    return SimulatedSerial({12:a,14:b,17:routing,43:bytes(2),65:curve,66:curve,95:bytes(31)})

class SimulatorTests(unittest.TestCase):
    def setUp(self):
        self.s=fixture()
    def read(self,pid,size):
        return decode(exchange(self.s,request(pid)),pid,size)
    def write(self,pid,data):
        return decode(exchange(self.s,write_frame(pid,data)),pid,0)
    def test_mode_and_curve_mirror(self):
        a=self.read(65,31)
        self.write(65,bytes(1)+a[1:])
        self.assertEqual(self.read(66,31)[0],0)
        a=bytearray(self.read(65,31)); a[3]=25
        self.write(65,a)
        self.assertEqual(self.read(12,31)[:3],bytes((58,25,18)))
        self.s.reboot()
        self.assertEqual(self.read(65,31)[3],25)
        self.s.factory_reset()
        self.assertEqual(self.read(65,31)[0],1)
    def test_room_delay(self):
        a=bytearray(self.read(12,31)); a[20]=15
        self.write(12,a)
        self.assertEqual(self.read(14,31)[16],15)
    def test_digital_routing(self):
        self.write(43,bytes((4,0)))
        self.assertEqual(self.read(17,31)[17],2)
    def test_gsm_rejected(self):
        with self.assertRaises(ValueError):
            self.write(95,bytes((1,))+bytes(30))
        self.assertEqual(self.read(95,31),bytes(31))
    def test_faults(self):
        for fault in ('timeout','checksum','truncate','reject'):
            with self.subTest(fault=fault):
                self.s.fault=fault
                with self.assertRaises(ValueError):
                    self.read(65,31)
    def test_lost_ack_does_not_imply_no_write(self):
        a=self.read(65,31)
        self.s.fault='timeout'
        with self.assertRaises(ValueError):
            self.write(65,bytes(1)+a[1:])
        self.assertEqual(self.read(65,31)[0],0)
