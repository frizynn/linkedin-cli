"""Authentication helpers for linkedin-cli."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any
from typing import Iterable

from linkedin_api import Linkedin
from requests.cookies import create_cookie
from requests.cookies import RequestsCookieJar

from .config import AppConfig
from .constants import COOKIE_REQUIRED_NAMES
from .constants import ENV_BROWSER
from .constants import ENV_COOKIE_HEADER
from .constants import ENV_JSESSIONID
from .constants import ENV_LI_AT
from .constants import SUPPORTED_BROWSERS

_LINKEDIN_DOMAINS = {
    "linkedin.com",
    ".linkedin.com",
    "www.linkedin.com",
    ".www.linkedin.com",
}


class AuthenticationError(RuntimeError):
    """Raised when a usable LinkedIn session cannot be resolved."""


@dataclass
class AuthSession:
    """Resolved LinkedIn auth cookies and metadata."""

    cookie_jar: RequestsCookieJar
    source: str
    browser: str | None = None
    proxy: str | None = None

    @property
    def li_at(self) -> str:
        return self.cookie_jar.get("li_at", "")

    @property
    def jsessionid(self) -> str:
        return self.cookie_jar.get("JSESSIONID", "").strip('"')

    @property
    def cookie_string(self) -> str:
        pairs = []
        for cookie in self.cookie_jar:
            pairs.append(f"{cookie.name}={cookie.value}")
        return "; ".join(pairs)

    @property
    def cookie_count(self) -> int:
        return sum(1 for _ in self.cookie_jar)

    @property
    def cookie_names(self) -> list[str]:
        return sorted({cookie.name for cookie in self.cookie_jar})

    def has_required_cookies(self) -> bool:
        return all(self.cookie_jar.get(name) for name in COOKIE_REQUIRED_NAMES)

    def as_playwright_cookies(self) -> list[dict[str, object]]:
        cookies = []
        for cookie in self.cookie_jar:
            cookies.append(
                {
                    "name": cookie.name,
                    "value": cookie.value,
                    "domain": cookie.domain or ".linkedin.com",
                    "path": cookie.path or "/",
                    "httpOnly": bool(cookie._rest.get("HttpOnly")),
                    "secure": bool(cookie.secure),
                    "sameSite": "Lax",
                }
            )
        return cookies


def resolve_auth_session(config: AppConfig) -> AuthSession:
    """Load LinkedIn cookies from env or browser storage."""
    env_header_session = _load_from_cookie_header(config)
    if env_header_session is not None:
        return env_header_session

    env_session = _load_from_env(config)
    if env_session is not None:
        return env_session

    browser_session = _load_from_browser(config)
    if browser_session is not None:
        return browser_session

    raise AuthenticationError(
        "No LinkedIn cookies found. Set LINKEDIN_COOKIE_HEADER or LINKEDIN_LI_AT/LINKEDIN_JSESSIONID, or log into linkedin.com in a supported browser."
    )


def build_api_client(session: AuthSession, config: AppConfig):
    """Create the unofficial LinkedIn Voyager client from resolved cookies."""
    proxies = {}
    if config.runtime.proxy:
        proxies = {
            "http": config.runtime.proxy,
            "https": config.runtime.proxy,
        }
    return Linkedin(
        "",
        "",
        authenticate=True,
        cookies=session.cookie_jar,
        proxies=proxies,
    )


def validate_auth_session(session: AuthSession, config: AppConfig) -> dict[str, Any]:
    """Perform a lightweight profile request using the resolved cookies."""
    from .transport import LinkedInTransport

    try:
        payload = LinkedInTransport(session, config).get_me()
    except Exception as exc:  # pragma: no cover - depends on live cookies/network
        raise AuthenticationError(f"LinkedIn auth validation failed: {exc}") from exc
    if not isinstance(payload, dict) or not payload:
        raise AuthenticationError("LinkedIn auth validation failed: empty profile payload.")
    return payload


def inspect_auth_session(session: AuthSession, config: AppConfig) -> dict[str, Any]:
    """Run the basic auth read without collapsing diagnostics into a generic error."""
    from .transport import LinkedInRedirectError
    from .transport import LinkedInTransport
    from .transport import LinkedInTransportError

    try:
        payload = LinkedInTransport(session, config).get_me()
    except LinkedInRedirectError as exc:
        return {
            "ok": False,
            "kind": exc.details.reason,
            "error": str(exc),
            "status_code": exc.details.status_code,
            "location": exc.details.location,
            "url": exc.details.url,
        }
    except LinkedInTransportError as exc:
        return {
            "ok": False,
            "kind": "transport-error",
            "error": str(exc),
        }
    except Exception as exc:  # pragma: no cover - depends on live cookies/network
        return {
            "ok": False,
            "kind": exc.__class__.__name__.replace("_", "-").lower(),
            "error": str(exc),
        }
    if not isinstance(payload, dict) or not payload:
        return {
            "ok": False,
            "kind": "invalid-payload",
            "error": "LinkedIn returned an empty profile payload.",
        }
    return {
        "ok": True,
        "kind": "profile-read",
        "payload": payload,
    }


def probe_read_access(
    session: AuthSession,
    config: AppConfig,
    *,
    public_id: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Run non-following probes against Voyager endpoints for diagnostics."""
    from .transport import LinkedInTransport

    transport = LinkedInTransport(session, config)
    checks = {
        "voyager_me": ("/me", {}),
        "voyager_feed": (
            "/feed/updatesV2",
            {
                "params": {"count": "1", "q": "chronFeed"},
                "headers": {"accept": "application/vnd.linkedin.normalized+json+2.1"},
            },
        ),
    }

    results: dict[str, dict[str, Any]] = {}
    for name, (uri, kwargs) in checks.items():
        try:
            results[name] = transport.probe(
                uri,
                params=kwargs.get("params"),
                headers=kwargs.get("headers"),
            )
            if "headers" in kwargs:
                results[name]["headers_used"] = list(kwargs["headers"].keys())
        except Exception as exc:  # pragma: no cover - live network behavior
            results[name] = {
                "ok": False,
                "kind": exc.__class__.__name__.replace("_", "-").lower(),
                "error": str(exc),
            }
    if public_id:
        try:
            results["voyager_profile"] = transport.probe_profile(public_id)
        except Exception as exc:  # pragma: no cover - live network behavior
            results["voyager_profile"] = {
                "ok": False,
                "kind": exc.__class__.__name__.replace("_", "-").lower(),
                "error": str(exc),
            }
    return results


def collect_auth_diagnostics(config: AppConfig) -> dict[str, Any]:
    """Resolve the current auth session and return diagnostic details."""
    session = resolve_auth_session(config)
    if not session.has_required_cookies():
        raise AuthenticationError("LinkedIn session is missing required cookies.")

    validation = inspect_auth_session(session, config)
    payload = validation.get("payload", {}) if validation.get("ok") else {}
    public_id, full_name = _extract_identity(payload)
    probes = probe_read_access(session, config, public_id=public_id or None)
    probes_ok = all(result.get("ok") for result in probes.values())
    return {
        "ok": bool(validation.get("ok")) and probes_ok,
        "source": session.source,
        "browser": session.browser,
        "cookie_count": session.cookie_count,
        "cookie_names": session.cookie_names,
        "public_id": public_id,
        "full_name": full_name,
        "validation": {
            "ok": bool(validation.get("ok")),
            "kind": validation.get("kind", ""),
            "error": validation.get("error", ""),
            "status_code": validation.get("status_code"),
            "location": validation.get("location"),
        },
        "probes": probes,
        "hint": _build_auth_hint(session, validation, probes),
    }


def _extract_identity(payload: dict[str, Any]) -> tuple[str, str]:
    mini_profile = payload.get("miniProfile", {}) if isinstance(payload, dict) else {}
    public_id = (
        mini_profile.get("publicIdentifier")
        or payload.get("plainId")
        or payload.get("publicIdentifier")
        or ""
    )
    full_name = " ".join(
        part for part in [payload.get("firstName", ""), payload.get("lastName", "")] if part
    ).strip()
    return public_id, full_name


def _build_auth_hint(
    session: AuthSession,
    validation: dict[str, Any],
    probes: dict[str, dict[str, Any]],
) -> str:
    redirect_reasons = {
        "redirect",
        "self-redirect-loop",
        "login",
        "checkpoint",
        "authwall",
        "challenge",
    }
    saw_redirects = validation.get("kind") in redirect_reasons or any(
        result.get("reason") in redirect_reasons for result in probes.values()
    )
    if not saw_redirects:
        if validation.get("ok") and all(result.get("ok") for result in probes.values()):
            return ""
        return "Basic auth did not complete cleanly. Review the probe details above."
    if session.cookie_count <= len(COOKIE_REQUIRED_NAMES):
        return (
            "Only the minimum cookies are loaded. LinkedIn often requires a fuller linkedin.com "
            "cookie jar. Try LINKEDIN_COOKIE_HEADER with the full Cookie header or browser extraction."
        )
    return (
        "LinkedIn is redirecting authenticated reads even with the current cookie jar. "
        "This usually means authwall/checkpoint behavior or missing browser-like request context."
    )


def _load_from_cookie_header(config: AppConfig) -> AuthSession | None:
    raw_header = os.getenv(ENV_COOKIE_HEADER, "").strip()
    if not raw_header:
        return None

    jar = RequestsCookieJar()
    for name, value in _parse_cookie_header(raw_header).items():
        jar.set(
            name,
            value,
            domain=".linkedin.com",
            path="/",
        )
    if not _has_required_cookies(jar):
        raise AuthenticationError(
            "LINKEDIN_COOKIE_HEADER was provided but does not include li_at and JSESSIONID."
        )
    return AuthSession(cookie_jar=jar, source="env-cookie-header", proxy=config.runtime.proxy)


def _load_from_env(config: AppConfig) -> AuthSession | None:
    li_at = os.getenv(ENV_LI_AT, "").strip()
    jsessionid = os.getenv(ENV_JSESSIONID, "").strip()
    if not li_at or not jsessionid:
        return None

    jar = RequestsCookieJar()
    jar.set("li_at", li_at, domain=".linkedin.com", path="/")
    jar.set("JSESSIONID", jsessionid, domain=".linkedin.com", path="/")
    return AuthSession(cookie_jar=jar, source="env", proxy=config.runtime.proxy)


def _load_from_browser(config: AppConfig) -> AuthSession | None:
    try:
        import browser_cookie3
    except ImportError as exc:  # pragma: no cover - dependency guarded by packaging
        raise AuthenticationError(
            "browser-cookie3 is required for browser cookie extraction."
        ) from exc

    browser_preference = os.getenv(ENV_BROWSER, "").strip().lower() or config.browser.preferred
    loaders = {
        "chrome": browser_cookie3.chrome,
        "chromium": browser_cookie3.chromium,
        "brave": browser_cookie3.brave,
        "edge": browser_cookie3.edge,
        "firefox": browser_cookie3.firefox,
    }

    for browser in _ordered_browser_names(browser_preference):
        loader = loaders.get(browser)
        if loader is None:
            continue
        try:
            jar = loader()
        except Exception:
            continue
        session = _session_from_cookie_jar(
            jar,
            source="browser",
            browser=browser,
            proxy=config.runtime.proxy,
        )
        if session is not None:
            return session
    return None


def _ordered_browser_names(preferred: str) -> Iterable[str]:
    if preferred and preferred in SUPPORTED_BROWSERS:
        yield preferred
    for browser in SUPPORTED_BROWSERS:
        if browser != preferred:
            yield browser


def _session_from_cookie_jar(
    jar: RequestsCookieJar,
    *,
    source: str,
    browser: str | None,
    proxy: str | None,
) -> AuthSession | None:
    linkedin_jar = RequestsCookieJar()
    for cookie in jar:
        if not _is_linkedin_domain(cookie.domain or ""):
            continue
        _copy_cookie(linkedin_jar, cookie)
    if _has_required_cookies(linkedin_jar):
        return AuthSession(
            cookie_jar=linkedin_jar,
            source=source,
            browser=browser,
            proxy=proxy,
        )
    return None


def _copy_cookie(target: RequestsCookieJar, cookie) -> None:
    target.set_cookie(
        create_cookie(
            name=cookie.name,
            value=cookie.value,
            domain=cookie.domain or ".linkedin.com",
            path=cookie.path or "/",
            secure=bool(cookie.secure),
            expires=getattr(cookie, "expires", None),
            rest=dict(getattr(cookie, "_rest", {})),
        )
    )


def _has_required_cookies(jar: RequestsCookieJar) -> bool:
    return all(jar.get(name) for name in COOKIE_REQUIRED_NAMES)


def _is_linkedin_domain(domain: str) -> bool:
    if domain in _LINKEDIN_DOMAINS:
        return True
    return domain.endswith(".linkedin.com")


def _parse_cookie_header(raw_header: str) -> dict[str, str]:
    cookies: dict[str, str] = {}
    for segment in raw_header.split(";"):
        item = segment.strip()
        if not item or "=" not in item:
            continue
        name, value = item.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name:
            continue
        cookies[name] = value
    return cookies
