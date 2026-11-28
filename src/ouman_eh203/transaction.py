"""Shared single-step wire transaction; policy and authorization stay with callers."""
def write_and_observe(entry, *, send, acknowledge, settle, read, save):
    """Persist uncertainty before sending exactly once, then ACK and observe.

    The caller must validate observed state (including dependencies) before
    marking the entry verified. No retry or rollback is implied.
    """
    save()
    rx = send(bytes.fromhex(entry['tx']))
    entry['rx'] = rx.hex()
    save()
    acknowledge(rx)
    settle()
    observed = read()
    entry['observed'] = {str(k): v.hex() for k, v in observed.items()}
    save()
    return observed
