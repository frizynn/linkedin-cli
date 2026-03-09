from __future__ import annotations

from linkedin_cli.models import Actor
from linkedin_cli.models import Post
from linkedin_cli.models import Profile
from linkedin_cli.serialization import posts_from_json
from linkedin_cli.serialization import posts_to_json
from linkedin_cli.serialization import profile_to_dict


def test_profile_to_dict_roundtrip_fields() -> None:
    profile = Profile(
        urn="urn:li:fs_profile:123",
        public_id="john-doe",
        full_name="John Doe",
        headline="Builder",
        summary="Makes things happen.",
        profile_url="https://www.linkedin.com/in/john-doe/",
    )

    payload = profile_to_dict(profile)

    assert payload["public_id"] == "john-doe"
    assert payload["full_name"] == "John Doe"
    assert payload["profile_url"].endswith("/john-doe/")


def test_posts_json_roundtrip() -> None:
    posts = [
        Post(
            urn="urn:li:activity:123456",
            author=Actor(name="Jane Doe", public_id="jane-doe"),
            text="Hello LinkedIn",
            url="https://www.linkedin.com/feed/update/urn:li:activity:123456/",
        )
    ]

    raw = posts_to_json(posts)
    loaded = posts_from_json(raw)

    assert len(loaded) == 1
    assert loaded[0].author.name == "Jane Doe"
    assert loaded[0].text == "Hello LinkedIn"
