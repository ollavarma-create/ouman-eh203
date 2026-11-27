# Native serial protocol (experimental)

## Wire parameters
RS-232 electrical levels, **4800 baud, 8 data bits, no parity, 1 stop bit**, no RTS/CTS, DSR/DTR or XON/XOFF flow control. This is **not TTL UART** and is **not Modbus RTU**.

## Observed read request
```text
02 81 02 00 PP CC
STX  operation?  length?  reserved?  parameter ID  checksum
```
Only the read request's exact bytes are proven; names of intermediary fields are provisional. `CC=(0x81+0x02+0x00+PP)&0xFF`.

Example reading parameter 18 (`0x12`): `02 81 02 00 12 95`.

## Observed response
```text
02 HH NN 00 PP DD ... DD CC
```
- `HH` varies (`02`, `06`, etc.); **do not assign alarm semantics**.
- `NN` is the response's logical length; full frame is `NN+4` bytes.
- The `00 PP` prefix echoes the parameter ID for accepted responses.
- Data starts at absolute frame offset **5** (zero-based). Thus `frame_offset=data_offset+5`.
- `CC=sum(frame[1:-1])&0xFF`.
- The rejected response includes `00 FF` instead of `00 PP` and has `NN=02`: e.g. `02 01 02 00 FF 02`.
- Do not rely on the response header's exact value to decide success.

Example ID 18 normal outdoor temperature `-4.10°C`:
```text
02 02 04 00 12 FE 66 7C
```
Data `FE 66` is signed big-endian int16 `-410`; divide by 100. At sensor-disconnection a raw `86 5A` was observed and must be treated as invalid rather than -311.42°C.

Other observed response sizes include ID 98 and 99, each 188 bytes (182 data bytes). Size receiving buffers for a full response, and do not assume every ID has a 31-byte data field.

## Parser invariants
1. STX must equal `0x02`.
2. Read first three bytes, then `length+1` additional bytes.
3. Enforce full length == `length+4` and validate checksum.
4. Before using a response, verify the `00 PP` echo (or handle the `00 FF` rejection).
5. Preserve raw bytes and metadata for offline re-analysis; timestamps and changing sensor values are not setting changes.
6. Start with read-only operations. Clock and ID 13 room setpoint writes are verified; other configuration writes and recovery remain untested.

## Open protocol questions
- Meaning of response header bits and changing event/status bytes.
- Whether addressing above single-byte IDs exists.
- Configuration-block write semantics, rejection handling and persistence.
- Read/transfer semantics for large blocks and any hidden EEPROM/configuration areas.
- Firmware-dependent layouts.

## Observed write request

`02 82 NN 00 PP DATA... CC`, where NN = data length + 2 and CC is SUM8 excluding STX. Acknowledge by checking length, checksum and echoed ID, then independently read back. ID 2 clock, ID 12 L1 room compensation gain and ID 13 L1 room setpoint writes are verified.

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

## ID 65 L1 five-point curve Y3 serial write — 2026-11-26

Dry run `ouman-write-fo016u6o.json`; actual write `ouman-write-lxoj52t3.json`. Firmware 2.15, Y3 25→26°C at ID 65 data offset 3. All 16 actual TX/RX frames independently validated for STX, length, SUM8 and echoed ID. Write ACK `02 06 02 00 41 49`. Full 31-byte readback matches proposed block; only offset 3 changes 19→1A. ID 12 mirror automatically changes only offset 1 from 19→1A without an ID 12 write. Operator confirms LCD 0°C=26°C. Persistence and restoration not yet tested. This proves synchronization for this field and direction only. Raw JSON remains local.

## ID 65 Y3 persistence and restoration — 2026-11-26

Operator confirmed LCD 0°C=26°C after power cycle. Post-cycle dry run `ouman-write-kw8vnk5z.json` shows ID 65 offset 3 and ID 12 offset 1 both 1A. Restoration `ouman-write-7x8hhuye.json` 26→25°C: all 16 TX/RX frames independently validated with Python for STX, length, SUM8 and echoed ID; proposed/readback match, only ID 65 offset 3 and ID 12 offset 1 change 1A→19. ACK `02 02 02 00 41 45`. Operator confirms LCD restoration with a small unmeasured display delay. Automatic mirror synchronization verified for increasing and decreasing Y3 via ID 65, not reverse ID 12 writes or other points. No post-restoration power cycle reported. Raw JSON not committed.

## ID 65 signed X2 experiment — 2026-11-26

Dry run `ouman-write-k2wni0jf.json`, write `ouman-write-cx2byrsk.json`, restoration `ouman-write-n32yr9lf.json`. X2 −12→−11→−12°C, signed byte at offset 6 F4→F5→F4. Both actual logs report verified and operator confirms LCD. ID 12 remains byte-identical in both directions. Restoration independently validated in Python: all 16 frames pass STX, length, SUM8 and ID echo; proposed equals readback, only offset 6 changes. X2 power-cycle persistence not separately tested. Raw logs not committed.

## ID 16 DHW setpoint write experiment — 2026-11-26

Dry run `ouman-write-xo_bodgm.json`, actual write `ouman-write-lt3_h3d1.json`, restoration `ouman-write-gri329gh.json`. U16BE offsets 1–2, scale 0.1°C, 58.0→58.1→58.0°C (0244→0245→0244). Both actual logs report verified; operator confirmed LCD both ways, restoration immediately visible. Restoration independently checked in Python: 10/10 frames pass STX, length, SUM8 and ID echo, write payload and readback match proposed, only offset 2 changes. ACK `02 06 02 00 10 18`. Persistence not separately tested. Raw logs not committed.

## 2026-11-27 read-only payload discoveries

IDs 42, 51 and weekly schedule pairs 4/5 and 6/7 are decoded in [PARAMETER_MAP.md](PARAMETER_MAP.md). LCD experiments do not establish serial write semantics. ESPHome/HA must use 0x81 exclusively. Header variations remain uninterpreted.

## Relay read-only discoveries

IDs 8/9, 14, 44, 45, 58 and 59 are documented in [PARAMETER_MAP.md](PARAMETER_MAP.md). With burner control active, all IDs 128–255 returned the valid rejection frame `02 01 02 00 FF 02`. This does not establish behavior on other firmware or commands. No relay serial writes tested.

## Digital input and alarm response observations

ID43 packs three digital input function nibbles (Dig1 low and Dig2 high nibble of data byte 1; Dig3 low nibble of byte 0). See PARAMETER_MAP.md for codes. In the pump alarm experiment ID43 response header changed 02 → 06 on alarm, then 02 on LCD acknowledgement while the alarm remained displayed, and stayed 02 after clearance. Do not interpret header bit 2 globally: IDs 96–101 returned 06 even after clearance. ID46 retained its timestamp after acknowledgement and clearance; its exact event semantics are unknown. Header values must not be used alone to infer active alarms.

## Measurement 6 context-dependent decoding

ID17 routing offsets 8/9/11/19 select L2 room/free temperature/wind/pressure respectively when set to 05. ID27 cannot be decoded as temperature unconditionally: pressure mode uses BE /100 bar; wind scaling unverified. ID54 candidate BE /1000 bar in pressure mode. ID47 offsets 0–3 pressure settings /10 bar. See PARAMETER_MAP.md for evidence and limitations. LCD changes do not validate serial writes.

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
