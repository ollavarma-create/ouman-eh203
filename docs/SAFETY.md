# Safety and data handling

This is reverse-engineering research on a heating controller, **not an approved controller replacement or commercial service tool**.

- Use a bench controller where possible. A heating installation may control circulation, valves, DHW temperatures and safety alarms.
- Shipped tools remain **read-only**. ID 2 clock writing is verified on the bench; ID 13 L1 room setpoint write and persistence are also verified; general restore safety is not established.
- Do not auto-acknowledge or suppress alarms.
- Treat invalid sensor readings as unavailable, not real temperatures: `0x865A` was observed for a disconnected temperature channel.
- Treat all unknown registers as opaque; never write or clone them into another controller.
- Any future restore must verify compatible controller model and firmware; exclude serial numbers, calibration, hardware-specific data and unknown bytes.
- A future backup/restore must have a preview, explicit user confirmation, target snapshot, per-field allowlist, read-after-write verification and failure handling.
- Preserve immutable raw captures; check that captured serial numbers or other installation-specific details are appropriate for publication. The repository is **public**.
- A successful read does not prove that the same field can safely be written.

- Avoid periodic or redundant writes: nonvolatile memory technology and endurance are unknown. Write only changed, explicitly allowlisted settings and verify readback.
