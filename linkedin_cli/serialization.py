"""Serialization helpers for linkedin-cli models."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Type, TypeVar, Union

from .models import Actor, Comment, EngagementMetrics, MediaAsset, Post, Profile, ReactionSummary, SearchResult

ModelT = TypeVar("ModelT", Actor, Comment, Post, Profile, SearchResult)


def _drop_none(value: Any) -> Any:
    """Recursively remove null values from serialization payloads."""
    if isinstance(value, list):
        return [_drop_none(item) for item in value]
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if item is None:
                continue
            result[key] = _drop_none(item)
        return result
    return value


def to_dict(value: Any) -> Any:
    """Convert dataclasses and containers into JSON-safe structures."""
    if is_dataclass(value):
        return _drop_none(asdict(value))
    if isinstance(value, list):
        return [to_dict(item) for item in value]
    if isinstance(value, tuple):
        return [to_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: to_dict(item) for key, item in value.items()}
    return value


def to_json(value: Any, *, indent: int = 2) -> str:
    """Serialize an arbitrary payload to JSON."""
    return json.dumps(to_dict(value), ensure_ascii=False, indent=indent)


def write_json(path: Union[str, Path], value: Any, *, indent: int = 2) -> None:
    """Write a serialized payload to disk."""
    Path(path).write_text(to_json(value, indent=indent) + "\n", encoding="utf-8")


def profile_to_dict(profile: Profile) -> Dict[str, Any]:
    """Serialize a profile."""
    return to_dict(profile)


def post_to_dict(post: Post) -> Dict[str, Any]:
    """Serialize a post."""
    return to_dict(post)


def comment_to_dict(comment: Comment) -> Dict[str, Any]:
    """Serialize a comment."""
    return to_dict(comment)


def search_result_to_dict(result: SearchResult) -> Dict[str, Any]:
    """Serialize a search result."""
    return to_dict(result)


def actor_from_dict(data: Dict[str, Any]) -> Actor:
    """Deserialize an actor."""
    return Actor.from_dict(data)


def profile_from_dict(data: Dict[str, Any]) -> Profile:
    """Deserialize a profile."""
    return Profile.from_dict(data)


def comment_from_dict(data: Dict[str, Any]) -> Comment:
    """Deserialize a comment."""
    return Comment.from_dict(data)


def post_from_dict(data: Dict[str, Any]) -> Post:
    """Deserialize a post."""
    return Post.from_dict(data)


def search_result_from_dict(data: Dict[str, Any]) -> SearchResult:
    """Deserialize a search result."""
    return SearchResult.from_dict(data)


def posts_from_json(raw: str) -> List[Post]:
    """Parse JSON into a list of posts."""
    return _load_many(raw, Post)


def profiles_from_json(raw: str) -> List[Profile]:
    """Parse JSON into a list of profiles."""
    return _load_many(raw, Profile)


def comments_from_json(raw: str) -> List[Comment]:
    """Parse JSON into a list of comments."""
    return _load_many(raw, Comment)


def search_results_from_json(raw: str) -> List[SearchResult]:
    """Parse JSON into a list of search results."""
    return _load_many(raw, SearchResult)


def posts_to_json(posts: Iterable[Post]) -> str:
    """Serialize posts to JSON."""
    return to_json(list(posts))


def profiles_to_json(profiles: Iterable[Profile]) -> str:
    """Serialize profiles to JSON."""
    return to_json(list(profiles))


def comments_to_json(comments: Iterable[Comment]) -> str:
    """Serialize comments to JSON."""
    return to_json(list(comments))


def search_results_to_json(results: Iterable[SearchResult]) -> str:
    """Serialize search results to JSON."""
    return to_json(list(results))


def _load_many(raw: str, model_type: Type[ModelT]) -> List[ModelT]:
    """Load a list payload into model instances."""
    payload = json.loads(raw)
    if isinstance(payload, dict):
        payload = payload.get("items", payload.get("results", payload.get("data")))
    if not isinstance(payload, list):
        raise ValueError("Expected a JSON list payload")
    return [_convert_item(item, model_type) for item in payload if isinstance(item, dict)]


def _convert_item(item: Dict[str, Any], model_type: Type[ModelT]) -> ModelT:
    """Dispatch model conversion for a single dictionary."""
    if model_type is Post:
        return Post.from_dict(item)  # type: ignore[return-value]
    if model_type is Profile:
        return Profile.from_dict(item)  # type: ignore[return-value]
    if model_type is Comment:
        return Comment.from_dict(item)  # type: ignore[return-value]
    if model_type is SearchResult:
        return SearchResult.from_dict(item)  # type: ignore[return-value]
    if model_type is Actor:
        return Actor.from_dict(item)  # type: ignore[return-value]
    raise TypeError("Unsupported model type: %s" % model_type)


__all__ = [
    "Actor",
    "Comment",
    "EngagementMetrics",
    "MediaAsset",
    "Post",
    "Profile",
    "ReactionSummary",
    "SearchResult",
    "actor_from_dict",
    "comment_from_dict",
    "comment_to_dict",
    "comments_from_json",
    "comments_to_json",
    "post_from_dict",
    "post_to_dict",
    "posts_from_json",
    "posts_to_json",
    "profile_from_dict",
    "profile_to_dict",
    "profiles_from_json",
    "profiles_to_json",
    "search_result_from_dict",
    "search_result_to_dict",
    "search_results_from_json",
    "search_results_to_json",
    "to_dict",
    "to_json",
    "write_json",
]
