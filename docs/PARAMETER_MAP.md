# Parameter map

**Index convention:** `data_offset` is zero-based **after** the response's echoed `00 ID` prefix, i.e. absolute `frame_offset=data_offset+5`. For multibyte values use big-endian unless specifically marked otherwise. `confirmed` means the corresponding LCD setting was independently changed and matching byte(s) observed. `candidate` means correlation only.

## ID 12 — L1 configuration (31 data bytes)

| Data offset | Format | Meaning | Status |
|---:|---|---|---|
| 0,1,2 | uint8 | three values 38/25/20 correlated with 3-point curve | candidate |
| 3 | uint8 °C | L1 supply minimum | confirmed 15→16 |
| 4 | uint8 °C | L1 supply maximum | confirmed 50→51 |
| 5 | uint8 °C | night reduction | confirmed 0→3 |
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
| 1–2 | u16 BE, candidate scale 0.1 | L1 first value 215 | unknown |
| 3–4 | u16 BE °C | L1 P band | confirmed 140→150 |
| 5–6 | u16 BE seconds | L1 I time | confirmed 50→60 |
| 7–8 | u16 BE /10 seconds | L1 D time | confirmed 0→15 for 1.5s |
| 9–10 | u16 BE seconds | L1 3-state actuator travel time | confirmed 150→160 |
| 11–12 | u16 BE | L2 first value 215 | unknown |
| 13–14 | u16 BE °C | L2 P band | confirmed 140→160 |
| 15–16 | u16 BE seconds | L2 I time (50 observed) | candidate |
| 17–18 | u16 BE /10 seconds | L2 D time (0 observed) | candidate |
| 19–20 | u16 BE seconds | L2 actuator time (150 observed) | candidate |

The L1 and L2 groups look symmetric but **only L2 P** has been experimentally changed.

## ID 14 — L2 configuration (31 data bytes)

- Data offset **22**, uint8 °C: L2 deviation alarm, **confirmed** 25→26.
- Offset **7**, uint8 °C: L2mv.min(0), **confirmed** 10→11, restored to 10.
- Offset **8**, uint8 °C: L2mv.min(-20), **confirmed** 30→31; restore to 30 at next experiment.
- Other values are not verified; do not copy L1 positional assumptions to L2.

## ID 15 — calculated settings, not fully decoded

- Data offset 6 correlates with the autumn drying adjustment (2→3).
- Data offset 13 changed with the L1 curve parallel shift 0→-2.
- Offset 14 changed in tests consistent with the final L1 target, but complete semantics and scaling remain **hypotheses**.
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
- **ID 65**: L1 five-point curve observed byte offsets 1–5 = `38,34,25,22,20`; offsets 6–8 = `-12,0,10` when read as signed int8. Five curve values agree with the LCD; individual field change experiment pending.
- **ID 66**: appears to contain L2 five-point curve, **candidate only**.

## Confidence and scope

A field's position in a *read response* does **not** imply a writeable field or a safe restore action. Firmware 2.15 only has been tested. Detailed experiment names are in [CAPTURE_MANIFEST.md](../research/CAPTURE_MANIFEST.md).
