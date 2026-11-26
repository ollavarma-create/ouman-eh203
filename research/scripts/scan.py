#!/usr/bin/env python3
"""Read-only Ouman EH-203 native serial sweep, no write commands.

pip install pyserial
python research/scripts/scan.py --port /dev/ttyUSB0 --start 0 --end 63 --output scan.json
"""
import argparse
import json
import time

def read_request(pid: int) -> bytes:
    if not 0 <= pid <= 255:
        raise ValueError("ID must be one byte")
    data = bytes((0x02, 0x81, 0x02, 0x00, pid))
    return data + bytes((sum(data[1:]) & 0xFF,))

def check_response(rx: bytes) -> bool:
    return (
        len(rx) >= 6
        and rx[0] == 0x02
        and len(rx) == rx[2] + 4
        and sum(rx[1:-1]) & 0xFF == rx[-1]
    )

def scan(port: str, baud: int, start: int, end: int, delay: float, output: str):
    import serial
    results = {}
    with serial.Serial(
        port, baud, timeout=1.0,
        rtscts=False, dsrdtr=False, xonxoff=False
    ) as ser:
        for pid in range(start, end + 1):
            tx = read_request(pid)
            ser.reset_input_buffer()
            t0 = time.monotonic()
            ser.write(tx)
            ser.flush()
            rx = ser.read(3)
            if len(rx) == 3 and rx[0] == 2:
                rx += ser.read(rx[2] + 1)
            elapsed = (time.monotonic() - t0) * 1000
            valid = check_response(rx)
            rejected = valid and rx[3:-1] == bytes((0, 255))
            echo_ok = valid and (rejected or rx[3:5] == bytes((0, pid)))
            results[str(pid)] = {
                "tx": tx.hex(" ").upper(),
                "rx": rx.hex(" ").upper(),
                "valid": bool(valid and echo_ok),
                "rejected": bool(rejected),
                "payload": rx[3:-1].hex(" ").upper() if valid else "",
                "response_ms": round(elapsed, 2),
            }
            status = "REJECTED" if rejected else "OK" if valid and echo_ok else "ERROR"
            print(f"ID {pid:3} | {status:8} | LEN={len(rx):3} | {rx.hex(' ').upper()}")
            time.sleep(delay)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        f.write("\n")
    print(f"Saved {output}")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="/dev/ttyUSB0")
    parser.add_argument("--baud", type=int, default=4800)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=63)
    parser.add_argument("--delay", type=float, default=0.25)
    parser.add_argument("--output", default="ouman_scan.json")
    args = parser.parse_args()
    if not 0 <= args.start <= args.end <= 255:
        parser.error("require 0 <= start <= end <= 255")
    scan(args.port, args.baud, args.start, args.end, args.delay, args.output)

if __name__ == "__main__":
    main()
