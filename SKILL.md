# linkedin-cli skill

Use this repo when you need LinkedIn workflows from the terminal.

## Preconditions

- A valid logged-in LinkedIn session is already available in a supported browser, or
- `LINKEDIN_LI_AT` and `LINKEDIN_JSESSIONID` are exported in the environment.

## Common commands

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

- Prefer `--json` when another tool or script will consume the output.
- Use `LINKEDIN_PROXY` when requests need a proxy.
- Use browser fallback only when HTTP mode cannot complete an action.
- Fail fast on auth issues and tell the user to refresh cookies before retrying.

