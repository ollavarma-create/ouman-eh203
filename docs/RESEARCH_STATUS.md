# Research status — 2026-11-26

## Test setup
- Ouman EH-203, software version **2.15**, observed serial **10004680**.
- Native serial protocol, 4800 baud, 8N1, USB-to-RS232 PL2303 via Fedora, `/dev/ttyUSB0`.
- LCD service menus used for controlled single-parameter changes; read-only serial sweep IDs 0–63 after each change.
- The present captures are from **one bench controller**. Do not extrapolate compatibility to other firmware without tests.

## Verified fundamentals
- Six-byte read request: `02 81 02 00 ID CHECKSUM`.
- Checksum is the low byte of the sum of all bytes **between** STX and checksum (for requests, `81+02+00+ID`).
- Response: `02 HEADER LENGTH 00 ID DATA... CHECKSUM`; total bytes = `LENGTH+4`.
- `HEADER` varies and its bit semantics have **not** been established.
- `02 01 02 00 FF 02` is an observed rejected-ID response; ID 0 uses a variant header.
- All 64 responses in successive 0–63 scans were structurally valid, including rejected responses.
- ID 0 and ID 48 rejected on the test unit.
- IDs 64–127 also scanned; only IDs 64,65,66,95–101 accepted in that range.
- Negative temperatures use signed BE 16-bit hundredths; raw `0x865A` observed when a temperature sensor was disconnected. Treat as a specific observed fault sentinel, not a universal rule.

## Controlled confirmations
- ID 1: bytes 0–3 of data are the observed serial number as little-endian uint32; version byte 8 = 215 for firmware 2.15.
- ID 12: offsets 3,4,5,8,9,10,11,12,14,19,26,27.
- ID 13: L1 PID P/I/D and L1 actuator time; L2 P control confirmed.
- ID 14: offset 22 = L2 deviation alarm threshold.
- ID 16: DHW setpoint, feedforward, P/I/D, fast-drive %, alarm delay, deviation alarm threshold.
- ID 44: ventilation-related threshold offset 8 (display label `Vent.keskisulk`) and deviation alarm delay offset 28.
- ID 51: DHW motor-command percentage (LCD matched 100%).
- ID 65: observed 5-point L1 heating curve values match LCD, but **individual curve-point modification has not been tested**.

See [PARAMETER_MAP.md](PARAMETER_MAP.md) for precise positions, types and units.

## Sensor observations and unresolved status
- Temperature IDs observed: 18 outdoor, 20 L1 supply, 21 L1 room, 23 L1 return, 24 DHW supply, 25 DHW circulation, 26 L2 supply, 27 configured measurement 6, 33 tank top, 34 tank bottom, 41 hot gas. Not all physical channels have connected sensors.
- ID 56 resembles outdoor temperature and differed on outdoor sensor disconnection; semantics **unverified**.
- IDs 49/50 may represent L1/L2 motor commands, but only zeros observed and not confirmed.
- IDs 17 and 46 changed on selected events; no verified direct native alarm bitmap. Header bits should not be misrepresented as alarm flags.
- ID 46 carries a timestamp and event-like state but remains undecoded.
- Trend sampling interval change 1s→5s produced no confirmed setting bytes in IDs 0–63.
- Query fourth byte 00→01 for a few IDs yielded identical responses; no proof of high address extension.

## Next controlled experiment
Latest scan: `ouman_l1_supply_min20_31.json`. L1 `L1mv.min(-20)` was **31°C**, whereas original bench setting was **30°C**.

1. Restore L1 `L1mv.min(-20)` from 31°C to 30°C.
2. Change **L2mv.min(0) 10°C→11°C**.
3. Rescan IDs 0–63 as `ouman_l2_supply_min0_11.json`.
4. Prediction: ID 12 data offset 9: `1F→1E`; ID 14 data offset 7: `0A→0B`.
5. Check full frame integrity and diff **data** bytes separately from dynamic timestamps.

This next step is a **prediction**, not a confirmed map.

## Research continuity rule
Every new session should record: previous capture, exact LCD change(s), next capture, frame validity, per-ID data-byte diff, which changes were independently confirmed, and next single test. Keep raw captures immutable.
