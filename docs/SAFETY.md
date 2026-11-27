# Safety and data handling

This is reverse-engineering research on a heating controller, **not an approved controller replacement or commercial service tool**.

- Use a bench controller where possible. A heating installation may control circulation, valves, DHW temperatures and safety alarms.
- The scanner remains **read-only**. The experimental writer is bench-only, with narrow tested ranges, identity check, durable local logs and explicit confirmation. ID 2 clock writing is verified on the bench; ID 13 L1 room setpoint write and persistence are also verified; general restore safety is not established.
- Do not auto-acknowledge or suppress alarms.
- Treat invalid sensor readings as unavailable, not real temperatures: `0x865A` was observed for a disconnected temperature channel.
- Treat all unknown registers as opaque; never write or clone them into another controller.
- Any future restore must verify compatible controller model and firmware; exclude serial numbers, calibration, hardware-specific data and unknown bytes.
- A future backup/restore must have a preview, explicit user confirmation, target snapshot, per-field allowlist, read-after-write verification and failure handling.
- Preserve immutable raw captures; check that captured serial numbers or other installation-specific details are appropriate for publication. The repository is **public**.
- A successful read does not prove that the same field can safely be written.

- Avoid periodic or redundant writes: nonvolatile memory technology and endurance are unknown. Write only changed, explicitly allowlisted settings and verify readback.
## Backup and restore boundary

Read-only raw snapshot of IDs 0–255 is feasible now. A portable configuration export must separately classify confirmed fields, mirrors, live values, identity and unknown data. Restore only independently write-tested allowlisted fields, with target snapshot, compatibility check, explicit diff/approval, read-modify-write, durable journal and full readback; never blindly replay raw blocks. Curve IDs 65/66 are canonical candidates; ID 65 Y3 mirror into ID 12 verified, other directions untested. General restore remains unvalidated. Next: operating modes, writer tests and staged bench restore.

## Integration separation (2026-11-27)

ESPHome/Home Assistant must remain strictly read-only, with no write service or command 0x82. Manual actuator experiments require disconnected loads on the bench. ID 51 is a command, not physical feedback. Schedule and operating-mode serial writes are unvalidated and excluded from restore. Stop on mismatch or uncertain state; do not automatically retry or roll back.

## Relay-specific boundaries

Keep relay loads disconnected during bench experiments. Relay configuration can be coupled (230 V motor mode reserves both relays); do not independently replay configuration bytes. Exclude live overrides, countdowns and commanded states from portable backup/restore. Weekly schedules and persistent relay settings are read-mapped only, not write-validated. Relay names and temperature-control hysteresis are not yet readable through the mapped interface. Do not claim a complete portable backup.

## Digital input restore boundary

Mapped digital input functions, pulse factors, consumption interval and pump indication are candidates for portable configuration, not validated write targets. Preserve unknown adjacent bytes and inactive settings. Respect UI exclusivity and automatic measurement configuration dependencies. Changing pump indication can trigger a real alarm. Do not restore live alarm flags, timestamps, counters or acknowledgement state. Do not expose a header bit as an active-alarm safety sensor. ESPHome/Home Assistant must remain read-only.

## Measurement 6 boundaries

Decode ID27 only with known measurement routing. Disconnected pressure input can report plausible full-scale pressure; do not assume sensor validity or use these readings as a safety interlock. ID54 semantics and physical calibration are unverified. L2 room routing with disconnected sensor changed calculated supply target to 70°C on bench. Routing and duplicated compensation limits have dependencies; pressure settings and routing remain excluded from write allowlist until independently validated. Preserve unknown bytes, do not restore live readings or alarm history. ESPHome/HA remains read-only.

### 2026-11-27 — Bus measurement and stale-value checkpoint (firmware 2.15)

ID17 data offsets are zero-based, excluding the echoed address and ID. Routing code 0x0B (bus) was observed at offset 8 (L2 room), 11 (wind), and 12 (solar); disabling each restored 0x0C. Physical measurement 6 uses 0x05. Disabling measurement 6 restored offset 19 to 0x0C and ID27 to 00 00, but ID54 retained 17 70 (consistent with the previous 6.0 bar reading). Outdoor bus selection was refused as channel already occupied; L1 room, energy and water bus routing remain unverified. Actual LCD menu includes wind and solar separately, not S-compensation. Dig3 remained configured for energy during bus tests (ID43 04 03).

L2 bus without a source produced a room error and ID15 final L2 target rose from 48 to 70 °C; disabling restored 48 °C. Wind bus without a source displayed 96.1 m/s with an alarm; encoding remains unknown. Solar bus selection unexpectedly displayed a network pressure alarm at 6.0 bar despite pressure routing being disabled. After disabling solar and acknowledging, operator confirmed the alarm disappeared; ID54 still retained 17 70. Suspected firmware defect or stale alarm handling, not a proven root cause. Do not treat ID54 alone as live pressure or infer valid bus measurements from routing alone. ID46 timestamp and response header flags are not reliable universal alarm indicators.

Manual Dig3 energy pulses at 1.0 kWh/pulse changed LCD instantaneous power but did not establish a serial power or energy field; IDs60/61 remain unidentified. Continuous pulse scan had missing responses at IDs46,54,59; cause unknown. Defer until controlled pulse generator testing. Across ten checkpoint captures, 2557 present TX/RX frames passed STX, length, SUM8 and ID echo checks; three responses were absent. No serial writes performed. ESPHome remains read-only; portable restore must exclude stale/live measurements and alarm state. Bus routing writes are not validated.
