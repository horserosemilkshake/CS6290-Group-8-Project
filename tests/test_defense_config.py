"""Tests for thread-safe defense config management."""
import threading

from agent_client.src.agents.l1_agent import (
    get_defense_config,
    set_defense_config,
)


def test_get_set_roundtrip():
    """set then get returns the same value."""
    original = get_defense_config()
    try:
        set_defense_config("bare")
        assert get_defense_config() == "bare"
        set_defense_config("l1l2l3")
        assert get_defense_config() == "l1l2l3"
    finally:
        set_defense_config(original)


def test_invalid_config_raises():
    import pytest
    with pytest.raises(ValueError, match="Invalid defense config"):
        set_defense_config("nonexistent")


def test_concurrent_set_get_never_reads_partial_state():
    """Under concurrent writes, get_defense_config must always return a
    valid config string — never a torn or partial value."""
    original = get_defense_config()
    valid_configs = {"bare", "l1", "l1l2", "l1l2l3"}
    errors = []

    def writer(config: str, iterations: int):
        for _ in range(iterations):
            set_defense_config(config)

    def reader(iterations: int):
        for _ in range(iterations):
            val = get_defense_config()
            if val not in valid_configs:
                errors.append(val)

    try:
        threads = [
            threading.Thread(target=writer, args=("bare", 200)),
            threading.Thread(target=writer, args=("l1l2l3", 200)),
            threading.Thread(target=reader, args=(400,)),
            threading.Thread(target=reader, args=(400,)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Got invalid config values: {errors}"
    finally:
        set_defense_config(original)


def test_process_request_uses_get_defense_config():
    """L1Agent.process_request must call get_defense_config() (lock-protected)
    instead of reading the raw _defense_config global directly."""
    import inspect
    from agent_client.src.agents.l1_agent import L1Agent

    source = inspect.getsource(L1Agent.process_request)
    # Must use the lock-protected getter, not the bare global
    assert "get_defense_config()" in source, (
        "process_request should call get_defense_config() to snapshot the "
        "config under the lock, not read _defense_config directly"
    )
    # Should NOT contain a bare read of the global (except possibly in comments)
    # Strip comments before checking
    code_lines = [
        line for line in source.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    code_without_comments = "\n".join(code_lines)
    assert "= _defense_config" not in code_without_comments, (
        "process_request should not read _defense_config directly; "
        "use get_defense_config() instead"
    )
