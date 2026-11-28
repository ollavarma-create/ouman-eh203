# Ouman EH-203 Manager — GUI roadmap

Updated 2026-11-28. This is a plan, not a released feature list.

## Scope and baseline

Build a bilingual FI/EN PySide6 desktop application on the existing Python core. Target Fedora KDE first; preserve CLI compatibility and optional GUI dependencies. Verify current main and tests before implementation. Firmware 2.15 is the validated bench baseline, not a guarantee of other firmware compatibility.

Two primary sections:
- Monitoring (always read-only): live readings, L1/L2/DHW, actual three/five-point heating curves, trends, schedules, relays and diagnostics where verified. Distinguish stale, unavailable, simulated and offline values. Do not infer reliable alarm state or actual valve position from unverified fields.
- Configuration: full backup, independent verification, comparison, offline inspection, guided restricted bench restoration and individually validated parameter editing.

ESPHome/Home Assistant will be developed separately as a strictly read-only integration using canonical 0x81 requests. No shared serial bridge is in scope.

## Architecture and safety

Qt Widgets views -> central operation manager / QThread worker -> existing core APIs -> protocol/transport -> physical controller or simulator. Exclusive serial operations; pause polling during backup/restore/edit and resume after safe completion. No GUI-thread blocking. Cancellation must explicitly mark incomplete captures or interrupted journals. Never retry uncertain writes automatically or imply rollback. Preserve unknown bytes, identity/live-state exclusions and existing restore restrictions.

Metadata distinguishes read-only, restore-only, individually editable and unknown parameters. Documented ranges are not write authorization or installation-specific safe limits. Re-read current block, validate transition/dependencies, preview and confirm, write via core, verify full readback and journal outcome. Persistence is separate from immediate readback. Unknown outcomes require reconciliation before further changes. Physical write acceptance on isolated bench only until separately validated for production.

## Context-sensitive help

Use bilingual metadata for original concise descriptions, LCD labels, menu paths, documented and observed defaults (separate), ranges, dependencies, evidence and manual references. Audit both manuals; retain unknowns and provisional status. Tooltips, detail panel and page-specific PDF navigation. Provide manual adjustment guidance where supported, followed by re-read; do not advise another change while a prior write outcome is uncertain.

Settings expose editable FI/EN manual URLs:
- https://ouman.fi/documentbank/EH-203__manual__fi.pdf
- https://ouman.fi/documentbank/EH-203__manual__en.pdf

User-initiated download or local PDF import only. No bundled manufacturer PDFs or automatic network calls. Use QStandardPaths for local storage, QSettings for preferences, validate PDF and record SHA-256/page count; warn on unknown editions and avoid claiming page mapping verified. Use atomic replacement, preserve valid local copy on failure, bounded download and HTTPS validation. QtPdf/QPdfView preferred, test availability in AppImage; external reader fallback. No telemetry. Manufacturer rights remain with their holders.

## Implementation sequence

1. Foundation: feature/gui-v1 from reviewed main; navigation, localization, preferences, simulator, serial worker and offscreen Qt smoke tests.
2. Help system: manual manager, metadata audit and page navigation.
3. Monitoring: prioritized polling, snapshots, status and stale-data handling.
4. Visualization: PyQtGraph candidate; heating curves, trends and weekly schedules with event order and weekday masks. Persistent SQLite history optional later.
5. Backup and comparison: full capture, independent pass, identity/integrity checks, private paths, no overwrite, raw and decoded differences.
6. Guided restore: existing validated executor, dry-run, dependencies/exclusions, explicit isolated bench confirmation, manual reset/power cycle, journal and persistence checks.
7. Parameter editor: enable only individually validated transitions; manual fallback for unsupported parameters.
8. Acceptance: preserve core tests, CI on supported Python versions, simulator and offscreen tests, Fedora KDE and isolated hardware acceptance, AppImage smoke test. No release/tag without agreement.

## Known limitations

See [core engine](CORE_ENGINE.md), [safety](SAFETY.md), [parameter map](PARAMETER_MAP.md), [backup](BACKUP.md) and [research status](RESEARCH_STATUS.md). Full bilingual audit, alarm encoding, relay hysteresis, GSM storage and other unresolved fields remain open. No unrestricted editor or production restore is authorized by this roadmap. Review core progress/cancellation and atomic export before GUI integration.

## Working method

Focused commits and pull requests; user pulls and tests on Fedora KDE and hardware as needed. Do not publish private device captures. Report actual tests, not assumed results.
