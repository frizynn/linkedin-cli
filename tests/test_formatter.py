from __future__ import annotations

from linkedin_cli.formatter import (
    build_post_panel,
    build_post_table,
    build_profile_panel,
    build_search_table,
    build_status_panel,
)


def test_build_profile_panel(sample_profile):
    panel = build_profile_panel(sample_profile)
    assert "Ada Lovelace" in str(panel.title)
    assert "Mathematician" in panel.renderable


def test_build_post_table(sample_post):
    table = build_post_table([sample_post], title="Feed")
    assert table.title == "Feed"
    assert len(table.rows) == 1


def test_build_post_panel(sample_post):
    panel = build_post_panel(sample_post)
    assert "Ada Lovelace" in str(panel.title)


def test_build_search_table(sample_search_result):
    table = build_search_table([sample_search_result], title="Results")
    assert table.title == "Results"
    assert len(table.rows) == 1


def test_build_status_panel():
    panel = build_status_panel("Saved", True, "ok")
    assert str(panel.title) == "SUCCESS"
