from sources import ai_web_search


def test_build_queries_uses_title_and_region_only():
    config = {
        "sources": {
            "linkedin": {
                "enabled": True,
                "query_templates": ['site:linkedin.com/jobs/view "{title}" "{location}"'],
            },
            "disabled": {
                "enabled": False,
                "query_templates": ['"{title}" "{location}" "{company}"'],
            },
        }
    }

    queries = ai_web_search.build_queries(
        "Product Owner",
        {"location": "Berlin", "companies": [{"name": "ShouldNotAppear"}]},
        config,
    )

    assert queries == [("linkedin", 'site:linkedin.com/jobs/view "Product Owner" "Berlin"')]
    assert "ShouldNotAppear" not in queries[0][1]


def test_budget_enforces_prompt_and_result_caps():
    budget = ai_web_search.AIWebSearchBudget(
        max_prompts_per_run=2,
        max_prompts_per_region=1,
        max_results_per_prompt=5,
        max_results_per_region=3,
        max_total_results_per_run=4,
    )

    assert budget.can_prompt("berlin") is True
    budget.record_prompt("berlin")
    assert budget.can_prompt("berlin") is False
    assert budget.can_prompt("oman") is True

    assert budget.remaining_results("berlin") == 3
    budget.record_results("berlin", 3)
    assert budget.remaining_results("berlin") == 0
    assert budget.remaining_results("oman") == 1


def test_fetch_ai_web_search_jobs_respects_caps_and_normalizes(monkeypatch):
    config = {
        "enabled": True,
        "max_prompts_per_run": 1,
        "max_prompts_per_region": 1,
        "max_results_per_prompt": 2,
        "max_results_per_region": 2,
        "max_total_results_per_run": 2,
        "sources": {
            "linkedin": {
                "enabled": True,
                "query_templates": ['site:linkedin.com/jobs/view "{title}" "{location}"'],
            },
            "stepstone": {
                "enabled": True,
                "query_templates": ['site:stepstone.de/stellenangebote-- "{title}" "{location}"'],
            },
        },
    }
    raw = """
    [
      {
        "title": "Product Owner",
        "company": "TestCo",
        "location": "Berlin",
        "url": "https://www.linkedin.com/jobs/view/123",
        "source": "linkedin",
        "snippet": "Product backlog role",
        "confidence": 0.9
      },
      {
        "title": "Product Owner AI",
        "company": "OtherCo",
        "location": "Berlin",
        "url": "https://www.stepstone.de/stellenangebote--Product-Owner-AI-Berlin-OtherCo--123-inline.html",
        "source": "stepstone",
        "snippet": "AI product role",
        "confidence": 0.8
      }
    ]
    """
    calls = []

    monkeypatch.setattr(ai_web_search, "ai_web_search_config", lambda: config)
    monkeypatch.setattr(ai_web_search, "_llm_settings", lambda: ("anthropic", "cheap-model", 500))

    def fake_complete(provider, model, user, max_tokens):
        calls.append(user)
        return raw

    monkeypatch.setattr(ai_web_search, "_complete_with_web_search", fake_complete)

    jobs = ai_web_search.fetch_ai_web_search_jobs(
        ["Product Owner"],
        {"berlin": {"location": "Berlin"}},
    )

    assert len(jobs) == 2
    assert len(calls) == 1
    assert jobs[0]["source"] == "AI web search: linkedin"
    assert jobs[0]["query"] == 'site:linkedin.com/jobs/view "Product Owner" "Berlin"'
