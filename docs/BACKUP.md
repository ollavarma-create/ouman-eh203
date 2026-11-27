# Read-only backup prototype — EH-203 firmware 2.15

`research/scripts/backup.py` captures all 256 native parameter IDs (0–255) through **only** the canonical `0x81` read request, using 4800 baud, 8N1. It is an independent research tool, **not** a complete settings restore or a production safety backup. It never uses `0x82`, alarm probes, alternative commands, or writes of configuration blocks.

## Setup and first bench capture (Fedora KDE)

```bash
python -m pip install pyserial
python -m unittest discover -s tests -v
mkdir -p backup-captures
python research/scripts/backup.py capture --port /dev/ttyUSB0 --output backup-captures/pre_reset_pass1.json
python research/scripts/backup.py verify backup-captures/pre_reset_pass1.json
python research/scripts/backup.py export backup-captures/pre_reset_pass1.json --output backup-captures/pre_reset_known.json
```

Wait for the first capture to finish successfully; then, without touching LCD settings, repeat the whole ID sweep:

```bash
python research/scripts/backup.py capture --port /dev/ttyUSB0 --output backup-captures/pre_reset_pass2.json
python research/scripts/backup.py verify backup-captures/pre_reset_pass2.json
python research/scripts/backup.py compare backup-captures/pre_reset_pass1.json backup-captures/pre_reset_pass2.json --output backup-captures/pre_reset_comparison.json
```

**Do not reset yet.** Inspect the comparison and keep both source captures in separate offline storage. In particular, investigate any change in an unclassified data block before calling the backup reliable. Current export only covers a conservative subset of LCD-confirmed persistent fields, not every decoded setting. The comparison exit code is `2` if a known exported field differs, `1` for errors, `0` for no known-field differences. Exit code `0` is **not** approval to reset.

## Data layout and validation

- Raw JSON includes original TX/RX frames, response status, timestamps, elapsed time, extracted data, and an SHA-256 integrity digest of the complete record dictionary. Each new record is atomically saved and fsynced, including the directory, so an interrupted run leaves a partial artifact for investigation.
- `verify` checks that all 256 IDs are present, that all requests use canonical `0x81`, that every full response has the right STX, length, SUM8 and ID echo (or known rejection marker), and that ID 1 identifies an EH-203 with firmware **2.15**. A rejected ID is an expected result, not a missing record; a malformed or absent response is an incomplete backup.
- `export` produces selective named settings with raw integer, converted value, units, byte offset and evidence classification; all carry `write_authorized=false`.
- `compare` checks both snapshots independently, requires the same hardware serial, model and firmware (ID 1), compares known settings, and reports raw data differences at zero-based **data offsets** per ID. Live/transient IDs are labeled *candidates*, not assumed safe to ignore. Header changes alone do not count as configuration changes; elapsed times and acquisition timestamps never do.
- The SHA-256 digest detects modification after capture **only if the digest is independently trusted**; for immutable evidence also record the external file hash (`sha256sum`) and copy the file to offline, read-only storage. SHA-256 is not proof of completeness or recoverability.
- The output target must not exist; the tool refuses overwriting backups or comparison reports.

## Known limitations and reset gate

- Unknown configuration bytes, schedules, advanced options and device-specific values are retained in the **raw** backup but not yet represented in portable JSON. Raw snapshots cannot be replayed as restore commands. An otherwise complete raw capture may omit configuration not exposed by the native interface.
- No automatic retries or resends are performed. The tool records malformed/missing responses and fails closed. If an ID is temporarily unavailable, start another named capture.
- Identity information and potentially private GSM values are contained in raw frames. **Do not commit any capture or JSON export to this public repository.** `.gitignore` excludes `backup-captures/`.
- Captures are consistent **per ID at the time read**, not an atomic instantaneous snapshot of the device. Clock, measurements, alarms and counters can change during and between passes.
- **No factory reset until** independent captures are complete and structurally verified, important settings/operating modes/schedules are documented, unexplained raw differences are resolved or explicitly accepted, and you have a separate manual recovery plan. This tool deliberately has no `reset` or `restore` action.

For technical background see [PROTOCOL.md](PROTOCOL.md), [PARAMETER_MAP.md](PARAMETER_MAP.md), and [SAFETY.md](SAFETY.md).
