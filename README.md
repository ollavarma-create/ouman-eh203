# Ouman EH-203 Manager

An independent, open-source project developing a desktop application for monitoring, diagnostics, configuration management, backup and restoration of Ouman EH-203 heating controllers via native RS-232.

The goal is to extend the useful service life of existing controllers with modern, local-first maintenance tools. Systematic reverse engineering and controlled bench experiments produced the protocol documentation and Python core that form the foundation of this application.

## Current status

The Python core alpha (0.1.0a1) is implemented; the PySide6 desktop GUI is planned, not yet released. Firmware 2.15 is the tested baseline. The core captures all 256 IDs, validates independent backups, exports 82 decoded parameters and supports restricted bench restoration with journaling and reboot verification. One physical acceptance run completed 16 writes with zero remaining planned writes after reboot. The last reported baseline was 91 passing tests. Factory comparison: 53 matches, zero differences, 29 without documented defaults.

## Desktop roadmap

- Monitoring: live measurements, heating curves, trends, schedules and diagnostics where mappings are verified.
- Configuration: backup, verification, comparison, guided restricted restoration and individually validated parameter editing.
- Finnish and English UI, offline backup inspection and simulator.
- Context-sensitive help, LCD menu paths and page references; user-configurable manual URLs and local PDF import.
- No telemetry, mandatory cloud services or bundled manufacturer manuals.

See [GUI roadmap](docs/GUI_ROADMAP.md), [core engine](docs/CORE_ENGINE.md), [backup workflow](docs/BACKUP.md) and [safety rules](docs/SAFETY.md).

## Getting started with the existing core

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
ouman-eh203 --help
ouman-eh203 metadata --lang fi
```

## Research and protocol documentation

- [Research status](docs/RESEARCH_STATUS.md)
- [Protocol framing](docs/PROTOCOL.md)
- [Parameter map](docs/PARAMETER_MAP.md)
- [Hardware and test setup](docs/HARDWARE.md)
- [Capture inventory](research/CAPTURE_MANIFEST.md)
- [Read-only scanner](research/scripts/scan.py)

The native serial interface (4800 8N1) is not Modbus RTU. Native IDs are not Modbus register addresses. Mappings distinguish confirmed, inferred and unknown fields. Read-only is the default; writes require independently validated transitions and verification. Production restoration and unrestricted editing are not supported.

ESPHome/Home Assistant monitoring is planned as a separate, strictly read-only project; no separate repository is claimed to exist yet.

This project is not affiliated with or endorsed by Ouman. See [LICENSE](LICENSE). Manufacturer manuals are obtained directly from the manufacturer or supplied locally by the user.

## Historical research checkpoints

The following records describe earlier experiments, not current feature status.

See the [original research README](docs/RESEARCH_README_2026-11-27.md) for the complete historical record.
