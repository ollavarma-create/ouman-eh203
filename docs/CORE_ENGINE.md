# Core Engine 0.1 alpha

The src-layout package supports read-only backup and explicitly authorized isolated bench restore. Research scripts remain unchanged. Install with pip install -e . and run python -m unittest discover -s tests -v.

The protocol codec is separate from serial transport. The registry contains observed fields, not blanket write authorization. Full and quick backups retain the existing JSON format and require the observed 72 accepted IDs for firmware 2.15. GSM/SMS coverage is incomplete (see BACKUP.md).

Schedule decoding preserves relative event order per circuit across blocks 4–7; this is deliberately conservative and does not establish controller precedence for simultaneous events. Validated schedule transitions are available only in the isolated bench restore.

Acceptance gate: verify two independent full backups; manually reset isolated bench controller; preview complete restore plan; execute only validated transitions with durable journal and readback; compare configuration and schedule semantics; power cycle once; verify again. Unknown bytes and runtime measurements must never be copied blindly. Hardware tests on firmware 2.15 demonstrated readback success followed by loss of an automatically interpolated L2 point on reboot. An explicit ID66 write followed by reboot produced a zero-write plan. The exact internal storage mechanism remains a hypothesis. The revised engine explicitly writes both curve blocks after mode conversion, including unchanged payloads, and waits five seconds after writes. A new uninterrupted hardware acceptance run is pending.

Journal status complete means readback only, not persistence. The persistence_verified flag remains false; an independent post-reboot full capture and zero-write plan are required. No automatic reboot or unknown writes are performed.
