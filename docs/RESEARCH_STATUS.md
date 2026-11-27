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
- IDs 128–255: all 128 requests and responses independently validated; all rejected with `02 01 02 00 FF 02`. Median response 26.535 ms (26.20–91.83 ms). Full 8-bit ID space scanned with the established read command: 72 accepted, 184 rejected. Other command types are not ruled out.
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
Clock and ID 13 room setpoint writes verified. ID 13 restoration to 25.0°C verified by serial readback. ID 12 room compensation gain 5.0→4.9 verified. Next proposed test: restore gain to 5.0.

## Research continuity rule
Every new session should record: previous capture, exact LCD change(s), next capture, frame validity, per-ID data-byte diff, which changes were independently confirmed, and next single test. Keep raw captures immutable.

## L1 room sensor and compensation experiments

Room sensor T3 was simulated with approximately 10 kΩ and enabled using Starttitoiminto (operator confirmed). ID 21 data offsets 0–1 returned 09 C4 (25.00°C, signed BE /100). ID 17 offset 3 changed 0C→02 on activation; offset 11 also changed, so the complete configuration table remains unresolved.

| Capture | Room setpoint °C | Gain | Supply minimum °C | ID 15 offset 1 (signed) | Offset 10 | Offset 14 |
|---|---:|---:|---:|---:|---:|---:|
| ouman_l1_room_sensor_enabled.json | 21.5 | 4.0 | 15 | -13 | 0 | 17 |
| ouman_l1_room_setpoint225.json | 22.5 | 4.0 | 15 | -10 | 0 | 20 |
| ouman_l1_room_comp5.json | 21.5 | 5.0 | 15 | -18 | 3 | 15 |
| ouman_l1_room_comp_min16.json | 21.5 | 5.0 | 16 | -19 | 4 | 16 |

All four captures independently checked for request bytes, response length, checksum, payload consistency and accepted ID echo: 512/512 valid, 72 accepted and 56 rejected per sweep. ID 15 offset 0 remained 28 and offset 6 remained 2. Offset 1 is strongly supported as signed room compensation; offset 10 tracks positive minimum-limit correction (signedness unresolved); offset 14 tracks the final supply target including minimum clamping. The last row's displayed terms sum to 15 rather than 16; independent rounding or time-dependent calculation is possible but not established. No write semantics inferred. L2 equivalents remain candidates.

Confirmed configuration: ID 12 offset 7 U8 /10 gain; ID 13 offsets 1–2 U16 BE /10 °C room setpoint.

## First successful serial write — 2026-11-26

Bench EH-203 firmware 2.15, ID 2 clock. Operator-confirmed single write followed by two reads. Exact terminal transcript (all six frames checked for length and SUM8):

```text
TX: 02 82 09 00 02 07 EA 0B 1A 12 20 17 EC
RX: 02 06 02 00 02 0A
TX: 02 81 02 00 02 85
RX: 02 2E 09 00 02 07 EA 0B 1A 12 20 17 98
TX: 02 81 02 00 03 86
RX: 02 06 09 00 03 07 EA 0B 1A 12 20 19 73
```

Written clock: 2026-11-26 18:32:23; ID 2 readback identical; ID 3 readback 18:32:25. The write acknowledgement has no data beyond the echoed ID. Header 06 was observed, not established as a universal success indicator. Persistence across power loss, ID 3 writability and configuration-block writes remain untested.

## ID 13 configuration write and persistence — 2026-11-26

Bench firmware 2.15: L1 room setpoint 25.0→25.1°C, U16 BE at data offsets 1–2. Read-modify-write preserved the other bytes; operator reported only offset 2 changed FA→FB and full block match. LCD independently confirmed 25.1°C. Operator subsequently confirmed the setting survived the requested power-cycle test; no post-reboot raw serial capture was supplied. Memory technology, endurance and general persistence of other fields remain unknown.

```text
TX: 02 82 21 00 0D 00 00 FB 00 8C 00 32 00 00 00 96 00 D7 00 8C 00 32 00 00 00 96 00 00 00 00 00 00 00 00 00 00 2A
RX: 02 06 02 00 0D 15
TX: 02 81 02 00 0D 90
RX: 02 06 21 00 0D 00 00 FB 00 8C 00 32 00 00 00 96 00 D7 00 8C 00 32 00 00 00 96 00 00 00 00 00 00 00 00 00 00 AE
```

All four transcript frames checked for length and SUM8; the 31-byte write and readback data match exactly. Avoid redundant writes, automatic retries and periodic writes of unchanged settings.

## ID 13 restoration — 2026-11-26

L1 room setpoint restored 25.1→25.0°C after the persistence test. Operator transcript reports only offset 2 FB→FA and full block match. All four frames independently checked for length and SUM8; write and readback data identical. Successful acknowledgement header 16 and readback header 1E demonstrate that success must not require header 06. No post-restoration LCD or power-cycle check reported.

```text
TX: 02 82 21 00 0D 00 00 FA 00 8C 00 32 00 00 00 96 00 D7 00 8C 00 32 00 00 00 96 00 00 00 00 00 00 00 00 00 00 29
RX: 02 16 02 00 0D 25
TX: 02 81 02 00 0D 90
RX: 02 1E 21 00 0D 00 00 FA 00 8C 00 32 00 00 00 96 00 D7 00 8C 00 32 00 00 00 96 00 00 00 00 00 00 00 00 00 00 C5
```

## ID 12 room compensation gain write — 2026-11-26

Firmware 2.15 bench: L1 gain 5.0→4.9, U8 /10 at data offset 7. Operator reports only offset 7 changed 32→31, full block match and LCD confirmation. All four frames checked for length and SUM8; write/readback data match exactly. Acknowledgement header 2E, readback header 36. Persistence and restoration of this field not yet tested.

```text
TX: 02 82 21 00 0C 26 19 14 0F 32 00 00 31 0A 1E 05 0F 46 FA 02 00 64 00 00 02 05 00 01 00 00 00 19 00 00 00 00 77
RX: 02 2E 02 00 0C 3C
TX: 02 81 02 00 0C 8F
RX: 02 36 21 00 0C 26 19 14 0F 32 00 00 31 0A 1E 05 0F 46 FA 02 00 64 00 00 02 05 00 01 00 00 00 19 00 00 00 00 2B
```

## Reusable writer hardware validation — 2026-11-26

`ouman-write-8f3tk54o.json`: dry run, identity EH-203 firmware 2.15, ID 12 gain 4.9→5.0 preview. `ouman-write-p9yh44zi.json`: actual restoration, status verified, five exchanges (identity, original read, pre-write recheck, write, readback). All ten frames independently checked for length and SUM8; 31-byte proposed and readback blocks identical, only offset 7 changed 31→32. Operator confirmed LCD 5.0. Original JSON files not committed. Unit test execution and failure-path hardware testing not reported.

## ID 65 L1 five-point curve Y3 serial write — 2026-11-26

Dry run `ouman-write-fo016u6o.json`; actual write `ouman-write-lxoj52t3.json`. Firmware 2.15, Y3 25→26°C at ID 65 data offset 3. All 16 actual TX/RX frames independently validated for STX, length, SUM8 and echoed ID. Write ACK `02 06 02 00 41 49`. Full 31-byte readback matches proposed block; only offset 3 changes 19→1A. ID 12 mirror automatically changes only offset 1 from 19→1A without an ID 12 write. Operator confirms LCD 0°C=26°C. Persistence and restoration not yet tested. This proves synchronization for this field and direction only. Raw JSON remains local.

## ID 65 Y3 persistence and restoration — 2026-11-26

Operator confirmed LCD 0°C=26°C after power cycle. Post-cycle dry run `ouman-write-kw8vnk5z.json` shows ID 65 offset 3 and ID 12 offset 1 both 1A. Restoration `ouman-write-7x8hhuye.json` 26→25°C: all 16 TX/RX frames independently validated with Python for STX, length, SUM8 and echoed ID; proposed/readback match, only ID 65 offset 3 and ID 12 offset 1 change 1A→19. ACK `02 02 02 00 41 45`. Operator confirms LCD restoration with a small unmeasured display delay. Automatic mirror synchronization verified for increasing and decreasing Y3 via ID 65, not reverse ID 12 writes or other points. No post-restoration power cycle reported. Raw JSON not committed.

## ID 65 signed X2 experiment — 2026-11-26

Dry run `ouman-write-k2wni0jf.json`, write `ouman-write-cx2byrsk.json`, restoration `ouman-write-n32yr9lf.json`. X2 −12→−11→−12°C, signed byte at offset 6 F4→F5→F4. Both actual logs report verified and operator confirms LCD. ID 12 remains byte-identical in both directions. Restoration independently validated in Python: all 16 frames pass STX, length, SUM8 and ID echo; proposed equals readback, only offset 6 changes. X2 power-cycle persistence not separately tested. Raw logs not committed.

## ID 16 DHW setpoint write experiment — 2026-11-26

Dry run `ouman-write-xo_bodgm.json`, actual write `ouman-write-lt3_h3d1.json`, restoration `ouman-write-gri329gh.json`. U16BE offsets 1–2, scale 0.1°C, 58.0→58.1→58.0°C (0244→0245→0244). Both actual logs report verified; operator confirmed LCD both ways, restoration immediately visible. Restoration independently checked in Python: 10/10 frames pass STX, length, SUM8 and ID echo, write payload and readback match proposed, only offset 2 changes. ACK `02 06 02 00 10 18`. Persistence not separately tested. Raw logs not committed.

## Motor configuration and restoration — 2026-11-26

L1 motor type: ID 12 data offset 21; L2: ID 14 offset 17. U8 enum for both: 0 = three-state, 1 = 0–10 V, 2 = 2–10 V. ID 13 motor travel times: L1 offsets 9–10, L2 offsets 19–20, U16BE seconds. Separate 160 s captures support both mappings; restored values 150 s. Motor configuration serial writes remain untested.

| Capture (JSON basename) | L1 type | L2 type | ID 49 | ID 50 | ID 51 |
|---|---:|---:|---:|---:|---:|
| ouman_motor_baseline | 0 | 0 | 0 | 0 | 100 |
| ouman_l1_motor_0_10v | 1 | 0 | 0 | 0 | 100 |
| ouman_l1_motor_2_10v | 2 | 0 | 0 | 0 | 100 |
| ouman_l2_motor_0_10v | 0 | 1 | 0 | 2 | 100 |
| ouman_l2_motor_2_10v | 0 | 2 | 0 | 11 | 100 |
| ouman_motor_restored | 0 | 0 | 0 | 20 | 100 |

Additional captures: ouman_l1_motor160.json and ouman_l2_motor160.json (64 IDs each). Final 128-ID capture differs from baseline only at IDs 2, 3, 36, 38, 46 and 50; IDs 12–14 identical. ID 50 is a candidate internal L2 command, not verified physical position or percentage. ID 49 remains a candidate L1 command. ID 51 DHW command previously LCD-confirmed. All eight motor captures (1792 frames) included in a fresh Python audit of 96 local JSON files (14980 frames, zero STX/length/SUM8 failures). This audit does not establish semantic validity of every field. Raw captures not uploaded to GitHub in this update.

## Backup and restore boundary

Read-only raw snapshot of IDs 0–255 is feasible now. A portable configuration export must separately classify confirmed fields, mirrors, live values, identity and unknown data. Restore only independently write-tested allowlisted fields, with target snapshot, compatibility check, explicit diff/approval, read-modify-write, durable journal and full readback; never blindly replay raw blocks. Curve IDs 65/66 are canonical candidates; ID 65 Y3 mirror into ID 12 verified, other directions untested. General restore remains unvalidated. Next: operating modes, writer tests and staged bench restore.

## 2026-11-27 — operating modes, DHW command and weekly schedules

Bench firmware 2.15, LCD changes followed by read-only sweeps. Data offsets exclude the echoed 00 ID prefix.

- ID 42 (0x2A), two data bytes: offset 1 low nibble L1, high nibble L2. Codes 0 automatic, 1 continuous day, 2 continuous night, 3 shutdown, 4 mechanical manual, 5 electrical manual. All six modes observed for both circuits. Mixed L1 day/L2 night returned 00 21; all automatic 00 00. Offset 0 low nibble DHW (LV): 0 automatic, 4 mechanical manual, 5 electrical manual observed; other codes and high nibble unknown. No serial mode writes tested.
- ID 51 (0x33), offset 0 U8, LCD DHW command percent, scale 1:1: manual LCD 100/50/26/0 matched hex 64/32/1A/00; automatic restored returned 0F (15%). LCD steps need not be uniform. Not measured physical valve feedback. IDs 49/50 remain candidates. ID 15 offset 26 tracked L2 shutdown 48→14→48°C, strong final-target candidate, not independently LCD verified.
- Weekly schedules share a table across L1/L2. Confirmed block pairs IDs 4/5 and 6/7, each 31 data bytes per ID. Even ID: 14 U16BE minute-of-day values at offsets 1+2*i (i=0..13); offsets 0,29,30 unknown. Odd ID: weekday masks offsets 0..13, event types offsets 14..27, offsets 28..30 unknown. Event codes hex 10 L1 reduction ON, 20 L1 OFF, 11 L2 ON, 21 L2 OFF. High/low nibble interpretation supported for these codes only. Expected weekday bits Mon..Sun = 0..6; observed masks 17,2E,40,7F,1F,60,01 support this mapping, but not every individual bit independently isolated.
- ON and OFF may have different weekday masks and times. Zero time is valid midnight, not a deletion marker. A single event with zero weekday mask retained its type; clearing the paired event's weekdays removed both and compacted the table across block boundaries. 16 events observed before deletion, 14 after, IDs 6/7 then zero. Last two times 11:50 and 11:54 moved to slots 13/14. Slot order may change on LCD edits; preserve order and raw bytes in backups. IDs 8–11 possible continuation, not proven; total capacity unknown. No LV schedule available on tested LCD. Relay schedules next; no schedule serial writes tested.
- ESPHome/Home Assistant is permanently read-only (0x81 only); separate offline backup/editor and bench-only restore tooling. Raw snapshots are not transferable settings. Exclude live commands, identity, unknown fields and mirrors from restore. Only independently write-tested fields may be restored with explicit approval, target snapshot, journal and readback. No automatic retries or blind rollback.

Next: relay schedules, remaining LCD menus, then raw backup and selective editor. Preserve the existing narrow writer allowlist.
