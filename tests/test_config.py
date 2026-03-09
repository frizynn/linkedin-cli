from __future__ import annotations

from pathlib import Path

from requests.cookies import RequestsCookieJar

from linkedin_cli.auth import AuthSession
from linkedin_cli.auth import _session_from_cookie_jar
from linkedin_cli.auth import collect_auth_diagnostics
from linkedin_cli.auth import probe_read_access
from linkedin_cli.auth import resolve_auth_session
from linkedin_cli.config import load_config
from linkedin_cli.config import resolve_config_path


def test_load_config_from_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "fetch:",
                "  count: 33",
                "browser:",
                "  preferred: firefox",
                "  fallback_enabled: false",
                "rateLimit:",
                "  requestDelay: 2.5",
                "  maxRetries: 7",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.fetch.count == 33
    assert config.browser.preferred == "firefox"
    assert config.browser.fallback_enabled is False
    assert config.rate_limit.request_delay == 2.5
    assert config.rate_limit.max_retries == 7
    assert config.path == config_path


def test_resolve_config_path_prefers_existing_file(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("fetch:\n  count: 10\n", encoding="utf-8")

    assert resolve_config_path(tmp_path) == config_path


def test_resolve_auth_session_from_cookie_header(monkeypatch) -> None:
    config = load_config()
    monkeypatch.setenv(
        "LINKEDIN_COOKIE_HEADER",
        'li_at=abc123; JSESSIONID="ajax:123"; lang=v=2&lang=en-us',
    )

    session = resolve_auth_session(config)

    assert session.source == "env-cookie-header"
    assert session.cookie_count == 3
    assert session.cookie_string.count("li_at=") == 1
    assert session.cookie_string.count("JSESSIONID=") == 1


def test_resolve_auth_session_from_minimal_env(monkeypatch) -> None:
    config = load_config()
    monkeypatch.delenv("LINKEDIN_COOKIE_HEADER", raising=False)
    monkeypatch.setenv("LINKEDIN_LI_AT", "abc123")
    monkeypatch.setenv("LINKEDIN_JSESSIONID", '"ajax:123"')

    session = resolve_auth_session(config)

    assert session.source == "env"
    assert session.cookie_count == 2
    assert session.li_at == "abc123"
    assert session.jsessionid == "ajax:123"


def test_session_from_cookie_jar_keeps_full_linkedin_cookie_set() -> None:
    source_jar = RequestsCookieJar()
    source_jar.set("li_at", "abc123", domain=".linkedin.com", path="/")
    source_jar.set("JSESSIONID", '"ajax:123"', domain=".linkedin.com", path="/")
    source_jar.set("li_theme", "light", domain=".www.linkedin.com", path="/")
    source_jar.set("sessionid", "ignore-me", domain=".example.com", path="/")

    session = _session_from_cookie_jar(
        source_jar,
        source="browser",
        browser="chrome",
        proxy=None,
    )

    assert session is not None
    assert session.cookie_count == 3
    assert session.cookie_jar.get("li_theme") == "light"
    assert session.cookie_jar.get("sessionid") is None


def test_collect_auth_diagnostics_returns_hint_when_validation_redirects(monkeypatch) -> None:
    config = load_config()
    jar = RequestsCookieJar()
    jar.set("li_at", "abc123", domain=".linkedin.com", path="/")
    jar.set("JSESSIONID", '"ajax:123"', domain=".linkedin.com", path="/")
    session = AuthSession(cookie_jar=jar, source="env")

    monkeypatch.setattr("linkedin_cli.auth.resolve_auth_session", lambda cfg: session)
    monkeypatch.setattr(
        "linkedin_cli.auth.inspect_auth_session",
        lambda current_session, cfg: {
            "ok": False,
            "kind": "self-redirect-loop",
            "error": "redirect loop",
            "status_code": 302,
            "location": "https://www.linkedin.com/voyager/api/me",
        },
    )
    monkeypatch.setattr(
        "linkedin_cli.auth.probe_read_access",
        lambda current_session, cfg, public_id=None: {
            "voyager_me": {"ok": False, "reason": "self-redirect-loop", "status_code": 302},
            "voyager_feed": {"ok": False, "reason": "redirect", "status_code": 302},
        },
    )

    diagnostics = collect_auth_diagnostics(config)

    assert diagnostics["ok"] is False
    assert diagnostics["validation"]["kind"] == "self-redirect-loop"
    assert "LINKEDIN_COOKIE_HEADER" in diagnostics["hint"]


def test_probe_read_access_uses_endpoint_headers_and_profile_probe(monkeypatch) -> None:
    config = load_config()
    jar = RequestsCookieJar()
    jar.set("li_at", "abc123", domain=".linkedin.com", path="/")
    jar.set("JSESSIONID", '"ajax:123"', domain=".linkedin.com", path="/")
    session = AuthSession(cookie_jar=jar, source="env")
    calls = []

    class FakeTransport:
        def __init__(self, current_session, current_config):
            assert current_session is session
            assert current_config is config

        def probe(self, resource, *, params=None, headers=None):
            calls.append(("probe", resource, params, headers))
            return {"ok": True, "status_code": 200}

        def probe_profile(self, public_id):
            calls.append(("profile", public_id))
            return {"ok": True, "status_code": 200}

    monkeypatch.setattr("linkedin_cli.transport.LinkedInTransport", FakeTransport)

    results = probe_read_access(session, config, public_id="jane-doe")

    assert results["voyager_feed"]["headers_used"] == ["accept"]
    assert (
        "probe",
        "/feed/updatesV2",
        {"count": "1", "q": "chronFeed"},
        {"accept": "application/vnd.linkedin.normalized+json+2.1"},
    ) in calls
    assert ("profile", "jane-doe") in calls
