"""Low-level LinkedIn Voyager transport with redirect diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

import requests
from bs4 import BeautifulSoup
from linkedin_api.utils.helpers import get_list_posts_sorted_without_promoted
from linkedin_api.utils.helpers import parse_list_raw_posts
from linkedin_api.utils.helpers import parse_list_raw_urns

from .auth import AuthSession
from .config import AppConfig
from .constants import API_BASE_URL
from .constants import DEFAULT_HEADERS
from .constants import VOYAGER_API_BASE_URL


REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}


@dataclass(frozen=True)
class RedirectDetails:
    """Normalized redirect diagnostics for a Voyager request."""

    status_code: int
    url: str
    location: str | None
    reason: str
    set_cookie: str | None = None


class LinkedInTransportError(RuntimeError):
    """Raised when the direct Voyager transport cannot complete a request."""


class LinkedInRedirectError(LinkedInTransportError):
    """Raised when LinkedIn redirects instead of returning data."""

    def __init__(self, message: str, details: RedirectDetails):
        super().__init__(message)
        self.details = details


class LinkedInTransport:
    """Browser-like transport for direct Voyager API access."""

    def __init__(self, session: AuthSession, config: AppConfig):
        self._auth_session = session
        self._config = config
        self._session = requests.Session()
        self._session.cookies.update(session.cookie_jar)
        self._session.headers.update(self._build_headers())
        if config.runtime.proxy:
            self._session.proxies.update(
                {
                    "http": config.runtime.proxy,
                    "https": config.runtime.proxy,
                }
            )

    def probe(
        self,
        resource: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Return structured diagnostics for a single request."""
        try:
            response = self._request(
                resource,
                params=params,
                headers=headers,
                allow_redirects=False,
            )
        except LinkedInRedirectError as exc:
            return {
                "ok": False,
                "status_code": exc.details.status_code,
                "url": exc.details.url,
                "location": exc.details.location,
                "reason": exc.details.reason,
                "set_cookie": exc.details.set_cookie,
            }
        except Exception as exc:  # pragma: no cover - network-dependent
            return {"ok": False, "error": str(exc)}
        if response.status_code >= 400:
            return {
                "ok": False,
                "status_code": response.status_code,
                "url": str(response.url),
                "reason": "http-error",
                "error": f"LinkedIn returned HTTP {response.status_code} for {response.url}",
            }
        return {
            "ok": True,
            "status_code": response.status_code,
            "url": str(response.url),
        }

    def probe_profile(self, public_id: str) -> dict[str, Any]:
        """Return diagnostics for the same HTML-backed profile path used by `profile`."""
        try:
            response = self._request_profile_page(public_id)
            payload = self._parse_profile_page(response.text, public_id)
        except LinkedInRedirectError as exc:
            return {
                "ok": False,
                "status_code": exc.details.status_code,
                "url": exc.details.url,
                "location": exc.details.location,
                "reason": exc.details.reason,
                "set_cookie": exc.details.set_cookie,
            }
        except Exception as exc:  # pragma: no cover - network-dependent
            return {"ok": False, "error": str(exc)}
        return {
            "ok": True,
            "status_code": response.status_code,
            "url": str(response.url),
            "public_id": payload.get("publicIdentifier") or public_id,
        }

    def fetch_me(self) -> dict[str, Any]:
        return self._get_json("/me")

    def get_me(self) -> dict[str, Any]:
        return self.fetch_me()

    def fetch_profile(self, public_id: str) -> dict[str, Any]:
        response = self._request_profile_page(public_id)
        return self._parse_profile_page(response.text, public_id)

    def get_profile(self, public_id: str) -> dict[str, Any]:
        return self.fetch_profile(public_id)

    def fetch_feed_posts(self, count: int) -> list[dict[str, Any]]:
        payload = self._get_json(
            "/feed/updatesV2",
            params={"count": str(count), "q": "chronFeed", "start": "0"},
            headers={"accept": "application/vnd.linkedin.normalized+json+2.1"},
        )
        raw_posts = payload.get("included", [])
        raw_urns = payload.get("data", {}).get("*elements", [])
        posts = parse_list_raw_posts(raw_posts, API_BASE_URL)
        urns = parse_list_raw_urns(raw_urns)
        return get_list_posts_sorted_without_promoted(urns, posts)

    def get_feed_posts(self, limit: int) -> list[dict[str, Any]]:
        return self.fetch_feed_posts(limit)

    def _get_json(
        self,
        resource: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        response = self._request(resource, params=params, headers=headers, allow_redirects=False)
        if response.status_code >= 400:
            raise LinkedInTransportError(
                f"LinkedIn returned HTTP {response.status_code} for {response.url}"
            )
        try:
            return response.json()
        except ValueError as exc:
            raise LinkedInTransportError(
                f"LinkedIn returned non-JSON content for {response.url}"
            ) from exc

    def _request_profile_page(self, public_id: str) -> requests.Response:
        profile_url = f"{API_BASE_URL}/in/{public_id.strip('/')}/"
        response = self._request(
            profile_url,
            headers={
                "accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,"
                    "image/avif,image/webp,*/*;q=0.8"
                ),
                "referer": f"{API_BASE_URL}/feed/",
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "same-origin",
                "upgrade-insecure-requests": "1",
            },
            allow_redirects=False,
        )
        if response.status_code >= 400:
            raise LinkedInTransportError(
                f"LinkedIn returned HTTP {response.status_code} for {response.url}"
            )
        return response

    def _parse_profile_page(self, html: str, public_id: str) -> dict[str, Any]:
        soup = BeautifulSoup(html, "lxml")
        code_map = {
            tag.get("id"): tag.get_text()
            for tag in soup.find_all("code")
            if tag.get("id")
        }
        payload = self._find_profile_payload(code_map, public_id)
        included = payload.get("included", [])
        if not isinstance(included, list):
            raise LinkedInTransportError("LinkedIn profile payload returned an invalid included list.")

        entities_by_urn = {
            item.get("entityUrn"): item
            for item in included
            if isinstance(item, dict) and item.get("entityUrn")
        }
        profile = next(
            (
                item
                for item in included
                if isinstance(item, dict)
                and item.get("$type") == "com.linkedin.voyager.dash.identity.profile.Profile"
            ),
            None,
        )
        if profile is None:
            raise LinkedInTransportError(
                f"LinkedIn profile page did not contain embedded profile data for {public_id}."
            )

        normalized = dict(profile)
        normalized["publicProfileUrl"] = f"{API_BASE_URL}/in/{public_id.strip('/')}/"

        geo_name = self._resolve_geo_name(profile.get("geoLocation"), entities_by_urn)
        if geo_name:
            normalized["geoLocationName"] = geo_name

        photo_url = self._extract_best_image_url(profile.get("profilePicture"))
        if photo_url:
            normalized["displayPictureUrl"] = photo_url

        return normalized

    def _find_profile_payload(self, code_map: dict[str, str], public_id: str) -> dict[str, Any]:
        vanity_markers = {
            f"vanityName:{public_id}",
            f"vanityName%3A{public_id}",
        }
        for code_text in code_map.values():
            if "voyagerIdentityDashProfiles" not in code_text:
                continue
            if not any(marker in code_text for marker in vanity_markers):
                continue
            try:
                metadata = json.loads(code_text)
            except json.JSONDecodeError:
                continue
            body_id = metadata.get("body")
            body_text = code_map.get(body_id or "")
            if not body_text:
                continue
            try:
                return json.loads(body_text)
            except json.JSONDecodeError as exc:
                raise LinkedInTransportError(
                    f"LinkedIn embedded an unreadable profile payload for {public_id}."
                ) from exc
        raise LinkedInTransportError(
            f"LinkedIn profile page did not expose an embedded profile payload for {public_id}."
        )

    def _resolve_geo_name(
        self,
        geo_location: Any,
        entities_by_urn: dict[str, dict[str, Any]],
    ) -> str:
        if isinstance(geo_location, dict):
            geo_urn = geo_location.get("*geo")
            if geo_urn and geo_urn in entities_by_urn:
                geo = entities_by_urn[geo_urn]
                return (
                    geo.get("defaultLocalizedNameWithoutCountryName")
                    or geo.get("defaultLocalizedName")
                    or ""
                )
        if isinstance(geo_location, str) and geo_location in entities_by_urn:
            geo = entities_by_urn[geo_location]
            return (
                geo.get("defaultLocalizedNameWithoutCountryName")
                or geo.get("defaultLocalizedName")
                or ""
            )
        return ""

    def _extract_best_image_url(self, payload: Any) -> str:
        if not isinstance(payload, dict):
            return ""

        candidates = []

        def walk(node: Any) -> None:
            if isinstance(node, dict):
                root_url = node.get("rootUrl")
                artifacts = node.get("artifacts")
                if isinstance(root_url, str) and isinstance(artifacts, list):
                    for artifact in artifacts:
                        if not isinstance(artifact, dict):
                            continue
                        segment = artifact.get("fileIdentifyingUrlPathSegment")
                        if not isinstance(segment, str) or not segment:
                            continue
                        width = int(artifact.get("width") or 0)
                        candidates.append((width, f"{root_url}{segment}"))
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(payload)
        if not candidates:
            return ""
        return max(candidates, key=lambda item: item[0])[1]

    def _request(
        self,
        resource: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        allow_redirects: bool = False,
    ) -> requests.Response:
        url = resource if resource.startswith("http") else f"{VOYAGER_API_BASE_URL}{resource}"
        response = self._session.get(
            url,
            params=params,
            headers=headers,
            allow_redirects=allow_redirects,
            timeout=self._config.rate_limit.timeout,
        )
        if response.status_code in REDIRECT_STATUS_CODES:
            details = RedirectDetails(
                status_code=response.status_code,
                url=str(response.url),
                location=response.headers.get("location"),
                reason=_classify_redirect(response),
                set_cookie=response.headers.get("set-cookie"),
            )
            classification = "session-rejected" if details.reason in {
                "self-redirect-loop",
                "login",
                "checkpoint",
                "authwall",
                "challenge",
            } else details.reason
            raise LinkedInRedirectError(
                f"LinkedIn redirected {classification} for {url}",
                details,
            )
        return response

    def _build_headers(self) -> dict[str, str]:
        headers = dict(DEFAULT_HEADERS)
        headers.update(
            {
                "accept-language": "en-US,en;q=0.9",
                "cache-control": "no-cache",
                "pragma": "no-cache",
                "referer": f"{API_BASE_URL}/feed/",
                "sec-ch-ua": '"Google Chrome";v="145", "Chromium";v="145", "Not.A/Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "x-li-lang": "en_US",
                "x-restli-protocol-version": "2.0.0",
                "csrf-token": self._auth_session.jsessionid,
            }
        )
        return headers


def _classify_redirect(response: requests.Response) -> str:
    location = response.headers.get("location") or ""
    if not location:
        return "empty-redirect"
    if location == str(response.url):
        return "self-redirect-loop"
    lowered = location.lower()
    if "checkpoint" in lowered:
        return "checkpoint"
    if "login" in lowered:
        return "login"
    if "authwall" in lowered:
        return "authwall"
    if "challenge" in lowered:
        return "challenge"
    return "redirect"


LinkedInVoyagerTransport = LinkedInTransport
