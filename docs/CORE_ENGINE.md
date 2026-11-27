# Core Engine 0.1 alpha

The new src-layout package is initially read-only. Research scripts remain unchanged. Install with pip install -e . and run python -m unittest discover -s tests -v.

The protocol codec is separate from serial transport. The registry contains observed fields, not blanket write authorization. Full and quick backups retain the existing JSON format and require the observed 72 accepted IDs for firmware 2.15. GSM/SMS coverage is incomplete (see BACKUP.md).

Schedule decoding preserves relative event order per circuit across blocks 4–7; this is deliberately conservative and does not establish controller precedence for simultaneous events. No automatic schedule writes are enabled in the core yet.

Acceptance gate: verify two independent full backups; manually reset isolated bench controller; preview complete restore plan; execute only validated transitions with durable journal and readback; compare configuration and schedule semantics; power cycle once; verify again. Unknown bytes and runtime measurements must never be copied blindly. Hardware acceptance remains pending.
