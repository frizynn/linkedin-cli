---
name: linkedin-cli
description: Use the `linkedin-cli` repository to operate LinkedIn from the terminal. Trigger on requests to inspect the LinkedIn feed, search people or posts, fetch a profile, fetch profile posts, inspect an activity, export LinkedIn data as JSON, run `linkedin` commands, or decide which `linkedin-cli` command to use. Also use when the user mentions this repo or the `linkedin` CLI directly.
---

# linkedin-cli

Use this skill for read-heavy and command-selection workflows with the public `linkedin-cli` repo.

## Runtime Entry Points

Prefer the first working option:

```bash
uv run linkedin ...
linkedin ...
.venv/bin/linkedin ...
```

Run commands from the repository root when using `uv run` or `.venv/bin/linkedin`.

## Standard Workflow

1. Verify the session first with `uv run linkedin auth-status`.
2. Choose the narrowest read command that answers the request.
3. Prefer `--json` when another tool or script will consume the output.
4. Prefer `--output <file>` for `feed`, `search`, and `profile-posts` when the user wants an artifact on disk.
5. Switch to `$linkedin-cli-auth` when the problem is mainly auth, cookies, browser extraction, proxying, or redirects.
6. Switch to `$linkedin-cli-write` when the task is mainly posting, reacting, saving, unsaving, or commenting.

## Command Selection

| Need | Command |
|------|---------|
| Verify session and probes | `uv run linkedin auth-status` |
| Read home feed | `uv run linkedin feed --max 10` |
| Search people and posts | `uv run linkedin search "AI engineer" --max 10` |
| Fetch one profile | `uv run linkedin profile lebrero-juan-francisco` |
| Fetch recent posts from a profile | `uv run linkedin profile-posts lebrero-juan-francisco --max 10` |
| Inspect one activity | `uv run linkedin activity urn:li:activity:123 --json` |

## Identifier Rules

- Pass a profile public identifier like `satyanadella` or a full LinkedIn profile URL to `profile` and `profile-posts`.
- Pass a full activity URN, a numeric activity id, or a LinkedIn activity URL to `activity` and write-side commands.
- Normalize to `--json` before downstream processing when the request involves filtering, summarizing, or saving structured output.

## Read Next

- Read [command-cookbook.md](references/command-cookbook.md) for exact command patterns, JSON usage, and realistic examples.
- Use `$linkedin-cli-auth` for session recovery and runtime troubleshooting.
- Use `$linkedin-cli-write` for authenticated mutations and browser fallback behavior.
