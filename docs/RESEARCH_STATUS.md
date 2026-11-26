# Research status — 2026-11-26

## Test setup
- Ouman EH-203, software version **2.15**, observed serial **10004680**.
- Native serial protocol, 4800 baud, 8N1, USB-to-RS232 PL2303 via Fedora, `/dev/ttyUSB0`.
- LCD service menus used for controlled single-parameter changes; read-only serial sweeps IDs 0–63 initially and 0–127 for curve experiments.
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
- ID 13: L1 and L2 PID P/I/D and actuator travel times confirmed.
- ID 14: offsets 3 and 4 = ordinary L2 supply minimum and maximum; offsets 7 and 8 = L2 supply minimum at 0°C and -20°C; offset 22 = L2 deviation alarm threshold; offset 5 = night reduction; offset 9 = autumn drying; offset 23 = parallel shift; offset 15 = outdoor-temperature delay.
- ID 16: DHW setpoint, feedforward, P/I/D, fast-drive %, alarm delay, deviation alarm threshold.
- ID 44: ventilation-related threshold offset 8 (display label `Vent.keskisulk`) and deviation alarm delay offset 28.
- ID 51: DHW motor-command percentage (LCD matched 100%).
- ID 65: L1 five-point curve, all eight editable coordinates confirmed; ID 12 offsets 0–2 mirror Y1/Y3/Y5.
- ID 66: L2 five-point curve, all eight editable coordinates confirmed. ID 14 offsets 0–2 mirror Y1/Y3/Y5. Outer X coordinates are not editable; numerical endpoints −20/+20°C remain assumed.
- IDs 65/66 offset 0: curve type enum confirmed 0→1→0 (five-point→three-point→five-point). Returning to five-point mode automatically changed L1 Y2 34→31°C, as confirmed by the operator. L2 coordinates unchanged. Algorithm unknown; mode switching is not guaranteed lossless.
- ID 15 changes during curve experiments support interpolation and autumn correction hypotheses; exact target semantics remain unverified.

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
Latest capture: `ouman_l1_curve_restored.json`. All 128 response frames independently validated; 72 accepted, 56 rejected. Compared with `ouman_l1_curve_x4_11.json`, ID 65 offset 8 changed 11→10 and only timestamps in IDs 2,3,36,38 otherwise changed. Both curve blocks are restored to their original coordinate values. Curve mapping complete (18/18 editable fields). Next experiment to be selected with the operator; no serial write commands have been established.

## Research continuity rule
Every new session should record: previous capture, exact LCD change(s), next capture, frame validity, per-ID data-byte diff, which changes were independently confirmed, and next single test. Keep raw captures immutable.
