---
name: linkedin-cli-auth
description: Diagnose and repair `linkedin-cli` authentication and runtime setup. Trigger on requests about `auth-status`, cookies, `LINKEDIN_COOKIE_HEADER`, `LINKEDIN_LI_AT`, `LINKEDIN_JSESSIONID`, browser extraction, `LINKEDIN_BROWSER`, `LINKEDIN_HEADLESS`, `LINKEDIN_PROXY`, `LINKEDIN_CONFIG`, `config.yaml`, redirect loops, authwall, checkpoint, session rejection, or any failure to authenticate LinkedIn requests in this repo.
---

# linkedin-cli-auth

Use this skill when the main problem is session health, cookie sourcing, browser extraction, config, or redirects.

## First Action

Run:

```bash
uv run linkedin auth-status
```

Use that output as the source of truth before trying any other LinkedIn command.

## Auth Resolution Order

`linkedin-cli` resolves auth in this order:

1. `LINKEDIN_COOKIE_HEADER`
2. `LINKEDIN_LI_AT` + `LINKEDIN_JSESSIONID`
3. Browser cookie extraction from Chrome, Chromium, Brave, Edge, or Firefox

Prefer the full cookie header over the minimal cookie pair whenever reads are unstable.

## Operating Rules

- Treat cookies and session headers like passwords.
- Never print raw cookie values in logs, issues, or shared transcripts.
- Fail fast when `auth-status` reports redirects, authwall, checkpoint, or missing required cookies.
- Re-run `auth-status` after each auth fix before retrying `feed`, `profile`, or write actions.
- Route to `$linkedin-cli-write` when the auth problem is resolved and the remaining task is a write action.

## Read Next

- Read [auth-troubleshooting.md](references/auth-troubleshooting.md) for failure mapping, env vars, config, and browser notes.
- Use `$linkedin-cli` when the task shifts back to read workflows.
