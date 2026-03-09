"""Terminal render helpers for linkedin-cli."""

from __future__ import annotations

from typing import Iterable, List, Optional

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .models import Comment, Post, Profile, SearchResult


def format_number(value: int) -> str:
    """Format large numbers for terminal output."""
    if value >= 1_000_000:
        return "%.1fM" % (value / 1_000_000)
    if value >= 1_000:
        return "%.1fK" % (value / 1_000)
    return str(value)


def format_reaction_summary(summary) -> str:
    """Render a compact reaction summary."""
    parts = []
    if summary.like:
        parts.append("like %s" % format_number(summary.like))
    if summary.celebrate:
        parts.append("celebrate %s" % format_number(summary.celebrate))
    if summary.support:
        parts.append("support %s" % format_number(summary.support))
    if summary.love:
        parts.append("love %s" % format_number(summary.love))
    if summary.insightful:
        parts.append("insightful %s" % format_number(summary.insightful))
    if summary.curious:
        parts.append("curious %s" % format_number(summary.curious))
    return ", ".join(parts) if parts else "none"


def _truncate(text: str, limit: int) -> str:
    """Shorten text for tables."""
    single_line = " ".join((text or "").split())
    if len(single_line) <= limit:
        return single_line
    return single_line[: limit - 3] + "..."


def _profile_header(profile: Profile) -> str:
    """Build the profile panel title."""
    parts = [profile.full_name or profile.public_id or "Unknown profile"]
    if profile.public_id:
        parts.append("(@%s)" % profile.public_id)
    badges = []
    if profile.verified:
        badges.append("verified")
    if profile.premium:
        badges.append("premium")
    if profile.creator_mode:
        badges.append("creator")
    if badges:
        parts.append("[%s]" % ", ".join(badges))
    return " ".join(parts)


def build_profile_panel(profile: Profile) -> Panel:
    """Build a rich panel for a profile."""
    lines: List[str] = []
    if profile.headline:
        lines.append(profile.headline)
    if profile.summary:
        if lines:
            lines.append("")
        lines.append(profile.summary)
    details = []
    if profile.location:
        details.append("Location: %s" % profile.location)
    if profile.followers_count:
        details.append("Followers: %s" % format_number(profile.followers_count))
    if profile.connections_count:
        details.append("Connections: %s" % format_number(profile.connections_count))
    if details:
        if lines:
            lines.append("")
        lines.extend(details)
    if profile.skills:
        lines.append("")
        lines.append("Skills: %s" % ", ".join(profile.skills))
    if profile.websites:
        lines.append("Websites: %s" % ", ".join(profile.websites))
    if profile.profile_url:
        lines.append("")
        lines.append(profile.profile_url)
    return Panel("\n".join(lines) or "No profile details available.", title=_profile_header(profile), border_style="cyan")


def build_post_table(posts: Iterable[Post], title: Optional[str] = None) -> Table:
    """Build a table for a list of posts."""
    post_list = list(posts)
    table = Table(title=title or "LinkedIn posts (%d)" % len(post_list), show_lines=True, expand=True)
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("Author", style="cyan", width=24, no_wrap=True)
    table.add_column("Post", ratio=4)
    table.add_column("Engagement", style="green", width=22)
    table.add_column("Flags", style="yellow", width=16)

    for index, post in enumerate(post_list, start=1):
        author_name = post.author.name or post.author.public_id or "Unknown"
        if post.author.public_id:
            author_name += "\n@%s" % post.author.public_id
        body = _truncate(post.text, 180)
        if post.media:
            body += "\nmedia: " + ", ".join(asset.kind or "asset" for asset in post.media[:3])
        if post.url:
            body += "\n" + post.url
        engagement = "\n".join(
            [
                "reactions: %s" % format_number(post.metrics.reactions or post.reactions.total),
                "comments: %s" % format_number(post.metrics.comments or len(post.comments)),
                "shares: %s" % format_number(post.metrics.reposts),
            ]
        )
        flags = []
        if post.visibility:
            flags.append(post.visibility)
        if post.saved_by_viewer:
            flags.append("saved")
        if post.liked_by_viewer:
            flags.append("liked")
        if not post.commentable:
            flags.append("comments-off")
        table.add_row(str(index), author_name, body or "-", engagement, "\n".join(flags) or "-")
    return table


def build_comment_table(comments: Iterable[Comment], title: Optional[str] = None) -> Table:
    """Build a table for a list of comments."""
    comment_list = list(comments)
    table = Table(title=title or "Comments (%d)" % len(comment_list), show_lines=True, expand=True)
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("Author", style="cyan", width=24, no_wrap=True)
    table.add_column("Comment", ratio=4)
    table.add_column("Reactions", style="green", width=18)
    for index, comment in enumerate(comment_list, start=1):
        author_name = comment.author.name or comment.author.public_id or "Unknown"
        if comment.author.public_id:
            author_name += "\n@%s" % comment.author.public_id
        table.add_row(
            str(index),
            author_name,
            _truncate(comment.text, 160) or "-",
            format_reaction_summary(comment.reactions),
        )
    return table


def build_post_panel(post: Post, include_comments: bool = True) -> Panel:
    """Build a detailed panel for a single post."""
    sections: List[object] = []
    title = post.author.name or post.author.public_id or "Unknown author"
    if post.author.public_id:
        title += " (@%s)" % post.author.public_id

    body = Text()
    body.append(post.text or "(empty post)")
    if post.hashtags:
        body.append("\n\nhashtags: %s" % ", ".join(post.hashtags))
    if post.mentions:
        body.append("\nmentions: %s" % ", ".join(post.mentions))
    if post.created_at:
        body.append("\n\ncreated: %s" % post.created_at)
    if post.visibility:
        body.append("\nvisibility: %s" % post.visibility)
    if post.url:
        body.append("\nurl: %s" % post.url)
    sections.append(body)

    stats = Table.grid(expand=True)
    stats.add_column(style="green")
    stats.add_column(style="green")
    stats.add_row("reactions", format_number(post.metrics.reactions or post.reactions.total))
    stats.add_row("comments", format_number(post.metrics.comments or len(post.comments)))
    stats.add_row("shares", format_number(post.metrics.reposts))
    if post.metrics.impressions:
        stats.add_row("impressions", format_number(post.metrics.impressions))
    stats.add_row("reaction mix", format_reaction_summary(post.reactions))
    sections.append(Panel(stats, title="Engagement", border_style="green"))

    if post.media:
        media_table = Table(title="Media", expand=True)
        media_table.add_column("Type", style="cyan", width=12)
        media_table.add_column("URL", ratio=3)
        media_table.add_column("Label", ratio=2)
        for asset in post.media:
            media_table.add_row(asset.kind or "-", asset.url or "-", asset.title or asset.alt_text or "-")
        sections.append(media_table)

    if include_comments and post.comments:
        sections.append(build_comment_table(post.comments[:5], title="Top comments"))

    return Panel(Group(*sections), title=title, border_style="blue", expand=True)


def build_search_table(results: Iterable[SearchResult], title: Optional[str] = None) -> Table:
    """Build a table for search results."""
    result_list = list(results)
    table = Table(title=title or "Search results (%d)" % len(result_list), show_lines=True, expand=True)
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("Type", style="yellow", width=12)
    table.add_column("Title", style="cyan", width=28)
    table.add_column("Snippet", ratio=3)
    table.add_column("URL", ratio=2)

    for index, result in enumerate(result_list, start=1):
        title_text = result.title
        if result.subtitle:
            title_text += "\n" + _truncate(result.subtitle, 40)
        snippet = result.snippet
        if not snippet and result.post:
            snippet = result.post.text
        if not snippet and result.profile:
            snippet = result.profile.summary or result.profile.headline
        url = result.url
        if not url and result.profile:
            url = result.profile.profile_url
        if not url and result.post:
            url = result.post.url
        table.add_row(
            str(index),
            result.kind or "unknown",
            title_text or "-",
            _truncate(snippet, 140) or "-",
            url or "-",
        )
    return table


def build_status_panel(action: str, success: bool, detail: str = "") -> Panel:
    """Build a simple status panel for mutating commands."""
    status = "SUCCESS" if success else "ERROR"
    border_style = "green" if success else "red"
    body = "%s\n%s" % (action, detail) if detail else action
    return Panel(body, title=status, border_style=border_style)


def print_profile(profile: Profile, console: Optional[Console] = None) -> None:
    """Print a profile."""
    (console or Console()).print(build_profile_panel(profile))


def print_post_table(posts: Iterable[Post], console: Optional[Console] = None, title: Optional[str] = None) -> None:
    """Print a list of posts."""
    (console or Console()).print(build_post_table(posts, title=title))


def print_post_detail(post: Post, console: Optional[Console] = None, include_comments: bool = True) -> None:
    """Print a single post."""
    (console or Console()).print(build_post_panel(post, include_comments=include_comments))


def print_comments(comments: Iterable[Comment], console: Optional[Console] = None, title: Optional[str] = None) -> None:
    """Print comments."""
    (console or Console()).print(build_comment_table(comments, title=title))


def print_search_results(
    results: Iterable[SearchResult], console: Optional[Console] = None, title: Optional[str] = None
) -> None:
    """Print search results."""
    (console or Console()).print(build_search_table(results, title=title))


def print_status(action: str, success: bool, detail: str = "", console: Optional[Console] = None) -> None:
    """Print a mutation result."""
    (console or Console()).print(build_status_panel(action, success, detail))


__all__ = [
    "build_comment_table",
    "build_post_panel",
    "build_post_table",
    "build_profile_panel",
    "build_search_table",
    "build_status_panel",
    "format_number",
    "format_reaction_summary",
    "print_comments",
    "print_post_detail",
    "print_post_table",
    "print_profile",
    "print_search_results",
    "print_status",
]
