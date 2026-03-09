"""Domain models for linkedin-cli."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _clean_text(value: Any) -> str:
    """Return a stripped string representation for arbitrary values."""
    if value is None:
        return ""
    return str(value).strip()


def _coerce_int(value: Any, default: int = 0) -> int:
    """Best-effort integer coercion."""
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_bool(value: Any, default: bool = False) -> bool:
    """Best-effort boolean coercion."""
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return default
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off"}:
            return False
    return bool(value)


def _coerce_string_list(value: Any) -> List[str]:
    """Normalize arbitrary input to a list of non-empty strings."""
    if value is None:
        return []
    if isinstance(value, str):
        items = [part.strip() for part in value.split(",")]
        return [item for item in items if item]
    if isinstance(value, list):
        return [_clean_text(item) for item in value if _clean_text(item)]
    return [_clean_text(value)] if _clean_text(value) else []


def _first_present(mapping: Dict[str, Any], *keys: str) -> Any:
    """Return the first non-empty value found in the mapping."""
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return None


@dataclass
class Actor:
    """Minimal actor identity used across posts and comments."""

    urn: str = ""
    public_id: str = ""
    name: str = ""
    headline: str = ""
    profile_url: str = ""
    avatar_url: str = ""
    verified: bool = False
    premium: bool = False

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "Actor":
        """Build an actor from an API or JSON dictionary."""
        payload = data or {}
        return cls(
            urn=_clean_text(_first_present(payload, "urn", "entity_urn", "entityUrn")),
            public_id=_clean_text(
                _first_present(payload, "public_id", "publicId", "handle", "id")
            ),
            name=_clean_text(_first_present(payload, "name", "full_name", "fullName")),
            headline=_clean_text(_first_present(payload, "headline", "occupation", "title")),
            profile_url=_clean_text(_first_present(payload, "profile_url", "profileUrl", "url")),
            avatar_url=_clean_text(
                _first_present(payload, "avatar_url", "avatarUrl", "photo_url", "photoUrl")
            ),
            verified=_coerce_bool(_first_present(payload, "verified", "is_verified", "isVerified")),
            premium=_coerce_bool(_first_present(payload, "premium", "is_premium", "isPremium")),
        )


@dataclass
class MediaAsset:
    """Media attached to a post."""

    kind: str
    url: str
    title: str = ""
    alt_text: str = ""
    width: Optional[int] = None
    height: Optional[int] = None
    thumbnail_url: str = ""

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "MediaAsset":
        """Build a media asset from a dictionary."""
        payload = data or {}
        width = _first_present(payload, "width")
        height = _first_present(payload, "height")
        return cls(
            kind=_clean_text(_first_present(payload, "kind", "type", "media_type", "mediaType")),
            url=_clean_text(_first_present(payload, "url", "media_url", "mediaUrl")),
            title=_clean_text(_first_present(payload, "title", "name")),
            alt_text=_clean_text(_first_present(payload, "alt_text", "altText", "description")),
            width=_coerce_int(width) if width not in (None, "") else None,
            height=_coerce_int(height) if height not in (None, "") else None,
            thumbnail_url=_clean_text(
                _first_present(payload, "thumbnail_url", "thumbnailUrl", "preview_url", "previewUrl")
            ),
        )


@dataclass
class ReactionSummary:
    """Normalized LinkedIn reaction counters."""

    like: int = 0
    celebrate: int = 0
    support: int = 0
    love: int = 0
    insightful: int = 0
    curious: int = 0

    @property
    def total(self) -> int:
        """Return the total amount of reactions."""
        return self.like + self.celebrate + self.support + self.love + self.insightful + self.curious

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "ReactionSummary":
        """Build a reaction summary from a dictionary."""
        payload = data or {}
        if "total" in payload and all(
            key not in payload for key in ("like", "celebrate", "support", "love", "insightful", "curious")
        ):
            return cls(like=_coerce_int(payload.get("total")))
        return cls(
            like=_coerce_int(_first_present(payload, "like", "likes")),
            celebrate=_coerce_int(payload.get("celebrate")),
            support=_coerce_int(payload.get("support")),
            love=_coerce_int(payload.get("love")),
            insightful=_coerce_int(payload.get("insightful")),
            curious=_coerce_int(payload.get("curious")),
        )


@dataclass
class EngagementMetrics:
    """Aggregated engagement data for a post."""

    reactions: int = 0
    comments: int = 0
    reposts: int = 0
    impressions: int = 0

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "EngagementMetrics":
        """Build engagement metrics from a dictionary."""
        payload = data or {}
        return cls(
            reactions=_coerce_int(_first_present(payload, "reactions", "likes", "reaction_count")),
            comments=_coerce_int(_first_present(payload, "comments", "comment_count", "commentsCount")),
            reposts=_coerce_int(_first_present(payload, "reposts", "shares", "share_count", "sharesCount")),
            impressions=_coerce_int(
                _first_present(payload, "impressions", "views", "view_count", "viewsCount")
            ),
        )


@dataclass
class Profile:
    """LinkedIn profile model."""

    urn: str = ""
    public_id: str = ""
    full_name: str = ""
    headline: str = ""
    summary: str = ""
    location: str = ""
    followers_count: int = 0
    connections_count: int = 0
    profile_url: str = ""
    photo_url: str = ""
    open_to_work: bool = False
    premium: bool = False
    verified: bool = False
    creator_mode: bool = False
    skills: List[str] = field(default_factory=list)
    websites: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "Profile":
        """Build a profile from a dictionary."""
        payload = data or {}
        return cls(
            urn=_clean_text(_first_present(payload, "urn", "entity_urn", "entityUrn")),
            public_id=_clean_text(
                _first_present(payload, "public_id", "publicId", "handle", "vanity_name", "vanityName")
            ),
            full_name=_clean_text(
                _first_present(payload, "full_name", "fullName", "name", "display_name", "displayName")
            ),
            headline=_clean_text(_first_present(payload, "headline", "occupation", "title")),
            summary=_clean_text(_first_present(payload, "summary", "bio", "about")),
            location=_clean_text(_first_present(payload, "location")),
            followers_count=_coerce_int(
                _first_present(payload, "followers_count", "followersCount", "followers")
            ),
            connections_count=_coerce_int(
                _first_present(payload, "connections_count", "connectionsCount", "connections")
            ),
            profile_url=_clean_text(_first_present(payload, "profile_url", "profileUrl", "url")),
            photo_url=_clean_text(_first_present(payload, "photo_url", "photoUrl", "avatar_url", "avatarUrl")),
            open_to_work=_coerce_bool(_first_present(payload, "open_to_work", "openToWork")),
            premium=_coerce_bool(_first_present(payload, "premium", "is_premium", "isPremium")),
            verified=_coerce_bool(_first_present(payload, "verified", "is_verified", "isVerified")),
            creator_mode=_coerce_bool(_first_present(payload, "creator_mode", "creatorMode")),
            skills=_coerce_string_list(payload.get("skills")),
            websites=_coerce_string_list(payload.get("websites")),
        )

    def as_actor(self) -> Actor:
        """Return the profile in actor form."""
        return Actor(
            urn=self.urn,
            public_id=self.public_id,
            name=self.full_name,
            headline=self.headline,
            profile_url=self.profile_url,
            avatar_url=self.photo_url,
            verified=self.verified,
            premium=self.premium,
        )


@dataclass
class Comment:
    """LinkedIn comment model."""

    urn: str
    author: Actor
    text: str
    created_at: str = ""
    edited_at: str = ""
    post_urn: str = ""
    url: str = ""
    reactions: ReactionSummary = field(default_factory=ReactionSummary)
    replies_count: int = 0

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "Comment":
        """Build a comment from a dictionary."""
        payload = data or {}
        return cls(
            urn=_clean_text(_first_present(payload, "urn", "entity_urn", "entityUrn", "id")),
            author=Actor.from_dict(payload.get("author")),
            text=_clean_text(_first_present(payload, "text", "body", "comment")),
            created_at=_clean_text(_first_present(payload, "created_at", "createdAt")),
            edited_at=_clean_text(_first_present(payload, "edited_at", "editedAt")),
            post_urn=_clean_text(_first_present(payload, "post_urn", "postUrn", "activity_urn", "activityUrn")),
            url=_clean_text(_first_present(payload, "url")),
            reactions=ReactionSummary.from_dict(payload.get("reactions")),
            replies_count=_coerce_int(_first_present(payload, "replies_count", "repliesCount", "replies")),
        )


@dataclass
class Post:
    """LinkedIn post model."""

    urn: str
    author: Actor
    text: str
    created_at: str = ""
    edited_at: str = ""
    url: str = ""
    visibility: str = ""
    media: List[MediaAsset] = field(default_factory=list)
    metrics: EngagementMetrics = field(default_factory=EngagementMetrics)
    reactions: ReactionSummary = field(default_factory=ReactionSummary)
    comments: List[Comment] = field(default_factory=list)
    hashtags: List[str] = field(default_factory=list)
    mentions: List[str] = field(default_factory=list)
    saved_by_viewer: bool = False
    liked_by_viewer: bool = False
    commentable: bool = True

    @property
    def id(self) -> str:
        """Return a stable identifier for display purposes."""
        return self.urn

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "Post":
        """Build a post from a dictionary."""
        payload = data or {}
        comments = payload.get("comments") or []
        media = payload.get("media") or []
        return cls(
            urn=_clean_text(_first_present(payload, "urn", "entity_urn", "entityUrn", "id")),
            author=Actor.from_dict(payload.get("author")),
            text=_clean_text(_first_present(payload, "text", "body", "content")),
            created_at=_clean_text(_first_present(payload, "created_at", "createdAt")),
            edited_at=_clean_text(_first_present(payload, "edited_at", "editedAt")),
            url=_clean_text(_first_present(payload, "url")),
            visibility=_clean_text(_first_present(payload, "visibility", "audience")),
            media=[MediaAsset.from_dict(item) for item in media if isinstance(item, dict)],
            metrics=EngagementMetrics.from_dict(payload.get("metrics")),
            reactions=ReactionSummary.from_dict(payload.get("reactions")),
            comments=[Comment.from_dict(item) for item in comments if isinstance(item, dict)],
            hashtags=_coerce_string_list(payload.get("hashtags")),
            mentions=_coerce_string_list(payload.get("mentions")),
            saved_by_viewer=_coerce_bool(
                _first_present(payload, "saved_by_viewer", "savedByViewer", "saved")
            ),
            liked_by_viewer=_coerce_bool(
                _first_present(payload, "liked_by_viewer", "likedByViewer", "liked")
            ),
            commentable=_coerce_bool(_first_present(payload, "commentable"), default=True),
        )


@dataclass
class SearchResult:
    """Normalized search result for LinkedIn entities."""

    kind: str
    title: str
    subtitle: str = ""
    snippet: str = ""
    url: str = ""
    profile: Optional[Profile] = None
    post: Optional[Post] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "SearchResult":
        """Build a search result from a dictionary."""
        payload = data or {}
        profile_data = payload.get("profile")
        post_data = payload.get("post")
        return cls(
            kind=_clean_text(_first_present(payload, "kind", "type")) or "unknown",
            title=_clean_text(_first_present(payload, "title", "name")),
            subtitle=_clean_text(_first_present(payload, "subtitle", "headline")),
            snippet=_clean_text(_first_present(payload, "snippet", "summary", "description")),
            url=_clean_text(_first_present(payload, "url")),
            profile=Profile.from_dict(profile_data) if isinstance(profile_data, dict) else None,
            post=Post.from_dict(post_data) if isinstance(post_data, dict) else None,
            metadata=dict(payload.get("metadata") or {}),
        )
