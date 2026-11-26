#!/usr/bin/env python3
"""Experimental bench-only EH-203 firmware 2.15 parameter writer."""
import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

# Deliberately narrow experimental ranges, not manufacturer limits.
PARAMETERS = {
    "l1_room_gain": (12, 7, 1, 49, 50),
    "l1_room_setpoint": (13, 1, 2, 250, 251),
}

def frame(cmd, pid, data=b""):
    body = bytes((cmd, len(data)+2, 0, pid)) + data
    return b"\x02" + body + bytes((sum(body)&255,))

def decode(rx, pid, size):
    if (len(rx) != size+6 or rx[0] != 2 or rx[2] != size+2
            or rx[3:5] != bytes((0,pid))
            or sum(rx[1:-1])&255 != rx[-1]):
        raise ValueError("Invalid response, echo, length or checksum")
    return rx[5:-1]

def raw_value(value, low, high):
    try:
        n = Decimal(value)*10
        if not n.is_finite() or n != n.to_integral_value() or not low <= n <= high:
            raise ValueError("Outside tested range or precision")
        return int(n)
    except InvalidOperation as exc:
        raise ValueError("Invalid decimal") from exc

def patch(data, offset, width, expected, target):
    if len(data) != 31 or int.from_bytes(data[offset:offset+width], "big") != expected:
        raise ValueError("Unexpected original block or value")
    return data[:offset]+target.to_bytes(width,"big")+data[offset+width:]

def save(path, record):
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".write-")
    try:
        with os.fdopen(fd,"w") as f:
            json.dump(record,f,indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(name,path)
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if os.path.exists(name):
            os.unlink(name)

def run(ser, args, path, record, confirm):
    pid, offset, width, low, high = PARAMETERS[args.parameter]
    expected = raw_value(args.expect,low,high)
    target = raw_value(args.value,low,high)
    def exchange(tx):
        entry = {"tx":tx.hex(" ")}
        record["frames"].append(entry)
        save(path,record)
        print("TX:",entry["tx"])
        ser.reset_input_buffer()
        if ser.write(tx) != len(tx):
            raise IOError("Short write")
        ser.flush()
        rx = ser.read(3)
        if len(rx)==3 and rx[0]==2:
            rx += ser.read(rx[2]+1)
        entry["rx"] = rx.hex(" ")
        save(path,record)
        print("RX:",entry["rx"])
        return rx
    identity = exchange(frame(0x81,1))
    # ID 1 length may vary; validate actual frame before inspecting fields.
    if len(identity)<24:
        raise ValueError("Short identity")
    ident = decode(identity,1,len(identity)-6)
    if ident[4:7]!=b"203" or ident[8]!=215:
        raise ValueError("Only EH-203 firmware 2.15 supported")
    record["serial_number"] = int.from_bytes(ident[:4],"little")
    original = decode(exchange(frame(0x81,pid)),pid,31)
    modified = patch(original,offset,width,expected,target)
    record.update(original=original.hex(" "), proposed=modified.hex(" "))
    save(path,record)
    print("Original:",original.hex(" "))
    print("Proposed:",modified.hex(" "))
    print("Write frame:",frame(0x82,pid,modified).hex(" "))
    if original==modified:
        return "unchanged"
    if args.dry_run:
        return "dry_run"
    if not confirm():
        return "cancelled"
    if decode(exchange(frame(0x81,pid)),pid,31)!=original:
        raise ValueError("Block changed since preview; no write sent")
    record["status"]="write_outcome_unknown"
    save(path,record)
    ack = exchange(frame(0x82,pid,modified))
    try:
        decode(ack,pid,0)
        ack_ok=True
    except ValueError:
        ack_ok=False
    import time
    time.sleep(1)
    actual=decode(exchange(frame(0x81,pid)),pid,31)
    record["readback"]=actual.hex(" ")
    save(path,record)
    if actual!=modified or not ack_ok:
        raise ValueError("Write not fully verified; inspect manually, no retry")
    return "verified"

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port",default="/dev/ttyUSB0")
    p.add_argument("--parameter",required=True,choices=PARAMETERS)
    p.add_argument("--expect",required=True)
    p.add_argument("--value",required=True)
    p.add_argument("--dry-run",action="store_true")
    p.add_argument("--log-dir",type=Path,default=Path("write-captures"))
    args=p.parse_args()
    _,_,_,low,high=PARAMETERS[args.parameter]
    try:
        raw_value(args.expect,low,high)
        raw_value(args.value,low,high)
    except ValueError as exc:
        p.error(str(exc))
    import serial
    args.log_dir.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix="ouman-write-",suffix=".json",dir=args.log_dir)
    os.close(fd)
    path=Path(name)
    record={"timestamp":datetime.now(timezone.utc).isoformat(),
            "parameter":args.parameter,"expected":args.expect,"value":args.value,
            "port":args.port,"status":"started","frames":[]}
    def confirm():
        with open("/dev/tty") as tty:
            print("Bench controller only. Execute write? [yes/no]: ",end="",flush=True)
            return tty.readline().strip()=="yes"
    try:
        with serial.Serial(args.port,4800,timeout=1,write_timeout=1,
                           exclusive=True,rtscts=False,dsrdtr=False,xonxoff=False) as ser:
            record["status"]=run(ser,args,path,record,confirm)
        return 0
    except (Exception,KeyboardInterrupt) as exc:
        record["error"]=str(exc)
        if record["status"]!="write_outcome_unknown":
            record["status"]="failed_before_write"
        print("STOP:",exc)
        return 1
    finally:
        save(path,record)
        print("Status:",record["status"],"Log:",path)

if __name__=="__main__":
    raise SystemExit(main())
