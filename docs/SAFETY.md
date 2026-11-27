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
