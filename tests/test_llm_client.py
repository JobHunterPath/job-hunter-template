from collections import deque
from unittest.mock import MagicMock

from core.llm_client import LLMClient


def _client_with_limit(requests_per_minute):
    client = LLMClient.__new__(LLMClient)
    client._provider = "test"
    client._raw = None
    client._requests_per_minute = requests_per_minute
    client._rate_lock = __import__("threading").Lock()
    client._call_timestamps = deque()
    return client


def test_throttle_noops_when_disabled(monkeypatch):
    client = _client_with_limit(0)
    sleep = MagicMock()
    monkeypatch.setattr("core.llm_client.time.sleep", sleep)

    client._throttle()

    sleep.assert_not_called()


def test_throttle_waits_when_window_is_full(monkeypatch):
    client = _client_with_limit(2)
    client._call_timestamps.extend([100.0, 101.0])
    sleep = MagicMock()
    times = iter([120.0, 160.1])
    monkeypatch.setattr("core.llm_client.time.monotonic", lambda: next(times))
    monkeypatch.setattr("core.llm_client.time.sleep", sleep)

    client._throttle()

    sleep.assert_called_once_with(40.0)
    assert list(client._call_timestamps) == [101.0, 160.1]
