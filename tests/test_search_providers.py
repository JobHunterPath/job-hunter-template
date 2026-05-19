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


class StaticProvider(search_providers.SearchProvider):
    name = "static"

    def search(self, query: str, region_config: dict, count: int = 10):
        return [
            search_providers.SearchResult(
                url="https://jobs.smartrecruiters.com/TestCo/123456-product-manager",
                title="Product Manager",
                description="Dublin product role",
                source="SearXNG",
            ),
            search_providers.SearchResult(
                url="https://jobs.smartrecruiters.com/TestCo",
                title="Product Manager jobs",
                description="Listing page",
                source="SearXNG",
            ),
        ]


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


def test_discover_ats_jobs_by_search_extracts_expanded_ats_shapes(monkeypatch):
    class FakeRouter:
        def __init__(self, provider_order):
            self.provider_order = provider_order

        def search(self, query: str, region_config: dict, count: int = 10):
            assert self.provider_order == ["searxng", "brave"]
            return StaticProvider().search(query, region_config, count=count)

    monkeypatch.setattr(search_providers, "ProviderSearchRouter", FakeRouter)
    monkeypatch.setattr(
        search_providers,
        "_search_cfg",
        lambda: {
            "ats_discovery": {
                "enabled": True,
                "sources": ["smartrecruiters"],
                "results_per_query": 10,
            }
        },
    )

    jobs = search_providers.discover_ats_jobs_by_search(
        ["Product Manager"],
        {"dublin": {"location": "Dublin"}},
        provider_order=["searxng", "brave"],
    )

    assert len(jobs) == 1
    assert jobs[0]["url"] == "https://jobs.smartrecruiters.com/TestCo/123456-product-manager"
    assert jobs[0]["company"] == "Testco"
    assert jobs[0]["source"] == "SearXNG ATS discovery: smartrecruiters"
