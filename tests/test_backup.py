"""Tests for strictly read-only full ID backup and comparison."""
import sys
import tempfile
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research" / "scripts"))
from backup import acquire, classify, compare, digest, known_fields, request, verify_file, read_exact


class FakeSerial:
    port = '/dev/fake'

    def __init__(self):
        self.out = b''
        self.remaining = None

    def reset_input_buffer(self):
        pass

    def write(self, data):
        if data[1] != 0x81:
            raise AssertionError('Backup emitted a non-read command')
        self.out = data
        self.remaining = None
        return len(data)

    def flush(self):
        pass

    def read(self, n):
        pid = self.out[4]
        if pid == 1:
            data = (10004680).to_bytes(4, 'little') + b'203' + bytes([0, 215])
            payload = bytes((0, pid)) + data
        elif pid == 12:
            data = bytearray(31)
            data[7] = 50
            payload = bytes((0, pid)) + data
        elif pid in (13, 14, 16, 44, 47, 65, 66):
            payload = bytes((0, pid)) + bytes(31)
        else:
            payload = b'\x00\xff'
        frame_body = bytes((2 if pid != 0 else 1, len(payload))) + payload
        frame = b'\x02' + frame_body + bytes((sum(frame_body) & 255,))
        if self.remaining is None:
            self.remaining = frame[3:]
            return frame[:3]
        result, self.remaining = self.remaining[:n], self.remaining[n:]
        return result


class BackupTests(unittest.TestCase):
    def test_request_is_canonical_read_only(self):
        self.assertEqual(request(18).hex(), '028102001295')
        self.assertEqual(request(255).hex(), '02810200ff82')
        with self.assertRaises(ValueError):
            request(256)

    def test_classification(self):
        self.assertEqual(classify(bytes.fromhex('02010200ff02'), 0)[0], 'rejected')
        self.assertEqual(classify(bytes.fromhex('0202040012fe667c'), 18)[0], 'accepted')
        self.assertEqual(classify(bytes.fromhex('0202040012fe6600'), 18)[0], 'invalid')

    def test_full_capture_export_and_comparison(self):
        with tempfile.TemporaryDirectory() as d:
            a = acquire(FakeSerial(), Path(d) / 'a.json', 0)
            b = acquire(FakeSerial(), Path(d) / 'b.json', 0)
            self.assertTrue(verify_file(a))
            self.assertTrue(verify_file(b))
            self.assertEqual(len(a['records']), 256)
            self.assertEqual(len(known_fields(a)['fields']), 82)
            self.assertEqual(known_fields(a)['fields']['l1_room_gain']['value'], '5.0')
            self.assertEqual(compare(a, b)['status'], 'exact_payload_match')

            # Simulate one changed parameter and update frame SUM8.
            rx = bytearray.fromhex(b['records']['12']['rx'])
            rx[12] = 49
            rx[-1] = sum(rx[1:-1]) & 255
            b['records']['12']['rx'] = rx.hex(' ').upper()
            b['records']['12']['data'] = rx[5:-1].hex(' ').upper()
            b['records_sha256'] = digest(b['records'])
            report = compare(a, b)
            self.assertEqual(report['status'], 'settings_changed')
            self.assertEqual(report['raw_payload_differences']['12']['changed_data_offsets'], [7])
            self.assertEqual(report['known_field_changes']['l1_room_gain']['after'], '4.9')

            b['records']['12']['rx'] = '00'
            b['records_sha256'] = digest(b['records'])
            with self.assertRaises(ValueError):
                verify_file(b)

    def test_tamper_detected(self):
        with tempfile.TemporaryDirectory() as d:
            a = acquire(FakeSerial(), Path(d) / 'a.json', 0)
            a['records']['1']['rx'] = ''
            with self.assertRaises(ValueError):
                verify_file(a)

    def test_existing_file_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'existing.json'
            path.write_text('leave me alone', encoding='utf-8')
            with self.assertRaises(FileExistsError):
                acquire(FakeSerial(), path, 0)
            self.assertEqual(path.read_text(encoding='utf-8'), 'leave me alone')

    def test_partial_read(self):
        class Partial:
            def __init__(self):
                self.parts = [b'\x02', b'\x01\x02', b'']

            def read(self, n):
                return self.parts.pop(0)
        self.assertEqual(read_exact(Partial(), 3), b'\x02\x01\x02')

    def test_missing_bytes_is_invalid(self):
        self.assertEqual(classify(b'\x02\x02\x04', 18)[0], 'invalid')
