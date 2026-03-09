"""CLI entrypoint for linkedin-cli."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from . import __version__
from .auth import collect_auth_diagnostics
from .client import LinkedInClient, LinkedInClientError
from .config import AppConfig, load_config
from .formatter import (
    build_search_table,
    build_status_panel,
    print_post_detail,
    print_post_table,
    print_profile,
)
from .serialization import posts_to_json, profile_to_dict, search_results_to_json, to_json

console = Console(stderr=True)
REACTION_CHOICES = ["like", "celebrate", "support", "love", "insightful", "curious"]


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s", stream=sys.stderr)


def _load_runtime_config(config_path: Optional[str]) -> AppConfig:
    path = Path(config_path) if config_path else None
    return load_config(path)


def _client_from_ctx(ctx: click.Context) -> LinkedInClient:
    return LinkedInClient(ctx.obj["config"])


def _write_output(output_file: Optional[str], payload: str) -> None:
    if output_file:
        Path(output_file).write_text(payload + "\n", encoding="utf-8")


def _handle_error(exc: Exception) -> None:
    console.print(build_status_panel("linkedin-cli", False, str(exc)))
    raise SystemExit(1) from exc


@click.group()
@click.option("--config", "config_path", type=click.Path(dir_okay=False, path_type=str), default=None, help="Path to a config YAML file.")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx: click.Context, config_path: Optional[str], verbose: bool) -> None:
    """linkedin - LinkedIn CLI."""
    _setup_logging(verbose)
    ctx.ensure_object(dict)
    ctx.obj["config"] = _load_runtime_config(config_path)


@cli.command("auth-status")
@click.pass_context
def auth_status(ctx: click.Context) -> None:
    """Verify the current LinkedIn session."""
    try:
        payload = collect_auth_diagnostics(ctx.obj["config"])
    except Exception as exc:
        _handle_error(exc)
    success = bool(payload.get("ok"))
    detail_lines = []
    identity = payload.get("public_id") or payload.get("full_name")
    summary_parts = [f"source={payload.get('source', 'unknown')}"]
    if payload.get("browser"):
        summary_parts.append(f"browser={payload['browser']}")
    if identity:
        summary_parts.append(f"identity={identity}")
    summary_parts.append(f"cookies={payload.get('cookie_count', 0)}")
    detail_lines.append(" | ".join(summary_parts))

    validation = payload.get("validation") or {}
    if validation.get("ok"):
        detail_lines.append("basic-probe=ok")
    else:
        probe_line = f"basic-probe={validation.get('kind') or 'error'}"
        if validation.get("status_code") is not None:
            probe_line += f":{validation['status_code']}"
        if validation.get("location"):
            probe_line += f" -> {validation['location']}"
        elif validation.get("error"):
            probe_line += f" ({validation['error']})"
        detail_lines.append(probe_line)

    for name, result in (payload.get("probes") or {}).items():
        if result.get("ok"):
            probe_line = f"{name}=ok"
            if result.get("status_code") is not None:
                probe_line += f":{result['status_code']}"
            detail_lines.append(probe_line)
            continue

        probe_line = f"{name}={result.get('reason') or result.get('kind') or 'error'}"
        if result.get("status_code") is not None:
            probe_line += f":{result['status_code']}"
        if result.get("location"):
            probe_line += f" -> {result['location']}"
        elif result.get("error"):
            probe_line += f" ({result['error']})"
        detail_lines.append(probe_line)

    if payload.get("hint"):
        detail_lines.append(f"hint={payload['hint']}")

    title = "Authentication OK" if success else "Authentication degraded"
    console.print(build_status_panel(title, success, "\n".join(detail_lines)))
    if not success:
        raise SystemExit(1)


@cli.command()
@click.option("--max", "max_count", type=int, default=None, help="Maximum number of feed items to fetch.")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON to stdout.")
@click.option("--output", "-o", "output_file", type=str, default=None, help="Write JSON output to a file.")
@click.pass_context
def feed(ctx: click.Context, max_count: Optional[int], as_json: bool, output_file: Optional[str]) -> None:
    """Fetch the authenticated home feed."""
    try:
        posts = _client_from_ctx(ctx).feed(limit=max_count)
    except Exception as exc:
        _handle_error(exc)
    payload = posts_to_json(posts)
    _write_output(output_file, payload)
    if as_json:
        click.echo(payload)
        return
    print_post_table(posts, console=console, title="LinkedIn feed")


@cli.command()
@click.argument("query")
@click.option("--max", "max_count", type=int, default=None, help="Maximum number of search results to fetch.")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON to stdout.")
@click.option("--output", "-o", "output_file", type=str, default=None, help="Write JSON output to a file.")
@click.pass_context
def search(ctx: click.Context, query: str, max_count: Optional[int], as_json: bool, output_file: Optional[str]) -> None:
    """Search LinkedIn entities and posts."""
    try:
        results = _client_from_ctx(ctx).search(query, limit=max_count)
    except Exception as exc:
        _handle_error(exc)
    payload = search_results_to_json(results)
    _write_output(output_file, payload)
    if as_json:
        click.echo(payload)
        return
    console.print(build_search_table(results, title=f"Search: {query}"))


@cli.command()
@click.argument("identifier")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON to stdout.")
@click.pass_context
def profile(ctx: click.Context, identifier: str, as_json: bool) -> None:
    """Fetch a LinkedIn profile by public id or URL."""
    try:
        result = _client_from_ctx(ctx).get_profile(identifier)
    except Exception as exc:
        _handle_error(exc)
    if as_json:
        click.echo(to_json(profile_to_dict(result)))
        return
    print_profile(result, console=console)


@cli.command("profile-posts")
@click.argument("identifier")
@click.option("--max", "max_count", type=int, default=None, help="Maximum number of posts to fetch.")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON to stdout.")
@click.option("--output", "-o", "output_file", type=str, default=None, help="Write JSON output to a file.")
@click.pass_context
def profile_posts(ctx: click.Context, identifier: str, max_count: Optional[int], as_json: bool, output_file: Optional[str]) -> None:
    """Fetch posts for a LinkedIn profile."""
    try:
        posts = _client_from_ctx(ctx).get_profile_posts(identifier, limit=max_count)
    except Exception as exc:
        _handle_error(exc)
    payload = posts_to_json(posts)
    _write_output(output_file, payload)
    if as_json:
        click.echo(payload)
        return
    print_post_table(posts, console=console, title=f"Posts by {identifier}")


@cli.command()
@click.argument("identifier")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON to stdout.")
@click.pass_context
def activity(ctx: click.Context, identifier: str, as_json: bool) -> None:
    """Fetch a LinkedIn activity detail."""
    try:
        post = _client_from_ctx(ctx).get_activity(identifier)
    except Exception as exc:
        _handle_error(exc)
    payload = to_json(post)
    if as_json:
        click.echo(payload)
        return
    print_post_detail(post, console=console)


@cli.command()
@click.argument("text")
@click.option("--visibility", type=click.Choice(["connections", "public"]), default="connections", show_default=True)
@click.pass_context
def post(ctx: click.Context, text: str, visibility: str) -> None:
    """Publish a new LinkedIn post through the browser fallback."""
    try:
        detail = _client_from_ctx(ctx).post(text, visibility=visibility)
    except Exception as exc:
        _handle_error(exc)
    console.print(build_status_panel("Post created", True, detail))


@cli.command()
@click.argument("identifier")
@click.option("--type", "reaction_type", type=click.Choice(REACTION_CHOICES), default="like", show_default=True)
@click.pass_context
def react(ctx: click.Context, identifier: str, reaction_type: str) -> None:
    """React to a LinkedIn activity."""
    try:
        detail = _client_from_ctx(ctx).react(identifier, reaction_type)
    except Exception as exc:
        _handle_error(exc)
    console.print(build_status_panel("Reaction applied", True, detail))


@cli.command()
@click.argument("identifier")
@click.pass_context
def unreact(ctx: click.Context, identifier: str) -> None:
    """Remove the current reaction from a LinkedIn activity."""
    try:
        detail = _client_from_ctx(ctx).unreact(identifier)
    except Exception as exc:
        _handle_error(exc)
    console.print(build_status_panel("Reaction removed", True, detail))


@cli.command()
@click.argument("identifier")
@click.pass_context
def save(ctx: click.Context, identifier: str) -> None:
    """Save a LinkedIn activity."""
    try:
        detail = _client_from_ctx(ctx).save(identifier)
    except Exception as exc:
        _handle_error(exc)
    console.print(build_status_panel("Post saved", True, detail))


@cli.command()
@click.argument("identifier")
@click.pass_context
def unsave(ctx: click.Context, identifier: str) -> None:
    """Remove a saved LinkedIn activity."""
    try:
        detail = _client_from_ctx(ctx).unsave(identifier)
    except Exception as exc:
        _handle_error(exc)
    console.print(build_status_panel("Post unsaved", True, detail))


@cli.command()
@click.argument("identifier")
@click.argument("text")
@click.pass_context
def comment(ctx: click.Context, identifier: str, text: str) -> None:
    """Comment on a LinkedIn activity."""
    try:
        detail = _client_from_ctx(ctx).comment(identifier, text)
    except Exception as exc:
        _handle_error(exc)
    console.print(build_status_panel("Comment posted", True, detail))


def main() -> None:
    """Entry point for `python -m linkedin_cli.cli`."""
    try:
        cli(standalone_mode=False)
    except LinkedInClientError as exc:
        _handle_error(exc)
    except click.ClickException as exc:
        exc.show()
        raise SystemExit(exc.exit_code) from exc


if __name__ == "__main__":  # pragma: no cover
    main()
