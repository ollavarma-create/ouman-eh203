# Ouman EH-203 native serial protocol — independent research

An experimental, **unofficial** reverse-engineering project for the Ouman EH-203 heating controller (tested on firmware **2.15**). The goal is to preserve reproducible evidence, build read-only diagnostics, and eventually support strictly read-only ESPHome/Home Assistant. A possible settings backup/restore tool is a **future research objective**, not an implemented feature.

**Project status (2026-11-27):** Native RS-232 **4800 8N1** read requests and checksums are known; many temperature measurements and configuration fields are mapped by controlled LCD-setting experiments. **A single clock write (ID 2, command 0x82) has been verified on the bench with readback.** ID 13 L1 room setpoint write, full-block readback, LCD confirmation and operator-confirmed power-cycle persistence are also established. Bench writes also verified for L1 gain, curve Y3/X2 and DHW setpoint; general restore remains experimental. Operating modes, DHW command percentage and weekly schedule read layouts are now mapped.

Start with:
- [Research status and next experiment](docs/RESEARCH_STATUS.md)
- [Protocol framing](docs/PROTOCOL.md)
- [Confirmed parameters](docs/PARAMETER_MAP.md)
- [Hardware and test setup](docs/HARDWARE.md)
- [Safety rules](docs/SAFETY.md)
- [Capture inventory](research/CAPTURE_MANIFEST.md)

A simple read-only Python scanner is in [research/scripts/scan.py](research/scripts/scan.py). It requires `pyserial` and does not change settings.

## Important boundaries

The EH-203 native serial interface is **not Modbus RTU**. The official EH-203 Modbus template and `EH-203.dev` file describe a *different interface*. Native parameter IDs must not be interpreted as Modbus register addresses.

All mappings distinguish **confirmed by changing one LCD setting** from **candidate, inferred or unknown**. Even confirmed byte mappings may be firmware-dependent. Read-only exploration is the default; experimenting with writes on a heating installation could affect safety.

## Longer-term vision

1. Reproducible protocol documentation and captures.
2. Python read-only status/diagnostics.
3. ESP32 + MAX3232 ESPHome component and Home Assistant entities.
4. Only after independent write-command validation: selective, model-aware settings backup/restore with verification and rollback safeguards.

This repository is not affiliated with or endorsed by Ouman. See [LICENSE](LICENSE).

ID 12 L1 room compensation gain write (5.0→4.9) also verified by full-block readback and LCD.

## Experimental bench writer

`python research/scripts/write_parameter.py --parameter l1_room_gain --expect 4.9 --value 5.0 --dry-run`

Remove `--dry-run` only on the bench and explicitly confirm. The writer allowlist is limited to tested transitions: gain 4.9–5.0, room setpoint 25.0–25.1°C, L1 curve Y3 25–26°C, X2 −12 to −11°C and DHW setpoint 58.0–58.1°C. Identity check requires EH-203 firmware 2.15. Logs (including original block and serial number) are saved in `write-captures/`; keep private unless approved. No automatic retries or rollback. Run tests with `python -m unittest discover -s tests`.

## Integration and backup roadmap

ESPHome/Home Assistant will remain read-only (0x81 only). A separate backup/editor application will handle selective settings migration; no general restore or schedule writing is implemented. See the [research status](docs/RESEARCH_STATUS.md) for the November 27 findings.

## Relay research update

Relay configuration, weekly schedules, commanded states, temporary overrides and burner settings are mapped in the [parameter map](docs/PARAMETER_MAP.md). Relay names and temperature-control hysteresis remain unresolved. All IDs 128–255 were rejected again with burner control active on firmware 2.15. Next: digital inputs. Relay writes remain untested.

### Digital input research checkpoint (2026-11-27)

Digital input function selection, energy/water pulse factors, consumption monitoring interval and pump indication are now mapped for the tested firmware 2.15. Pump alarm acknowledgement and clearance were observed, but active alarm encoding remains unresolved. See [parameter map](docs/PARAMETER_MAP.md) and [research status](docs/RESEARCH_STATUS.md). ESPHome/Home Assistant remains read-only; newly mapped settings are not automatically write-enabled.

### Measurement 6 checkpoint (2026-11-27)

Measurement routing, wind compensation signal limits and all four pressure configuration fields are mapped by LCD experiments. Pressure readings are context-dependent; ID54 interpretation and physical calibration remain provisional. See [parameter map](docs/PARAMETER_MAP.md). Next: disabled measurement selection and energy/pulse counters. ESPHome remains read-only.
