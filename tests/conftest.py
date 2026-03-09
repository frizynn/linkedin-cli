from __future__ import annotations

import pytest

from linkedin_cli.models import Actor, Comment, EngagementMetrics, Post, Profile, ReactionSummary, SearchResult


@pytest.fixture
def sample_profile() -> Profile:
    return Profile(
        urn="urn:li:fs_profile:123",
        public_id="ada-lovelace",
        full_name="Ada Lovelace",
        headline="Mathematician",
        summary="Built the first algorithm for a machine.",
        location="London",
        followers_count=1200,
        connections_count=500,
        profile_url="https://www.linkedin.com/in/ada-lovelace/",
        skills=["Python", "Math"],
    )


@pytest.fixture
def sample_post(sample_profile: Profile) -> Post:
    return Post(
        urn="urn:li:activity:999",
        author=sample_profile.as_actor(),
        text="Shipping linkedin-cli today #python @team",
        created_at="1h",
        url="https://www.linkedin.com/feed/update/urn:li:activity:999/",
        metrics=EngagementMetrics(reactions=42, comments=4, reposts=2),
        reactions=ReactionSummary(like=30, celebrate=10, insightful=2),
        comments=[
            Comment(
                urn="urn:li:comment:1",
                author=Actor(name="Grace Hopper", public_id="grace-hopper"),
                text="Looks great",
            )
        ],
        hashtags=["#python"],
        mentions=["@team"],
        saved_by_viewer=True,
    )


@pytest.fixture
def sample_search_result(sample_profile: Profile, sample_post: Post) -> SearchResult:
    return SearchResult(
        kind="post",
        title="Ada shared a post",
        subtitle=sample_profile.headline,
        snippet=sample_post.text,
        url=sample_post.url,
        profile=sample_profile,
        post=sample_post,
    )
