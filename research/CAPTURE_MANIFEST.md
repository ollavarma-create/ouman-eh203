# Raw experiment capture inventory

Each `ouman_*.json` file contains one read-only parameter sweep with entries keyed by queried ID, including `tx`, `rx`, `valid`, `rejected`, `payload` (which includes echoed `00 ID`), and `response_ms`. All files were uploaded into the research chat; this document records their names and experimental meaning. **Raw captures have not yet been committed here**; upload the immutable originals separately.

## Baselines, fault exploration and broad sweep
- `ouman_normal.json`: normal baseline.
- `ouman_fault.json`: outdoor sensor open/fault state.
- `ouman_l1_open.json`: L1 supply sensor open.
- `ouman_l1_ack.json`: L1 supply fault acknowledged.
- `ouman_l1_restored.json`: L1 supply connected again.
- `ouman_scan_64_127.json`: read sweep IDs 64–127.

## L1 and general controller settings
- `ouman_l1_min16.json`: L1 supply minimum 15→16.
- `ouman_l1_max51.json`: L1 supply maximum 50→51.
- `ouman_l1_night3.json`: night reduction 0→3.
- `ouman_l1_shift_minus2.json`: L1 parallel shift 0→−2.
- `ouman_l1_autumn3.json`: autumn drying 2→3.
- `ouman_l1_valveclose20.json`: Vent.keskisulk 19→20.
- `ouman_l1_outdoor_delay3.json`: outdoor-temperature delay 2→3 hours.
- `ouman_l1_trend5.json`: L1 trend sampling 1→5 seconds; change not found in scanned ID range.
- `ouman_l1_p150.json`: L1 P 140→150.
- `ouman_l1_i60.json`: L1 I 50→60 s.
- `ouman_l1_d15.json`: L1 D 0.0→1.5 s.
- `ouman_l1_motor160.json`: L1 actuator travel 150→160 s.
- `ouman_l2_p160.json`: L2 P 140→160.
- `ouman_l1_alarm26.json`: L1 deviation alarm 25→26.
- `ouman_l2_alarm26.json`: L2 deviation alarm 25→26.
- `ouman_alarmdelay61.json`: deviation alarm delay **60→70 minutes**, despite filename suffix `61`.
- `ouman_return_max71.json`: return maximum 70→71 °C.
- `ouman_return_min0_6.json`: return min at 0°C, 5→6.
- `ouman_return_min20_16.json`: return min at −20°C, 15→16.
- `ouman_l1_supply_min0_11.json`: L1 supply min at 0°C, 10→11.
- `ouman_l1_supply_min20_31.json`: L1 supply min at −20°C, 30→31.

## DHW (LV)
- `ouman_lv_setpoint59.json`: DHW setpoint 58.0→59.0.
- `ouman_lv_fastdrive65.json`: DHW fast drive 60→65%.
- `ouman_lv_feedforward150.json`: DHW feedforward 140→150°C.
- `ouman_lv_p80.json`: DHW P 70→80.
- `ouman_lv_i20.json`: DHW I 18→20s.
- `ouman_lv_d15.json`: DHW D 0→1.5s.
- `ouman_lv_alarm26.json`: DHW deviation alarm 25→26.
- `ouman_lv_alarmdelay610.json`: DHW alarm delay 600→610s.

Other source reference files: `EH-203.xml` and `EH-203.dev` describe **Modbus** capabilities, not the native serial byte map. Observe Ouman's copyright/license before redistributing vendor content.

## L2 supply limits
- `ouman_l2_supply_min0_11.json`: 10→11°C at 0°C outdoor.
- `ouman_l2_supply_min20_31.json`: 30→31°C at -20°C outdoor.

- `ouman_l2_min16.json`: ordinary L2 supply minimum 15→16°C.
- `ouman_l2_max71.json`: ordinary L2 supply maximum 70→71°C.

- `ouman_l2_night3.json`: L2 night reduction 0→3°C.
- `ouman_l2_autumn3.json`: L2 autumn drying 2→3°C.

- `ouman_l2_shift_minus2.json`: L2 parallel shift 0→−2°C.
- `ouman_l2_outdoor_delay3.json`: L2 outdoor delay 0→3h.

## L2 tuning continuation
- `ouman_l2_i60.json`: L2 I 50→60s.
- `ouman_l2_d15.json`: L2 D 0→1.5s.
- `ouman_l2_motor160.json`: L2 actuator travel 150→160s.

## Five-point curve experiments (IDs 0–127)
- `ouman_l1_curve0_26.json`: L1 Y3 25→26.
- `ouman_l1_curve_x_minus2.json`: L1 X3 0→−2.
- `ouman_l2_curve0_43.json`: L2 Y3 42→43.
- `ouman_l2_curve_x_minus2.json`: L2 X3 0→−2.
- `ouman_l2_curve_x2_minus11.json`: L2 X2 −10→−11.
- `ouman_l2_curve_x4_11.json`: L2 X4 10→11.
- `ouman_l2_curve_y2_53.json`: L2 Y2 52→53.
- `ouman_l2_curve_y4_32.json`: L2 Y4 31→32.
- `ouman_l2_curve_y1_63.json`: L2 Y1 62→63.
- `ouman_l2_curve_y5_21.json`: L2 Y5 20→21 .

Previous test values were restored during the sequence; filenames identify the newly changed field. 

## Curve-type experiments (IDs 0–127)
- `ouman_curve_type_5point.json`: five-point baseline; L2 Y5 restored to 20°C.
- `ouman_curve_type_3point.json`: selector changed to three-point, IDs 65/66 offset 0 = 1.
- `ouman_curve_type_5point_restored.json`: selector restored to five-point, IDs 65/66 offset 0 = 0; automatic L1 Y2 change 34→31°C confirmed by operator.

## L1 curve completion and restoration
- `ouman_l1_curve_y2_restored34.json`: Y2 31→34°C.
- `ouman_l1_curve_y4_23.json`: Y4 22→23°C.
- `ouman_l1_curve_y1_39.json`: Y1 38→39°C.
- `ouman_l1_curve_y5_21.json`: Y5 20→21°C.
- `ouman_l1_curve_x2_minus11.json`: X2 −12→−11°C.
- `ouman_l1_curve_x4_11.json`: X4 10→11°C.
- `ouman_l1_curve_restored.json`: X4 11→10°C; both curves restored, latest capture. All 128 frames valid; only ID 65 and four timestamp blocks changed versus preceding capture.

## Upper ID range sweep
- `ouman_scan_128_255.json`: all 128 IDs rejected with identical valid response `02 01 02 00 FF 02`; request and response checksums, lengths and payloads independently verified. Median response 26.535 ms. Completes the 0–255 read-command survey (72 accepted, 184 rejected overall).

## L1 room sensor and compensation experiments

Room sensor T3 was simulated with approximately 10 kΩ and enabled using Starttitoiminto (operator confirmed). ID 21 data offsets 0–1 returned 09 C4 (25.00°C, signed BE /100). ID 17 offset 3 changed 0C→02 on activation; offset 11 also changed, so the complete configuration table remains unresolved.

| Capture | Room setpoint °C | Gain | Supply minimum °C | ID 15 offset 1 (signed) | Offset 10 | Offset 14 |
|---|---:|---:|---:|---:|---:|---:|
| ouman_l1_room_sensor_enabled.json | 21.5 | 4.0 | 15 | -13 | 0 | 17 |
| ouman_l1_room_setpoint225.json | 22.5 | 4.0 | 15 | -10 | 0 | 20 |
| ouman_l1_room_comp5.json | 21.5 | 5.0 | 15 | -18 | 3 | 15 |
| ouman_l1_room_comp_min16.json | 21.5 | 5.0 | 16 | -19 | 4 | 16 |

All four captures independently checked for request bytes, response length, checksum, payload consistency and accepted ID echo: 512/512 valid, 72 accepted and 56 rejected per sweep. ID 15 offset 0 remained 28 and offset 6 remained 2. Offset 1 is strongly supported as signed room compensation; offset 10 tracks positive minimum-limit correction (signedness unresolved); offset 14 tracks the final supply target including minimum clamping. The last row's displayed terms sum to 15 rather than 16; independent rounding or time-dependent calculation is possible but not established. No write semantics inferred. L2 equivalents remain candidates.

- `ouman_clock_before.json`: read-only IDs 2 and 3, both 2026-11-26 18:28:16; original not committed.

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

## 2026-11-27 LCD experiments (IDs 0–127)

Capture basenames (JSON, local originals; not committed): baseline_01, baseline_02, l1_continuous_day, l1_auto_restored, l1_continuous_night, l1_down, l1_hand_mech, l1_hand_elec, l2_continuous_day, l2_continuous_night, l2_down, l2_hand_mech, l2_hand_elec, l1_day_l2_night, all_auto_restored, lv_hand_mech, lv_hand_elec, lv_hand_elec_50, lv_hand_elec_26, lv_hand_elec_min, lv_auto_restored, l1_schedule_mon, l1_schedule_multi, l1_schedule_daymask, l2_schedule, schedule_capacity, schedule_delete, schedule_pair_delete. See parameter map and research status for observations. A fresh aggregate audit is pending; no new test-suite result claimed.
