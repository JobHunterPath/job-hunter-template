"""Tests for generic search-provider routing behavior."""

from sources import search_providers


class FailingProvider(search_providers.SearchProvider):
    name = "failing"

    def __init__(self) -> None:
        self.calls = 0

    def search(self, query: str, region_config: dict, count: int = 10):
        self.calls += 1
        raise RuntimeError("boom")


class EmptyProvider(search_providers.SearchProvider):
    name = "empty"

    def __init__(self) -> None:
        self.calls = 0

    def search(self, query: str, region_config: dict, count: int = 10):
        self.calls += 1
        return []


def test_router_skips_provider_after_configured_consecutive_failures():
    search_providers._PROVIDER_FAILURES.clear()
    failing = FailingProvider()
    fallback = EmptyProvider()
    router = search_providers.SearchRouter(providers=[failing, fallback])
    router.max_consecutive_failures = 3

    for _ in range(4):
        router.search("query", {}, count=1)

    assert failing.calls == 3
    assert fallback.calls == 4


def test_canonicalize_url_strips_tracking_for_dedupe():
    left = "https://www.example.com/jobs/123/?utm_source=x&b=2&a=1#details"
    right = "https://example.com/jobs/123?a=1&b=2"

    assert search_providers.canonicalize_url(left) == search_providers.canonicalize_url(right)
