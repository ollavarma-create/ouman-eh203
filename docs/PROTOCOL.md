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
6. Start with read-only operations. Clock write framing is verified; configuration writes and recovery remain untested.

## Open protocol questions
- Meaning of response header bits and changing event/status bytes.
- Whether addressing above single-byte IDs exists.
- Configuration-block write semantics, rejection handling and persistence.
- Read/transfer semantics for large blocks and any hidden EEPROM/configuration areas.
- Firmware-dependent layouts.

## Observed write request

`02 82 NN 00 PP DATA... CC`, where NN = data length + 2 and CC is SUM8 excluding STX. Acknowledge by checking length, checksum and echoed ID, then independently read back. Only ID 2 clock writing is verified.

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
