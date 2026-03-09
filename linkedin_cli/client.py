"""High-level LinkedIn client for the CLI."""

from __future__ import annotations

import logging
import time
from typing import Any, Iterable, Optional
from urllib.parse import urlparse

from requests import exceptions as requests_exceptions

from .auth import AuthenticationError
from .auth import build_api_client
from .auth import probe_read_access
from .auth import resolve_auth_session
from .auth import validate_auth_session
from .browser import BrowserActionError, LinkedInBrowserFallback
from .config import AppConfig
from .models import Actor, Comment, EngagementMetrics, Post, Profile, ReactionSummary, SearchResult
from .transport import LinkedInTransportError
from .transport import LinkedInVoyagerTransport

logger = logging.getLogger(__name__)

REACTION_TYPE_MAP = {
    "like": "LIKE",
    "celebrate": "PRAISE",
    "support": "APPRECIATION",
    "love": "EMPATHY",
    "insightful": "INTEREST",
    "curious": "ENTERTAINMENT",
}


class LinkedInClientError(RuntimeError):
    """Raised when a LinkedIn operation fails."""


class LinkedInClient:
    """Facade over linkedin-api plus browser fallback flows."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.session = resolve_auth_session(config)
        self.api = build_api_client(self.session, config)
        self.browser = LinkedInBrowserFallback(self.session, config)
        self.transport = LinkedInVoyagerTransport(self.session, config)
        self._auth_payload: dict[str, Any] | None = None

    def auth_status(self) -> dict[str, Any]:
        """Validate the session and return lightweight metadata."""
        payload = self._ensure_auth_payload()
        mini_profile = payload.get("miniProfile", {})
        return {
            "source": self.session.source,
            "browser": self.session.browser,
            "public_id": mini_profile.get("publicIdentifier", ""),
            "full_name": " ".join(
                part for part in [payload.get("firstName", ""), payload.get("lastName", "")] if part
            ),
        }

    def feed(self, limit: Optional[int] = None) -> list[Post]:
        count = self._resolve_limit(limit)
        return self._retry(
            "feed",
            lambda: self._normalize_posts(self.transport.get_feed_posts(limit=count)),
        )

    def search(self, query: str, limit: Optional[int] = None) -> list[SearchResult]:
        count = self._resolve_limit(limit)

        def run() -> list[SearchResult]:
            people = self.api.search_people(keywords=query, limit=count)
            entities = self.api.search({"keywords": query}, limit=count)
            results = [self._normalize_person_result(item) for item in people if isinstance(item, dict)]
            results.extend(
                self._normalize_search_result(item)
                for item in entities
                if isinstance(item, dict)
            )
            return [result for result in results if result.title or result.url][:count]

        return self._retry("search", run)

    def get_profile(self, identifier: str) -> Profile:
        public_id = self.normalize_profile_id(identifier)
        return self._retry(
            "profile",
            lambda: self._normalize_profile(self.transport.get_profile(public_id)),
        )

    def get_profile_posts(self, identifier: str, limit: Optional[int] = None) -> list[Post]:
        public_id = self.normalize_profile_id(identifier)
        count = self._resolve_limit(limit)
        return self._retry(
            "profile-posts",
            lambda: self._normalize_posts(self.api.get_profile_posts(public_id=public_id, post_count=count)),
        )

    def get_activity(self, identifier: str) -> Post:
        activity_urn = self.normalize_activity_urn(identifier)
        activity_id = activity_urn.split(":")[-1]

        def run() -> Post:
            comments = self.api.get_post_comments(activity_id, comment_count=20)
            reactions = self.api.get_post_reactions(activity_urn, max_results=10)
            return Post(
                urn=activity_urn,
                author=Actor(name="Unknown author"),
                text="LinkedIn activity detail. Some fields may be partial when Voyager does not expose the original share body directly.",
                url=self.activity_url(activity_urn),
                comments=[
                    self._normalize_comment(item, activity_urn)
                    for item in comments
                    if isinstance(item, dict)
                ],
                reactions=self._normalize_reaction_summary(reactions),
                metrics=EngagementMetrics(
                    reactions=len(reactions or []),
                    comments=len(comments or []),
                ),
            )

        return self._retry("activity", run)

    def post(self, text: str, visibility: str = "connections") -> str:
        return self._browser_result(self.browser.create_post(text, visibility))

    def react(self, identifier: str, reaction_type: str) -> str:
        activity_urn = self.normalize_activity_urn(identifier)
        activity_id = activity_urn.split(":")[-1]
        normalized = REACTION_TYPE_MAP.get(reaction_type.lower())
        if not normalized:
            raise LinkedInClientError(f"Unsupported reaction type: {reaction_type}")

        failed = self._retry(
            "react",
            lambda: self.api.react_to_post(activity_id, reaction_type=normalized),
        )
        if failed:
            raise LinkedInClientError("LinkedIn rejected the reaction request.")
        return f"Reaction {reaction_type.lower()} applied to {activity_urn}."

    def unreact(self, identifier: str) -> str:
        urn = self.normalize_activity_urn(identifier)
        return self._browser_result(
            self.browser.toggle_reaction(self.activity_url(urn), "like", remove=True)
        )

    def save(self, identifier: str) -> str:
        urn = self.normalize_activity_urn(identifier)
        return self._browser_result(self.browser.toggle_save(self.activity_url(urn), should_save=True))

    def unsave(self, identifier: str) -> str:
        urn = self.normalize_activity_urn(identifier)
        return self._browser_result(self.browser.toggle_save(self.activity_url(urn), should_save=False))

    def comment(self, identifier: str, text: str) -> str:
        urn = self.normalize_activity_urn(identifier)
        return self._browser_result(self.browser.comment_on_post(self.activity_url(urn), text))

    def activity_url(self, activity_urn: str) -> str:
        activity_id = activity_urn.split(":")[-1]
        return f"https://www.linkedin.com/feed/update/urn:li:activity:{activity_id}/"

    def normalize_profile_id(self, identifier: str) -> str:
        text = identifier.strip()
        if not text:
            raise LinkedInClientError("Profile identifier cannot be empty.")
        if "linkedin.com" not in text:
            return text.strip("/").split("/")[-1]
        parsed = urlparse(text)
        parts = [part for part in parsed.path.split("/") if part]
        if not parts:
            raise LinkedInClientError(f"Could not parse LinkedIn profile URL: {identifier}")
        return parts[-1]

    def normalize_activity_urn(self, identifier: str) -> str:
        text = identifier.strip()
        if not text:
            raise LinkedInClientError("Activity identifier cannot be empty.")
        if text.startswith("urn:li:activity:"):
            return text
        if text.isdigit():
            return f"urn:li:activity:{text}"
        if "linkedin.com" in text:
            for part in text.rstrip("/").split("/"):
                if part.startswith("urn:li:activity:"):
                    return part
            for part in reversed([segment for segment in text.rstrip("/").split("/") if segment]):
                if part.isdigit():
                    return f"urn:li:activity:{part}"
        raise LinkedInClientError(f"Unsupported LinkedIn activity identifier: {identifier}")

    def _retry(self, operation: str, callback):
        attempts = self.config.rate_limit.max_retries + 1
        last_error: Optional[Exception] = None
        for attempt in range(1, attempts + 1):
            try:
                self._sleep_request_delay()
                return callback()
            except (AuthenticationError, BrowserActionError):
                raise
            except requests_exceptions.TooManyRedirects as exc:
                raise LinkedInClientError(self._build_redirect_error(operation)) from exc
            except LinkedInTransportError as exc:
                last_error = exc
                logger.debug("%s attempt %s transport failure: %s", operation, attempt, exc)
                if "session-rejected" in str(exc) or "self-redirect" in str(exc):
                    break
                if attempt == attempts:
                    break
                time.sleep(self.config.rate_limit.retry_base_delay * attempt)
            except Exception as exc:
                last_error = exc
                logger.debug("%s attempt %s failed: %s", operation, attempt, exc)
                if attempt == attempts:
                    break
                time.sleep(self.config.rate_limit.retry_base_delay * attempt)
        raise LinkedInClientError(f"{operation} failed: {last_error}") from last_error

    def _browser_result(self, result) -> str:
        if not result.success:
            raise LinkedInClientError(result.detail)
        return result.detail

    def _ensure_auth_payload(self) -> dict[str, Any]:
        if self._auth_payload is None:
            self._auth_payload = validate_auth_session(self.session, self.config)
        return self._auth_payload

    def _build_redirect_error(self, operation: str) -> str:
        public_id = self.auth_status().get("public_id") or None
        probes = probe_read_access(self.session, self.config, public_id=public_id)
        failing = []
        for name, result in probes.items():
            if result.get("ok"):
                continue
            if result.get("status_code") is not None:
                failing.append(f"{name}={result.get('status_code')}")
            elif result.get("error"):
                failing.append(f"{name}=error")
        failing_text = ", ".join(failing) if failing else "unknown"
        if self.session.cookie_count <= 2:
            hint = (
                "The current session only has the minimum cookies. "
                "LinkedIn often requires a full browser cookie jar; provide LINKEDIN_COOKIE_HEADER "
                "or use browser extraction with all linkedin.com cookies."
            )
        else:
            hint = (
                "LinkedIn returned redirect loops even with the current cookie jar. "
                "This usually means authwall/checkpoint behavior or missing browser-like request context."
            )
        return f"{operation} hit a LinkedIn redirect loop ({failing_text}). {hint}"

    def _sleep_request_delay(self) -> None:
        delay = max(self.config.rate_limit.request_delay, 0.0)
        if delay:
            time.sleep(delay)

    def _resolve_limit(self, limit: Optional[int]) -> int:
        if limit is None:
            return max(self.config.fetch.count, 1)
        if limit <= 0:
            raise LinkedInClientError("--max must be greater than 0.")
        return limit

    def _normalize_posts(self, raw_posts: Iterable[dict[str, Any]]) -> list[Post]:
        return [self._normalize_post(item) for item in raw_posts if isinstance(item, dict)]

    def _normalize_post(self, raw: dict[str, Any]) -> Post:
        author_profile = self._extract_first(raw, "author_profile", "authorProfile", "actor.navigationUrl", "url")
        url = self._extract_first(raw, "url")
        urn = self._extract_first(raw, "entityUrn", "entity_urn", "urn") or self._urn_from_url(url or "")
        text = self._extract_text(raw.get("commentary")) or self._extract_first(raw, "content", "text")
        reactions_total = self._extract_count(raw, "reactionCount", "socialDetail.totalSocialActivityCounts.numLikes")
        comments_total = self._extract_count(raw, "commentCount", "socialDetail.totalSocialActivityCounts.numComments")
        reposts_total = self._extract_count(raw, "shareCount", "socialDetail.totalSocialActivityCounts.numShares")
        return Post(
            urn=urn or "",
            author=Actor(
                urn=self._extract_first(raw, "actor.entityUrn", "actor.urn") or "",
                public_id=self._public_id_from_url(author_profile or ""),
                name=self._extract_first(raw, "author_name", "actor.name.text", "actor.name") or "",
                headline=self._extract_first(raw, "actor.subDescription.text", "headline") or "",
                profile_url=author_profile or "",
            ),
            text=text or "",
            created_at=self._extract_first(raw, "old", "createdAt", "created_at") or "",
            url=url or "",
            visibility=self._extract_first(raw, "visibility", "audience") or "",
            metrics=EngagementMetrics(
                reactions=reactions_total,
                comments=comments_total,
                reposts=reposts_total,
            ),
            reactions=ReactionSummary(like=reactions_total),
            hashtags=self._extract_tokens(text or "", "#"),
            mentions=self._extract_tokens(text or "", "@"),
            liked_by_viewer=bool(self._extract_first(raw, "likedByViewer", "liked")),
            saved_by_viewer=bool(self._extract_first(raw, "savedByViewer", "saved")),
        )

    def _normalize_profile(self, raw: dict[str, Any]) -> Profile:
        full_name = self._extract_first(raw, "fullName", "full_name", "name")
        if not full_name:
            first_name = self._extract_first(raw, "firstName", "first_name") or ""
            last_name = self._extract_first(raw, "lastName", "last_name") or ""
            full_name = " ".join(part for part in [first_name, last_name] if part)
        return Profile(
            urn=self._extract_first(raw, "entityUrn", "entity_urn", "urn") or "",
            public_id=self._extract_first(raw, "publicIdentifier", "public_id") or "",
            full_name=full_name or "",
            headline=self._extract_first(raw, "headline", "occupation") or "",
            summary=self._extract_text(raw.get("summary")) or self._extract_text(raw.get("headline")),
            location=self._extract_first(raw, "locationName", "geoLocationName", "location") or "",
            followers_count=self._extract_count(raw, "followerCount", "followersCount", "followers"),
            connections_count=self._extract_count(raw, "connectionsCount", "connections"),
            profile_url=self._extract_first(raw, "publicProfileUrl", "profile_url", "url") or "",
            photo_url=self._extract_first(raw, "displayPictureUrl", "photoUrl", "photo_url") or "",
            premium=bool(self._extract_first(raw, "premium")),
            verified=bool(self._extract_first(raw, "verified")),
            creator_mode=bool(self._extract_first(raw, "creatorMode", "creator_mode")),
            skills=[
                self._extract_text(item.get("name")) or self._extract_text(item)
                for item in raw.get("skills", [])
                if isinstance(item, dict)
            ],
        )

    def _normalize_comment(self, raw: dict[str, Any], post_urn: str) -> Comment:
        actor = raw.get("commenter") or raw.get("actor") or {}
        return Comment(
            urn=self._extract_first(raw, "entityUrn", "entity_urn", "urn") or "",
            author=Actor(
                urn=self._extract_first(actor, "entityUrn", "urn") or "",
                public_id=self._extract_first(actor, "publicIdentifier", "public_id") or "",
                name=self._extract_first(actor, "name", "name.text") or "",
                headline=self._extract_first(actor, "headline", "occupation") or "",
                profile_url=self._extract_first(actor, "navigationUrl", "url") or "",
            ),
            text=self._extract_text(raw.get("commentary")) or self._extract_text(raw),
            created_at=self._extract_first(raw, "createdAt", "created_at") or "",
            post_urn=post_urn,
            reactions=ReactionSummary(like=self._extract_count(raw, "numLikes", "reactionCount")),
            replies_count=self._extract_count(raw, "numReplies", "repliesCount"),
        )

    def _normalize_reaction_summary(self, reactions: Iterable[dict[str, Any]]) -> ReactionSummary:
        buckets = {
            "like": 0,
            "celebrate": 0,
            "support": 0,
            "love": 0,
            "insightful": 0,
            "curious": 0,
        }
        for item in reactions or []:
            reaction = str(self._extract_first(item, "reactionType", "reaction_type") or "").lower()
            if reaction == "praise":
                reaction = "celebrate"
            elif reaction == "appreciation":
                reaction = "support"
            elif reaction == "empathy":
                reaction = "love"
            elif reaction == "interest":
                reaction = "insightful"
            elif reaction == "entertainment":
                reaction = "curious"
            if reaction in buckets:
                buckets[reaction] += 1
        return ReactionSummary(**buckets)

    def _normalize_person_result(self, raw: dict[str, Any]) -> SearchResult:
        profile = Profile(
            urn=self._extract_first(raw, "entityUrn", "trackingUrn") or "",
            public_id=self._extract_first(raw, "publicIdentifier", "public_id") or "",
            full_name=self._extract_first(raw, "name", "title.text") or "",
            headline=self._extract_first(raw, "headline", "primarySubtitle.text") or "",
            summary=self._extract_first(raw, "summary", "secondarySubtitle.text") or "",
            profile_url=self._extract_first(raw, "navigationUrl", "url") or "",
        )
        return SearchResult(
            kind="profile",
            title=profile.full_name or profile.public_id,
            subtitle=profile.headline,
            snippet=profile.summary,
            url=profile.profile_url,
            profile=profile,
        )

    def _normalize_search_result(self, raw: dict[str, Any]) -> SearchResult:
        title = self._extract_first(raw, "title.text", "title", "name") or ""
        subtitle = self._extract_first(raw, "primarySubtitle.text", "subtitle", "headline") or ""
        snippet = self._extract_first(raw, "secondarySubtitle.text", "summary", "description") or ""
        url = self._extract_first(raw, "navigationUrl", "url") or ""
        result_type = str(self._extract_first(raw, "entityResultType", "type", "_type") or "unknown").lower()
        if "profile" in result_type or "/in/" in url:
            profile = Profile(
                public_id=self._public_id_from_url(url),
                full_name=title,
                headline=subtitle,
                summary=snippet,
                profile_url=url,
            )
            return SearchResult(
                kind="profile",
                title=title,
                subtitle=subtitle,
                snippet=snippet,
                url=url,
                profile=profile,
            )
        if "/feed/update/" in url or "activity" in result_type:
            post = Post(
                urn=self._urn_from_url(url),
                author=Actor(name=subtitle or "Unknown"),
                text=snippet or title,
                url=url,
                hashtags=self._extract_tokens(snippet or title, "#"),
                mentions=self._extract_tokens(snippet or title, "@"),
            )
            return SearchResult(
                kind="post",
                title=title or "LinkedIn post",
                subtitle=subtitle,
                snippet=snippet,
                url=url,
                post=post,
            )
        return SearchResult(
            kind=result_type or "unknown",
            title=title,
            subtitle=subtitle,
            snippet=snippet,
            url=url,
            metadata=raw,
        )

    def _extract_count(self, raw: Any, *paths: str) -> int:
        for path in paths:
            value = self._extract_first(raw, path)
            if value in (None, ""):
                continue
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
        return 0

    def _extract_first(self, raw: Any, *paths: str):
        for path in paths:
            value = self._extract_path(raw, path)
            if value not in (None, "", [], {}):
                return value
        return None

    def _extract_path(self, raw: Any, path: str):
        current = raw
        for part in path.split("."):
            if isinstance(current, dict):
                if part in current:
                    current = current[part]
                else:
                    return None
            else:
                return None
        return current

    def _extract_text(self, raw: Any) -> str:
        if raw is None:
            return ""
        if isinstance(raw, str):
            return raw.strip()
        if isinstance(raw, dict):
            for key in ("text", "string", "title", "value"):
                value = raw.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
                if isinstance(value, dict):
                    text = self._extract_text(value)
                    if text:
                        return text
            for value in raw.values():
                text = self._extract_text(value)
                if text:
                    return text
        if isinstance(raw, list):
            return " ".join(part for part in (self._extract_text(item) for item in raw) if part).strip()
        return str(raw).strip()

    def _extract_tokens(self, text: str, prefix: str) -> list[str]:
        return [token for token in text.split() if token.startswith(prefix)]

    def _urn_from_url(self, url: str) -> str:
        if "urn:li:activity:" in url:
            for part in url.rstrip("/").split("/"):
                if part.startswith("urn:li:activity:"):
                    return part
        for part in reversed([segment for segment in url.rstrip("/").split("/") if segment]):
            if part.isdigit():
                return f"urn:li:activity:{part}"
        return ""

    def _public_id_from_url(self, url: str) -> str:
        if "/in/" not in url:
            return ""
        parsed = urlparse(url)
        parts = [part for part in parsed.path.split("/") if part]
        return parts[-1] if parts else ""
