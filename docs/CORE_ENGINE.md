# Core Engine 0.1 alpha

The src-layout package supports read-only backup and explicitly authorized isolated bench restore. Research scripts remain unchanged. Install with pip install -e . and run python -m unittest discover -s tests -v.

The protocol codec is separate from serial transport. The registry contains observed fields, not blanket write authorization. Full and quick backups retain the existing JSON format and require the observed 72 accepted IDs for firmware 2.15. GSM/SMS coverage is incomplete (see BACKUP.md).

Schedule decoding preserves relative event order per circuit across blocks 4–7; this is deliberately conservative and does not establish controller precedence for simultaneous events. Validated schedule transitions are available only in the isolated bench restore.

Acceptance gate: verify two independent full backups; manually reset isolated bench controller; preview complete restore plan; execute only validated transitions with durable journal and readback; compare configuration and schedule semantics; power cycle once; verify again. Unknown bytes and runtime measurements must never be copied blindly. Hardware tests on firmware 2.15 demonstrated readback success followed by loss of an automatically interpolated L2 point on reboot. An explicit ID66 write followed by reboot produced a zero-write plan. The exact internal storage mechanism remains a hypothesis. The revised engine explicitly writes both curve blocks after mode conversion, including unchanged payloads, and waits five seconds after writes. An uninterrupted hardware acceptance run succeeded on 2026-11-27.

Journal status complete means readback only, not persistence. The persistence_verified flag remains false; an independent post-reboot full capture and zero-write plan are required. No automatic reboot or unknown writes are performed.

Mode conversion now uses a five-second initial delay, followed by full monitored-state samples separated by two seconds, requiring ten seconds without observed changes within a 60-second sampling window. Only bounded intermediate Y changes in IDs 65/66 are allowed. Every sample is journaled; unexpected changes or timeout stop execution. Replanning must retain the exact approved ordered write payloads. The strict pre-write stale-state check remains unchanged. This is a sampled stability heuristic, not a firmware completion signal.

## Physical acceptance — 2026-11-27

The isolated EH-203 firmware 2.15 test restored the validated configuration from factory defaults in 16 verified writes. Four monitored samples remained identical over 11.59 seconds after the initial settling delay. Both curve blocks were explicitly written. A manual power cycle and full capture yielded a zero-write restore plan. The offline persistence verifier accepted the actual evidence; the operator subsequently reported 59 automated tests passing.

Evidence identifiers (SHA-256):
- Source records: `3233bfcb92ca9c07fdf92547956a5622c1033f57292e52d0b812677036dab909`
- Reboot records: `f703c975c4fe9d7b2f1f7604f1811fd4a13e1f1ae6a05a9d7c0b36eabee6c36d`
- Original journal file: `d4c9799ecb5a03551bd9aa5171b92c4fa15f1703185432f8b62fdd6a40464d05`

## Offline persistence report

```sh
ouman-eh203 verify-persistence --source original.json \
  --journal restore_journal_04.json --reboot final_reboot_04.json \
  --output persistence_04.json --confirm-power-cycle
```

The original journal is not modified. The new report links the evidence by hashes, checks full captures, target identity, recorded writes and monitored state, and requires a zero-write plan. The power cycle is operator-attested, not independently detected. Reports are not signed. Acceptance is limited to the tested restore transitions and firmware 2.15; unknown parameters, GSM settings, other firmware and production deployment are not certified. No new hardware reset is required for offline verification.


## Presentation metadata and factory reference

The registry covers 82 decoded parameters. Metadata is bilingual (Finnish and
English), but partial records are not a claim of complete manual verification.
Missing labels, paths, ranges and descriptions remain null. The provisional
`valve_center_close` field remains unresolved. Metadata never authorizes writes.

Offline commands:

```sh
ouman-eh203 metadata --lang fi --key l1_supply_min
ouman-eh203 metadata --lang en --output metadata.json
ouman-eh203 compare-defaults --source tests/fixtures/eh203_215/factory_reset_pass1.json --confirm-factory-reset --output factory_comparison.json
ouman-eh203 metadata --reference tests/fixtures/eh203_215/factory_reset_pass1.json --output metadata_215.json
```

The user-confirmed factory capture for firmware 2.15 has records SHA-256
`f76181a776e6b0b028a9267880a4ff65e0cc542de4c239a89e85eae8cdc4bebf`.
The physical comparison reported 53 matching documented defaults, zero
differences and 29 without documented defaults. This is evidence from one
controller, not a universal firmware specification. Observed defaults are
kept separate from documented defaults. The DHW high alarm was observed at
65 degrees C; the manual also lists 70 degrees C on page 28.

GUI consumers must preserve unknown values, display documentation status,
and treat menu paths and descriptions as provisional where incomplete.
Manual ranges are not restore authorization. Enum mappings may be incomplete.
Hidden three-point curve coordinates are stored values, not active control
points. The reference fixture is supplied explicitly, not bundled at runtime.
JSON exports refuse overwrite but are not atomic.

The user reported 91 passing tests after the structural metadata audit.
A complete bilingual semantic audit against both manuals remains outstanding.
No additional physical reset is required for this documentation work.
