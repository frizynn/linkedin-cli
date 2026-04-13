---
name: linkedin-cli
description: "Operate LinkedIn from the terminal using the linkedin-cli repository. Use when the user wants to read their LinkedIn feed, search people or posts, fetch a profile, export LinkedIn data as JSON, publish posts, react to activities, or run any linkedin CLI command."
---

# linkedin-cli

Use this skill when you need LinkedIn workflows from the terminal using the `linkedin-cli` repository.

## Preconditions

- A valid logged-in LinkedIn session is available in a supported browser, or
- `LINKEDIN_COOKIE_HEADER` is exported (preferred), or
- `LINKEDIN_LI_AT` and `LINKEDIN_JSESSIONID` are exported in the environment.

## Standard Workflow

1. Verify the session: `linkedin auth-status`
2. If auth fails, refresh cookies before retrying any other command.
3. Choose the narrowest command that answers the request.
4. Prefer `--json` when another tool or script will consume the output.

## Common Commands

```bash
linkedin auth-status
linkedin feed --max 20
linkedin search "staff software engineer" --max 10
linkedin profile satyanadella
linkedin profile-posts satyanadella --max 10
linkedin post "Hello from linkedin-cli"
linkedin react urn:li:activity:123 --type like
linkedin comment urn:li:activity:123 "great post"
```

## Guidance

- Use `LINKEDIN_PROXY` when requests need a proxy.
- Use browser fallback only when HTTP mode cannot complete an action.
- For detailed command patterns, see `skills/linkedin-cli/`.
- For auth troubleshooting, see `skills/linkedin-cli-auth/`.
- For write operations, see `skills/linkedin-cli-write/`.
