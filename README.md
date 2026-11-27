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

## 2026-11-27 checkpoint: command space and alarm experiments

Bench firmware 2.15. Relay temperature-control hysteresis changed from 1 to 10 °C on LCD and retained after reboot (operator observation); the two scans differ only in IDs 2, 3, 25, 36, 38 (clock/measurement data). No serial field identified; do not confuse it with ID44 offset28 or burner hysteresis. ID54 stale pressure value cleared on reboot.

- Command sweep: MODE=0, ID=1, all command bytes except 82 and 84. 254 probes, 27 controls; 237 rejected and 17 accepted probes. Commands 81,89,91,99,A1,A9,B1,B9,C1,C9,D1,D9,E1,E9,F1,F9 returned ID1. Mask (command & 0x87)==0x81 describes these observed aliases only, not a general decoder guarantee. 85 returned ID46 once. Separate 80/83/85 probes rejected. MODE 2,128,255 with 81/ID1 returned the same identity as MODE0; no general MODE semantics established.
- Single 84/ID1 probes sometimes returned ID46, including during active pump alarm; other attempts including fresh alarm rejected. 84/ID0 and 85/ID1 or ID46 rejected during active alarm. Neither command demonstrated LCD alarm acknowledgement. ID46 data from accepted 84 matched subsequent 81/ID46. Do not label 84/85 as confirmed read or acknowledgement commands.
- Three ID sweeps: 84 and 85, MODE0, IDs 0–255, starting states active unacknowledged, active acknowledged, clear. Each had 512 rejected probes and 108 successful controls (54 identity, 54 ID46); all 1536 probes rejected. Header counts (hex): unack 01:512,02:106,2E:1,3A:1; ack 01:512,02:108; clear 01:511,02:106,2E:1,32:1,39:1. Exceptional headers cluster at start; bit5 is not a reliable active alarm indicator. ID46 payload constant within each sweep; unack/ack identical, clear differs only timestamp (15:01:22 to 15:06:25 controller time). Initial state labels are operator observations, not continuously verified state.
- Structural revalidation of four JSONL sweeps and 14 single probes: 4310 TX/RX frames, zero STX/length/SUM8 failures. Post-command-sweep scan compared to reboot scan: only IDs 2,3,25,36,38,46 payloads changed; no observed persistent setting change in that comparison, not proof of absence of side effects.
- Open hypothesis: event flags or queue may be consumed by traffic; initial 81 controls could influence subsequent probes. Original MODBUS-200/EH-485 accessory may use a different transaction sequence or active protocol translation between controller-side serial interface and external RS-485 bus. Not verified; RS-485 electrical signaling alone does not establish Modbus framing on the controller side. Future work: passive capture on verified electrical interfaces of original accessory, compare both sides, no injection on production bus.
- Production ESPHome/HA and backup acquisition use canonical 81 only. No reliable alarm-state sensor yet. Unknown opcodes and aliases remain bench-only; no new write fields approved. Next implementation: raw backup and portable known-settings representation, followed by guarded restore using existing write-tested allowlist, preserving unknown bytes and excluding identity/live state. Unknown alarm commands and hysteresis mapping are not blockers.
