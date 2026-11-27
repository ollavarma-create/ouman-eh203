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
