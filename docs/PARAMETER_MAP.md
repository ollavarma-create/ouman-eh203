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

## Digital inputs (firmware 2.15, 2026-11-27)

ID43 (0x2B), two data bytes: Dig1 = offset 1 low nibble; Dig2 = offset 1 high nibble; Dig3 = offset 0 low nibble. Offset 0 high nibble unknown. Observed function codes: 0 alarm, 1 half-speed extractor, 2 home/away, 3 pump 1 indication, 4 district heat energy, 5 district heat water, 6 water consumption. Home/away cannot be assigned twice in the tested UI.

| ID (decimal) | Data offset | Meaning | Observations |
|---|---:|---|---|
| 44 | 2 | Energy pulse factor, raw / 10 kWh | 05 = 0.5, 0F = 1.5 |
| 44 | 4 | District heat water litres/pulse | 0C = 12, 64 = 100; UI max 100 |
| 44 | 18 | Consumption water litres/pulse | 11 = 17; UI max 100 |
| 47 | 4 | Consumption alarm monitoring interval, minutes | 00 to 1E = 30; UI max 99 |
| 47 | 6 | Pump indication | 00 overload protection, 01 running status |

Offsets are zero-based after the echoed ID. Observed byte changes establish scaling, not necessarily full field width. Preserve adjacent unknown bytes. Inactive pulse settings persist across function changes. ID17 offset 17 changed 63 to 02 in energy mode and back in district water mode; offset 18 changed 63 to 02 in consumption mode. Exact semantics remain unknown.

Pump alarm experiment: changing indication to running status with open input triggered LCD alarm and buzzer; OK silenced buzzer but LCD alarm remained; reverting indication removed LCD alarm. ID43 header 02 → 06 → 02 → 02. Bit 2 is a candidate unacknowledged-alarm indicator for this response, not a global alarm flag. IDs 96–101 still returned 06 after LCD alarm cleared. ID46 retained timestamp 2026-11-27 11:50:01 after acknowledgement and clearance; history interpretation remains provisional. Physical input states, polarity, names, pulse counters and active alarm encoding remain unresolved. Read mapping only; no new write validation.

## Measurement 6 and pressure (firmware 2.15, 2026-11-27)

ID17 appears to be a measurement routing table: data byte value 05 selects physical input 6 (inferred zero-based numbering); 0C appears unassigned. LCD selection moves 05 between offsets 8 (L2 room), 9 (free temperature measurement, factory cold water), 11 (wind compensation), 19 (network pressure). Other tested routing slots revert to 0C. Disabled selection not independently tested in this series. Renaming free measurement to VESI did not expose a matching ASCII payload. ID27 is context-dependent: temperature mode uses S16BE /100 °C with disconnected sentinel 865A; wind mode returned 26FC (9980), percentage scaling remains candidate only; pressure mode uses two-byte BE /100 bar, observed 0320 = 8.00 and 0258 = 6.00. In L2 room mode with disconnected sensor, ID15 offsets 16/23/26 changed to 4A/CC/46; final L2 target rose from 48 to 70°C and returned to 48 on switching to free temperature. Exact correction semantics remain provisional.

| ID (decimal) | Data offset | Meaning | Observed encoding |
|---|---:|---|---|
| 12 | 15 | Compensation/measurement signal minimum | U8 %, 00→0D |
| 12 | 16 | Compensation/measurement signal maximum | U8 %, 64→57 |
| 14 | 11 | Same minimum, synchronized by LCD | U8 %, 00→0D |
| 14 | 12 | Same maximum, synchronized by LCD | U8 %, 64→57 |
| 47 | 0 | Pressure measurement range | U8 /10 bar, 50→3C |
| 47 | 1 | Upper pressure alarm | U8 /10 bar, 16→23 |
| 47 | 2 | Filling alarm | U8 /10 bar, 07→0D |
| 47 | 3 | Lower pressure alarm | U8 /10 bar, 05→09 |

Offsets zero-based after echoed ID. Pressure settings changed individually on LCD: 8.0→6.0, 2.2→3.5, 0.7→1.3, 0.5→0.9 bar. ID47 offset 4 remains 1E (30 min consumption interval). Wind min/max restored to 0/100 before pressure test. Serial synchronization of duplicated min/max fields not tested.

ID54 offset 0–1 BE /1000 bar is a candidate second pressure value: 1F40→1A90→1770 (8.000→6.800→6.000) while ID27 0320→02C6→0258 (8.00→7.10→6.00). Different response times suggest filtering, but scans are sequential, not simultaneous; exact semantics, signedness and physical calibration are unverified. Disconnected bench input reported full-scale pressure and triggered LCD upper alarm; do not interpret this as a real pressure measurement. Header 06 observed but not a reliable global alarm flag. No serial writes tested for these fields.

### 2026-11-27 — Bus measurement and stale-value checkpoint (firmware 2.15)

ID17 data offsets are zero-based, excluding the echoed address and ID. Routing code 0x0B (bus) was observed at offset 8 (L2 room), 11 (wind), and 12 (solar); disabling each restored 0x0C. Physical measurement 6 uses 0x05. Disabling measurement 6 restored offset 19 to 0x0C and ID27 to 00 00, but ID54 retained 17 70 (consistent with the previous 6.0 bar reading). Outdoor bus selection was refused as channel already occupied; L1 room, energy and water bus routing remain unverified. Actual LCD menu includes wind and solar separately, not S-compensation. Dig3 remained configured for energy during bus tests (ID43 04 03).

L2 bus without a source produced a room error and ID15 final L2 target rose from 48 to 70 °C; disabling restored 48 °C. Wind bus without a source displayed 96.1 m/s with an alarm; encoding remains unknown. Solar bus selection unexpectedly displayed a network pressure alarm at 6.0 bar despite pressure routing being disabled. After disabling solar and acknowledging, operator confirmed the alarm disappeared; ID54 still retained 17 70. Suspected firmware defect or stale alarm handling, not a proven root cause. Do not treat ID54 alone as live pressure or infer valid bus measurements from routing alone. ID46 timestamp and response header flags are not reliable universal alarm indicators.

Manual Dig3 energy pulses at 1.0 kWh/pulse changed LCD instantaneous power but did not establish a serial power or energy field; IDs60/61 remain unidentified. Continuous pulse scan had missing responses at IDs46,54,59; cause unknown. Defer until controlled pulse generator testing. Across ten checkpoint captures, 2557 present TX/RX frames passed STX, length, SUM8 and ID echo checks; three responses were absent. No serial writes performed. ESPHome remains read-only; portable restore must exclude stale/live measurements and alarm state. Bus routing writes are not validated.

## 2026-11-27 checkpoint: remaining settings, GSM and DHW boost

Bench firmware 2.15, read-only captures. Data offsets exclude the two-byte response payload prefix.

- Room temperature delay: ID12 offset20 and ID14 offset16 both 05 -> 0F for 0.5 -> 1.5 h; U8 /10 h, UI 0–2 h in 0.5 h steps. LCD synchronizes both copies; serial write synchronization untested.
- Power limit: ID44 offsets5–6 U16BE, 03 E7 -> 01 41 for 999 -> 321 kW; UI 0–999 kW, step 1. Zero semantics unknown. Subsequently restored to 999.
- GSM device ID: ID95 offset0 00 -> 01 enables ID; offsets1–4 ASCII four digits (1234 tested), preserve leading zeros; offsets5–10 ASCII EH-203 model designation, unchanged. SMS protocol role of model string unknown. GSM1 number accepted by long OK press, retained on menu reentry without GSM module, but no serial storage field identified. Editor accepts digits, + and comma. GSM2, maximum length and power-cycle persistence untested. Do not publish real phone numbers.
- Finnish/Swedish language selection has no identified field in current read scan. Trend display is live data, not a portable setting.
- ID16 offset4 DHW boost 00 -> 05, UI 0–25 °C; offset6 DHW high alarm 41 -> 48 (65 -> 72 °C), UI 65–120 °C. Adjacent preceding bytes at offsets3 and5 are zero; U16BE layout plausible but high-byte meaning unverified. Distinguish high alarm from deviation alarm at offsets23–24.
- ID42 offset0 low nibble DHW operating mode: 00 auto, 04 mechanical manual, 05 electrical manual, 06 no boost, 07 continuous boost. Non-auto warning appeared on LCD; no reliable serial warning flag established. Auto restored in lv_schedule capture.
- DHW boost schedule confirmed in shared heating table ID4/5 and ID6/7: with 14 existing L1/L2 events, ID6 offsets1–2 = 04 51 (1105 min, 18:25), offsets3–4 = 04 D3 (1235 min, 20:35); ID7 offsets0–1 = 15 2A (Mon/Wed/Fri and Tue/Thu/Sat), offsets14–15 = 12 22 (boost on/off). Event high nibble 1 on, 2 off; low nibble 0 L1, 1 L2, 2 DHW, 3 relay1, 4 relay2. Relay events observed in ID8/9. ID10/11 role and total capacity remain unconfirmed.
- All eleven checkpoint captures contain 128 records, 72 accepted and 56 rejected each. All 2816 TX/RX frames passed STX, length, SUM8, ID echo and payload correspondence checks. This is structural validation, not proof of every semantic mapping.
- No new serial writes validated. ESPHome/HA remains strictly read-only. Portable backup may represent identified persistent settings and schedules; restoration remains restricted to write-tested fields, preserving unknown bytes and excluding live operating overrides. Next open investigation: relay temperature-control hysteresis.

## 2026-11-27 checkpoint: command space and alarm experiments

Bench firmware 2.15. Relay temperature-control hysteresis changed from 1 to 10 °C on LCD and retained after reboot (operator observation); the two scans differ only in IDs 2, 3, 25, 36, 38 (clock/measurement data). No serial field identified; do not confuse it with ID44 offset28 or burner hysteresis. ID54 stale pressure value cleared on reboot.

- Command sweep: MODE=0, ID=1, all command bytes except 82 and 84. 254 probes, 27 controls; 237 rejected and 17 accepted probes. Commands 81,89,91,99,A1,A9,B1,B9,C1,C9,D1,D9,E1,E9,F1,F9 returned ID1. Mask (command & 0x87)==0x81 describes these observed aliases only, not a general decoder guarantee. 85 returned ID46 once. Separate 80/83/85 probes rejected. MODE 2,128,255 with 81/ID1 returned the same identity as MODE0; no general MODE semantics established.
- Single 84/ID1 probes sometimes returned ID46, including during active pump alarm; other attempts including fresh alarm rejected. 84/ID0 and 85/ID1 or ID46 rejected during active alarm. Neither command demonstrated LCD alarm acknowledgement. ID46 data from accepted 84 matched subsequent 81/ID46. Do not label 84/85 as confirmed read or acknowledgement commands.
- Three ID sweeps: 84 and 85, MODE0, IDs 0–255, starting states active unacknowledged, active acknowledged, clear. Each had 512 rejected probes and 108 successful controls (54 identity, 54 ID46); all 1536 probes rejected. Header counts (hex): unack 01:512,02:106,2E:1,3A:1; ack 01:512,02:108; clear 01:511,02:106,2E:1,32:1,39:1. Exceptional headers cluster at start; bit5 is not a reliable active alarm indicator. ID46 payload constant within each sweep; unack/ack identical, clear differs only timestamp (15:01:22 to 15:06:25 controller time). Initial state labels are operator observations, not continuously verified state.
- Structural revalidation of four JSONL sweeps and 14 single probes: 4310 TX/RX frames, zero STX/length/SUM8 failures. Post-command-sweep scan compared to reboot scan: only IDs 2,3,25,36,38,46 payloads changed; no observed persistent setting change in that comparison, not proof of absence of side effects.
- Open hypothesis: event flags or queue may be consumed by traffic; initial 81 controls could influence subsequent probes. Original MODBUS-200/EH-485 accessory may use a different transaction sequence or active protocol translation between controller-side serial interface and external RS-485 bus. Not verified; RS-485 electrical signaling alone does not establish Modbus framing on the controller side. Future work: passive capture on verified electrical interfaces of original accessory, compare both sides, no injection on production bus.
- Production ESPHome/HA and backup acquisition use canonical 81 only. No reliable alarm-state sensor yet. Unknown opcodes and aliases remain bench-only; no new write fields approved. Next implementation: raw backup and portable known-settings representation, followed by guarded restore using existing write-tested allowlist, preserving unknown bytes and excluding identity/live state. Unknown alarm commands and hysteresis mapping are not blockers.


### B3.3 monitoring evidence (firmware 2.15 bench)

IDs below are decimal. Signed big-endian temperature / 100; existing missing-sensor sentinel handling applies.

| ID | Interpretation | Evidence |
|---|---|---|
| 23 | L1 return | LCD comparison: 24.2 vs 24 C; provisional |
| 24 | DHW supply (T7) | T7 resistor change, 52.3 to 25.1 C; LCD 25 C |
| 25 | DHW circulation/anticipation (T8) | Remained near 52.5 C during T7 change; LCD 53 C; no independent T8 perturbation |
| 26 | L2 supply | LCD comparison: 41.5 vs 42 C; provisional |
| 33 | Input 9, default L2 return | LCD comparison: 21.4 vs 21 C; provisional; input may be relabelled |

T7 replacement resistor retained on the isolated bench to distinguish DHW channels. IDs 49/50 remained zero during the manual-control test; do not expose as verified percentages. No new write operations authorized.

## Parallel shift: mirrored curve fields (firmware 2.15)

IDs are decimal; offsets are zero-based payload offsets.

| Parameter | Settings field | Automatic curve mirror | Encoding |
|---|---|---|---|
| L1 parallel shift | ID 12, offset 27 | ID 65, offset 9 | signed int8, 1 °C/LSB |
| L2 parallel shift | ID 14, offset 23 | ID 66, offset 9 | signed int8, 1 °C/LSB |

Physical bench observations on 2026-11-28: L1 -5 then -3 °C; L2 -4 °C. Both mirror predictions passed full restore-block readback and LCD comparison. The curve bytes are derived mirrors, not independent writable fields. Initial mirror mismatch blocks a shift change; restore additionally checks source consistency. Persistence and broader physical regression remain pending.
