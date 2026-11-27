# Parameter map

**Index convention:** `data_offset` is zero-based **after** the response's echoed `00 ID` prefix, i.e. absolute `frame_offset=data_offset+5`. For multibyte values use big-endian unless specifically marked otherwise. `confirmed` means the corresponding LCD setting was independently changed and matching byte(s) observed. `candidate` means correlation only.

## ID 12 — L1 configuration (31 data bytes)

| Data offset | Format | Meaning | Status |
|---:|---|---|---|
| 0,1,2 | uint8 °C | Y1/Y3/Y5 mirrors of ID 65 | all confirmed |
| 3 | uint8 °C | L1 supply minimum | confirmed 15→16 |
| 4 | uint8 °C | L1 supply maximum | confirmed 50→51 |
| 5 | uint8 °C | night reduction | confirmed 0→3 |
| 7 | uint8 /10 | L1 room compensation gain | confirmed 4.0→5.0 (`28→32`); serial write 5.0→4.9 verified |
| 8 | uint8 °C | L1mv.min(0°C) | confirmed 10→11 |
| 9 | uint8 °C | L1mv.min(-20°C) | confirmed 30→31 |
| 10 | uint8 °C | Pal.min(0°C) | confirmed 5→6 |
| 11 | uint8 °C | Pal.min(-20°C) | confirmed 15→16 |
| 12 | uint8 °C | Paluuv.max | confirmed 70→71 |
| 14 | uint8 | autumn drying setting | confirmed 2→3 |
| 19 | uint8 hours | outdoor-temperature delay | confirmed 2→3 |
| 26 | uint8 °C | L1 deviation alarm threshold | confirmed 25→26 |
| 27 | int8 °C | L1 parallel curve shift | confirmed 0→-2 (`00→FE`) |

All other ID 12 bytes are undecoded. Offset 9 has been restored to 30°C.

## ID 13 — L1/L2 tuning (31 data bytes)

| Offset(s) | Encoding | Meaning | Status |
|---|---|---|---|
| 1–2 | u16 BE /10 °C | L1 room setpoint | confirmed 21.5→22.5→21.5; serial write 25.0→25.1 verified |
| 3–4 | u16 BE °C | L1 P band | confirmed 140→150 |
| 5–6 | u16 BE seconds | L1 I time | confirmed 50→60 |
| 7–8 | u16 BE /10 seconds | L1 D time | confirmed 0→15 for 1.5s |
| 9–10 | u16 BE seconds | L1 3-state actuator travel time | confirmed 150→160 |
| 11–12 | u16 BE | L2 first value 215 | unknown |
| 13–14 | u16 BE °C | L2 P band | confirmed 140→160 |
| 15–16 | u16 BE seconds | L2 I time | confirmed 50→60, restored to 50 |
| 17–18 | u16 BE /10 seconds | L2 D time | confirmed 0→15 for 1.5s, restored to 0 |
| 19–20 | u16 BE seconds | L2 actuator time | confirmed 150→160 |

Both groups have experimentally confirmed P/I/D and actuator travel time. The L1 room setpoint is confirmed; L2 equivalent remains a candidate.

## ID 14 — L2 configuration (31 data bytes)

- Data offset **22**, uint8 °C: L2 deviation alarm, **confirmed** 25→26.
- Offset **7**, uint8 °C: L2mv.min(0), **confirmed** 10→11, restored to 10.
- Offset **8**, uint8 °C: L2mv.min(-20), **confirmed** 30→31, restored to 30.
- Offset **3**, uint8 °C: L2 supply minimum, **confirmed** 15→16, restored to 15.
- Offset **4**, uint8 °C: L2 supply maximum, **confirmed** 70→71; restored to 70.
- Offset **5**, uint8 °C: L2 night reduction, **confirmed** 0→3, restored to 0.
- Offset **9**, uint8 °C: L2 autumn drying, **confirmed** 2→3, restored to 2.
- Offset **23**, int8 °C: L2 parallel curve shift, **confirmed** 0→-2 (`00→FE`), restored to 0.
- Offset **15**, uint8 hours: L2 outdoor-temperature delay, **confirmed** 0→3, restored to 0.
- Offsets **0,1,2**, uint8 °C: Y1/Y3/Y5 mirrors of ID 66, all confirmed by controlled changes.
- Other values are not verified; do not copy L1 positional assumptions to L2.

## ID 15 — calculated settings, not fully decoded

- Data offset 6 correlates with the autumn drying adjustment (2→3).
- Data offset 13 changed with the L1 curve parallel shift 0→-2.
- Offset 14 tracks the final L1 target in room compensation and minimum-limit tests; see experiment table below.
- Offset 21 changed 2→3 with L2 autumn drying; offset 26 changed 48→49 while offset 15 remained 46. This supports the hypothesis of L2 active autumn correction and final target, respectively; exact semantics remain unverified.
- Offset 25 changed 0→-2 and back to 0 with L2 parallel shift; offset 26 changed 49→46→48 across autumn/shift experiments, consistent with base 46 plus autumn correction and shift. Final target semantics still require LCD confirmation.
- No assertion that ID 15 is a writable configuration block.

## ID 16 — DHW configuration (31 data bytes)

| Offset(s) | Encoding | Meaning | Status |
|---|---|---|---|
| 1–2 | u16 BE /10 °C | DHW setpoint | confirmed 58.0→59.0 |
| 7–8 | u16 BE °C | DHW feedforward (Ennakointi) | confirmed 140→150 |
| 9–10 | u16 BE °C | DHW P band | confirmed 70→80 |
| 11–12 | u16 BE seconds | DHW I time | confirmed 18→20 |
| 13–14 | u16 BE /10 seconds | DHW D time | confirmed 0→15 for 1.5s |
| 19–20 | u16 BE % | DHW fast drive (Pika-ajo) | confirmed 60→65 |
| 21–22 | u16 BE ×10 seconds | DHW alarm delay | confirmed 600→610 seconds (stored 60→61) |
| 23–24 | u16 BE °C | DHW deviation alarm threshold | confirmed 25→26 |

Remaining offsets undecoded. The array starts with data byte 0; never shift offsets by one when parsing.

## ID 44 — other configuration

- Offset **8**, uint8: `Vent.keskisulk`, **confirmed** 19→20. Exact engineering interpretation/unit requires separate verification.
- Offset **28**, uint8 ×10 minutes: `PoikHälHidMin` **confirmed** 60→70 min (stored 6→7).

## IDs 18+, 51, 65 and others

- Temperature measurements use signed int16 BE /100 °C; observed raw sentinel `0x865A` on disconnected sensors. ID 18 outdoor and ID 20 L1 supply are verified by LCD/physical changes; other labelled IDs are observational rather than individually altered.
- **ID 51**: DHW motor-command percent, confirmed LCD sweep 100/50/26/0; see November 27 findings below.
## IDs 65 and 66 — five-point heating curves (31 data bytes each)

ID 65 = L1; ID 66 = L2. LCD observations establish non-editable outer X coordinates and three editable interior X coordinates. The outer X values −20 and +20°C are assumed from the manual examples, not independently verified. All five Y coordinates are editable.

| Data offset | Format | Field | L1 status | L2 status |
|---:|---|---|---|---|
| 0 | enum8 | curve type: 0 = five-point, 1 = three-point | confirmed 0→1→0 | confirmed 0→1→0 |
| 1 | uint8 °C | Y1 | confirmed 38→39 | confirmed 62→63 |
| 2 | uint8 °C | Y2 | confirmed 31→34 | confirmed 52→53 |
| 3 | uint8 °C | Y3 | confirmed 25→26 | confirmed 42→43 |
| 4 | uint8 °C | Y4 | confirmed 22→23 | confirmed 31→32 |
| 5 | uint8 °C | Y5 | confirmed 20→21 | confirmed 20→21 |
| 6 | int8 °C | X2 | confirmed −12→−11 | confirmed −10→−11 |
| 7 | int8 °C | X3 | confirmed 0→−2 | confirmed 0→−2 |
| 8 | int8 °C | X4 | confirmed 10→11 | confirmed 10→11 |

All 18 editable fields across both blocks are confirmed; ID 12 offsets 0–2 mirror L1 Y1/Y3/Y5. Final restoration capture `ouman_l1_curve_restored.json` confirms L1 X4 11→10, with only four timestamp blocks also changing. Offsets 9–30 remain unknown. Latest observed L1 points: (−20,38), (−12,34), (0,25), (10,22), (20,20). Latest L2 points: (−20,62), (−10,52), (0,42), (10,31), (20,20). Y2/Y4 and interior X changes did not mirror into ID 14; Y1/Y3/Y5 did. Whether ID 12/14 represent the active three-point curve or compatibility storage is unverified. The LCD curve-type selector changes offset 0 in both IDs 65 and 66 together; independent circuit selection is unverified.

**Observed side effect:** on returning from three-point to five-point mode, L1 Y2 changed automatically from 34 to 31°C (ID 65 offset 2, `22→1F`), confirmed by the operator. L2 coordinates remained unchanged. The recalculation algorithm is unknown. Future restore design must account for mode-dependent coordinate changes: set mode before restoring coordinates and verify all fields by readback. This is a proposed safety requirement, not a tested write procedure.

## Confidence and scope

A field's position in a *read response* does **not** imply a writeable field or a safe restore action. Firmware 2.15 only has been tested. Detailed experiment names are in [CAPTURE_MANIFEST.md](../research/CAPTURE_MANIFEST.md).

## L1 room sensor and compensation experiments

Room sensor T3 was simulated with approximately 10 kΩ and enabled using Starttitoiminto (operator confirmed). ID 21 data offsets 0–1 returned 09 C4 (25.00°C, signed BE /100). ID 17 offset 3 changed 0C→02 on activation; offset 11 also changed, so the complete configuration table remains unresolved.

| Capture | Room setpoint °C | Gain | Supply minimum °C | ID 15 offset 1 (signed) | Offset 10 | Offset 14 |
|---|---:|---:|---:|---:|---:|---:|
| ouman_l1_room_sensor_enabled.json | 21.5 | 4.0 | 15 | -13 | 0 | 17 |
| ouman_l1_room_setpoint225.json | 22.5 | 4.0 | 15 | -10 | 0 | 20 |
| ouman_l1_room_comp5.json | 21.5 | 5.0 | 15 | -18 | 3 | 15 |
| ouman_l1_room_comp_min16.json | 21.5 | 5.0 | 16 | -19 | 4 | 16 |

All four captures independently checked for request bytes, response length, checksum, payload consistency and accepted ID echo: 512/512 valid, 72 accepted and 56 rejected per sweep. ID 15 offset 0 remained 28 and offset 6 remained 2. Offset 1 is strongly supported as signed room compensation; offset 10 tracks positive minimum-limit correction (signedness unresolved); offset 14 tracks the final supply target including minimum clamping. The last row's displayed terms sum to 15 rather than 16; independent rounding or time-dependent calculation is possible but not established. No write semantics inferred. L2 equivalents remain candidates.

## IDs 2 and 3 — clock

Seven data bytes: year U16 BE, then month, day, hour, minute, second (U8 each). Both IDs readable; ID 2 write verified on firmware 2.15, ID 3 write untested. See [PROTOCOL.md](PROTOCOL.md) for exact evidence.

ID 13 L1 room setpoint serial write and power-cycle persistence confirmed by operator; other fields in the block were preserved, not independently write-tested.

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
- ON and OFF may have different weekday masks and times. Zero time is valid midnight, not a deletion marker. A single event with zero weekday mask retained its type; clearing the paired event's weekdays removed both and compacted the table across block boundaries. 16 events observed before deletion, 14 after, IDs 6/7 then zero. Last two times 11:50 and 11:54 moved to slots 13/14. Slot order may change on LCD edits; preserve order and raw bytes in backups. IDs 8/9 subsequently identified as a separate relay schedule table; IDs 10/11 remain unverified; total capacity unknown. No LV schedule available on tested LCD. Relay schedules mapped below; no schedule serial writes tested.
- ESPHome/Home Assistant is permanently read-only (0x81 only); separate offline backup/editor and bench-only restore tooling. Raw snapshots are not transferable settings. Exclude live commands, identity, unknown fields and mirrors from restore. Only independently write-tested fields may be restored with explicit approval, target snapshot, journal and readback. No automatic retries or blind rollback.

## 2026-11-27 — relay experiments (firmware 2.15)

Offsets exclude echoed 00 ID. LCD changes followed by read-only scans; no relay serial writes tested.

| ID | Offset | Encoding | Observed meaning |
|---|---:|---|---|
| 44 | 9 | U8 enum | R2 configuration |
| 44 | 10 | U8 enum | R1 configuration |
| 44 | 15 | S8 °C | R1 outdoor threshold, −15→−7 (F1→F9) |
| 44 | 27 | U8 °C | R1 temperature threshold, 55→63 |
| 14 | 25 | U8 °C | R1 burner ON threshold, 70→83 |
| 14 | 26 | U8 °C | R1 burner hysteresis, 5→9 |
| 45 | 1 | bit 3 / bit 4 | R1 / R2 commanded state, not contact feedback |
| 58 | 2–3 | U16BE | R1 override mode (high nibble), remaining minutes (low 12 bits) |
| 59 | 2–3 | U16BE | R2 override, same layout observed for modes 0 and 3 |

Configuration codes (hex): 00 unused (R2 confirmed), 01 weekly time control (both), 04 coupled 230 V motor control (both), 06 time/outdoor control (R1), 07 temperature control (R1), 08 burner control (R1). Pump mode remains unmapped. Selecting motor control requires releasing R2; leaving motor control for R1 temperature control automatically releases R2 (04/04→00/07 in offsets 9/10). Preserve inactive stored settings; do not treat these coupled configuration fields as independent writes.

Override modes: 0 schedule, 1 continuous ON, 2 continuous OFF, 3 timer ON, 4 timer OFF (all observed for R1; only 0 and 3 independently observed for R2). 600 minutes encoded as 32 58 in offsets 2–3 of both IDs. Short timers already decrement during scanning. LCD limit 999 minutes. Offsets 0–1 unknown. Overrides/countdowns and commanded state are live data, not portable settings.

Relay weekly schedules use separate shared ID 8/9 table with the same 14-slot layout as 4/5. R1 event types 13/23 hex (ON/OFF), R2 14/24. R1 13:17 Mon/Wed/Fri and 15:43 Tue/Thu/Sat; R2 14:25 Mon and 16:35 Fri. ID 10/11 continuation remains unverified. Schedules retained when relay configuration changed. No serial schedule writes tested.

R1 renamed TEST12345 on LCD, but no corresponding payload change found. R1 temperature-control hysteresis 3→7 persisted on LCD but no corresponding payload change found. Neither mapping is established; do not silently claim complete backup coverage. Burner hysteresis is a separate confirmed field. ID 44 offset 28 is not established as temperature hysteresis.

Extended scan with burner control active: all 128 IDs 128–255 returned 02 01 02 00 FF 02, consistent with previous day's scan. No new readable IDs in this configuration. Scope is firmware 2.15 and tested configurations, not all firmware or commands. Continue ordinary research scans 0–127; retain optional full 0–255 raw snapshot for compatibility research.

Next: digital input configuration, then remaining LCD menus and selective bench restore. Keep relay loads disconnected and existing writer allowlist unchanged.
