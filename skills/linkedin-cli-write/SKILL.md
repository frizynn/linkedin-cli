---
name: linkedin-cli-write
description: Use `linkedin-cli` for authenticated LinkedIn write actions. Trigger on requests to publish a LinkedIn post, react, unreact, save, unsave, or comment through the terminal, or when a user needs guidance on write-side browser fallback, visibility options, reaction types, or safe mutation workflows in this repo.
---

# linkedin-cli-write

Use this skill for authenticated LinkedIn mutations in the `linkedin-cli` repository.

## Preflight

Run `uv run linkedin auth-status` first. Do not attempt write actions against a degraded session.

## Write Commands

```bash
uv run linkedin post "Hello from linkedin-cli" --visibility connections
uv run linkedin react urn:li:activity:123 --type like
uv run linkedin unreact urn:li:activity:123
uv run linkedin save urn:li:activity:123
uv run linkedin unsave urn:li:activity:123
uv run linkedin comment urn:li:activity:123 "great post"
```

## Operating Rules

- Confirm the target activity identifier before sending a mutation.
- Keep write volume conservative; do not automate repeated posting or engagement loops.
- Prefer `connections` visibility unless the user explicitly requests `public`.
- Use `$linkedin-cli-auth` immediately when writes fail because of session health, redirects, or missing cookies.
- Read the reference doc before relying on browser fallback behavior.

## Read Next

- Read [write-workflows.md](references/write-workflows.md) for command coverage, fallback behavior, and failure mapping.
- Use `$linkedin-cli` for read-side inspection before mutating unknown activities.
