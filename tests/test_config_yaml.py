"""Smoke tests for YAML files touched by automation changes."""

from pathlib import Path

import yaml


def test_workflow_and_config_yaml_parse():
    files = [
        ".github/workflows/daily_jobs.yml",
        "config/search_config.yml",
        "config/api_config.yml",
        "config/discovery_cache.yml",
        "template/config/search_config.yml",
        "template/config/api_config.yml",
        "template/config/discovery_cache.yml",
    ]

    for file in files:
        yaml.safe_load(Path(file).read_text(encoding="utf-8"))


def test_daily_hunt_crons_match_enabled_regions_with_companies():
    config = yaml.safe_load(Path("config/search_config.yml").read_text(encoding="utf-8"))
    workflow = yaml.safe_load(Path(".github/workflows/daily_jobs.yml").read_text(encoding="utf-8"))

    regions = [
        name
        for name, region in (config.get("regions") or {}).items()
        if region.get("enabled", True) and region.get("companies")
    ]
    hunt_crons = [
        item["cron"]
        for item in workflow[True]["schedule"]
        if item["cron"] != "0 18 * * 1"
    ]

    assert len(hunt_crons) == len(regions)
