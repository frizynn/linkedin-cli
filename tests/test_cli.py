from __future__ import annotations

from dataclasses import dataclass

from click.testing import CliRunner

from linkedin_cli.cli import cli
from linkedin_cli.models import Actor
from linkedin_cli.models import Post
from linkedin_cli.models import Profile
from linkedin_cli.models import SearchResult


@dataclass
class FakeClient:
    def auth_status(self):
        return {
            "source": "env",
            "browser": None,
            "public_id": "john-doe",
            "full_name": "John Doe",
        }

    def feed(self, limit=None):
        return [
            Post(
                urn="urn:li:activity:123456",
                author=Actor(name="Jane Doe", public_id="jane-doe"),
                text="Hello feed",
                url="https://www.linkedin.com/feed/update/urn:li:activity:123456/",
            )
        ]

    def search(self, query, limit=None):
        return [
            SearchResult(
                kind="profile",
                title="Jane Doe",
                subtitle="Builder",
                snippet=f"query={query}",
                url="https://www.linkedin.com/in/jane-doe/",
                profile=Profile(
                    public_id="jane-doe",
                    full_name="Jane Doe",
                    headline="Builder",
                    profile_url="https://www.linkedin.com/in/jane-doe/",
                ),
            )
        ]

    def get_profile(self, identifier):
        return Profile(
            public_id=identifier,
            full_name="Jane Doe",
            headline="Builder",
            profile_url=f"https://www.linkedin.com/in/{identifier}/",
        )

    def get_profile_posts(self, identifier, limit=None):
        return self.feed(limit=limit)

    def get_activity(self, identifier):
        return self.feed()[0]

    def post(self, text, visibility="connections"):
        return f"posted {visibility}: {text}"

    def react(self, identifier, reaction_type):
        return f"reacted {reaction_type} -> {identifier}"

    def unreact(self, identifier):
        return f"unreacted -> {identifier}"

    def save(self, identifier):
        return f"saved -> {identifier}"

    def unsave(self, identifier):
        return f"unsaved -> {identifier}"

    def comment(self, identifier, text):
        return f"commented -> {identifier}: {text}"


def test_cli_help_renders() -> None:
    runner = CliRunner()

    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "LinkedIn CLI" in result.output or "linkedin" in result.output


def test_feed_json_output(monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.setattr("linkedin_cli.cli._client_from_ctx", lambda ctx: FakeClient())

    result = runner.invoke(cli, ["feed", "--json"])

    assert result.exit_code == 0
    assert '"text": "Hello feed"' in result.output


def test_auth_status_includes_probe_summary(monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.setattr(
        "linkedin_cli.cli.collect_auth_diagnostics",
        lambda config: {
            "ok": False,
            "source": "env",
            "public_id": "jane-doe",
            "cookie_count": 7,
            "validation": {
                "ok": False,
                "kind": "self-redirect-loop",
                "status_code": 302,
                "location": "https://www.linkedin.com/voyager/api/me",
            },
            "probes": {
                "voyager_me": {"ok": False, "reason": "self-redirect-loop", "status_code": 302},
                "voyager_feed": {"ok": False, "reason": "redirect", "status_code": 302},
            },
            "hint": "Need a fuller cookie jar.",
        },
    )

    result = runner.invoke(cli, ["auth-status"])

    assert result.exit_code == 1
    assert "cookies=7" in result.output
    assert "basic-probe=self-redirect-loop:302" in result.output
    assert "voyager_feed=redirect:302" in result.output
    assert "Need a fuller cookie jar." in result.output


def test_auth_status_success(monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.setattr(
        "linkedin_cli.cli.collect_auth_diagnostics",
        lambda config: {
            "ok": True,
            "source": "browser",
            "browser": "chrome",
            "public_id": "jane-doe",
            "cookie_count": 9,
            "validation": {"ok": True, "kind": "profile-read"},
            "probes": {
                "voyager_me": {"ok": True, "status_code": 200},
                "voyager_feed": {"ok": True, "status_code": 200},
            },
            "hint": "",
        },
    )

    result = runner.invoke(cli, ["auth-status"])

    assert result.exit_code == 0
    assert "source=browser" in result.output
    assert "basic-probe=ok" in result.output
    assert "voyager_feed=ok:200" in result.output


def test_profile_json_output(monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.setattr("linkedin_cli.cli._client_from_ctx", lambda ctx: FakeClient())

    result = runner.invoke(cli, ["profile", "jane-doe", "--json"])

    assert result.exit_code == 0
    assert '"public_id": "jane-doe"' in result.output


def test_search_json_output(monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.setattr("linkedin_cli.cli._client_from_ctx", lambda ctx: FakeClient())

    result = runner.invoke(cli, ["search", "builder", "--json"])

    assert result.exit_code == 0
    assert '"title": "Jane Doe"' in result.output
