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
- **ID 51**: DHW motor-command percent, matched LCD 100% (not a controlled output sweep).
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
