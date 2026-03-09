from __future__ import annotations

from requests import exceptions as requests_exceptions

from linkedin_cli.client import LinkedInClient
from linkedin_cli.client import LinkedInClientError
from linkedin_cli.config import load_config


class _Session:
    cookie_count = 2
    source = "env"
    browser = None


def test_retry_turns_redirect_loop_into_actionable_error(monkeypatch) -> None:
    client = object.__new__(LinkedInClient)
    client.config = load_config()
    client.session = _Session()
    client._auth_payload = {
        "firstName": "Jane",
        "lastName": "Doe",
        "miniProfile": {"publicIdentifier": "jane-doe"},
    }

    monkeypatch.setattr(
        "linkedin_cli.client.probe_read_access",
        lambda session, config, public_id=None: {
            "voyager_feed": {"ok": False, "status_code": 302},
        },
    )
    monkeypatch.setattr(
        LinkedInClient,
        "_sleep_request_delay",
        lambda self: None,
    )

    try:
        client._retry("feed", lambda: (_ for _ in ()).throw(requests_exceptions.TooManyRedirects()))
    except LinkedInClientError as exc:
        message = str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected LinkedInClientError")

    assert "redirect loop" in message
    assert "LINKEDIN_COOKIE_HEADER" in message
    assert "voyager_feed=302" in message
