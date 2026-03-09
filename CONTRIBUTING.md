# Contributing to linkedin-cli

Thanks for contributing.

The goal of this project is to keep the CLI practical, readable, and honest about what is stable versus what is still fragile against LinkedIn's changing web surface.

## Before You Start

- Read the [README](./README.md) for the current supported flows.
- Read the [Security Policy](./SECURITY.md) before sharing logs or repro steps.
- Do not open public issues with live session cookies, HAR files, or screenshots that expose account data.

## Development Setup

```bash
git clone https://github.com/frizynn/linkedin-cli.git
cd linkedin-cli
uv sync --extra dev
uv run playwright install chromium
```

## Running Checks

```bash
uv run ruff check .
uv run pytest -q
uv run python -m compileall linkedin_cli tests
```

If you change CLI behavior, add or update tests in `tests/` and update documentation in the same pull request.

## Working with LinkedIn Sessions

This repository intentionally relies on real LinkedIn web sessions for many flows.

Rules:
- Use your own session for local manual verification.
- Prefer `LINKEDIN_COOKIE_HEADER` when reproducing read-path issues.
- Treat `li_at`, `JSESSIONID`, and the full cookie header as credentials.
- Never hardcode cookies in source, tests, fixtures, scripts, examples, or screenshots.
- Keep live-network testing manual. Unit tests should mock transport or browser behavior.

## Contribution Guidelines

### Good contributions

- Fixes that make auth and diagnostics more reliable
- Smaller, well-tested command improvements
- Documentation fixes that better match actual behavior
- Better error messages when LinkedIn changes an endpoint or rejects a session

### Contributions that need extra care

- Broad scraping features
- Aggressive automation defaults
- Changes that silently increase request volume
- Claims in documentation that are not backed by tests or manual verification

## Pull Request Expectations

A pull request should:
- explain what changed and why
- include tests when behavior changed
- update docs when user-visible behavior changed
- avoid unrelated refactors
- keep secrets out of the diff

Use small, reviewable changes when possible.

## Reporting Bugs

Open an issue with:
- the command you ran
- the expected result
- the actual result
- sanitized output from `linkedin auth-status`
- whether you used `LINKEDIN_COOKIE_HEADER`, minimal env cookies, or browser extraction
- OS, Python version, and whether Playwright was involved

If the issue involves credentials, session leakage, or a security concern, do not file a public bug. Follow [SECURITY.md](./SECURITY.md) instead.

## Coding Style

- Keep implementations simple and explicit.
- Prefer small functions over clever abstractions.
- Keep CLI output actionable.
- Add comments only when they explain non-obvious behavior.
- Maintain compatibility with the current supported Python range in `pyproject.toml`.

## Documentation Style

- Be precise about what is implemented versus what is proven stable.
- Prefer practical examples that users can run immediately.
- Avoid marketing language.

## Community

By participating in this project, you agree to follow the [Code of Conduct](./CODE_OF_CONDUCT.md).
