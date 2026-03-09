# Command Cookbook

## Contents

1. Runtime entry points
2. Preflight
3. Read commands
4. Output modes
5. Identifier handling
6. Examples
7. Stability notes

## Runtime Entry Points

From the repository root, prefer:

```bash
uv run linkedin ...
```

If the project is already installed as a tool, use:

```bash
linkedin ...
```

If the repository has a local virtual environment but `uv` is not available, use:

```bash
.venv/bin/linkedin ...
```

## Preflight

Always start with:

```bash
uv run linkedin auth-status
```

Treat a degraded result as a blocker for all read and write requests until the session is repaired.

Healthy output usually contains:

- `basic-probe=ok`
- `voyager_me=ok:200`
- `voyager_feed=ok:200`
- `voyager_profile=ok:200`

## Read Commands

Fetch the authenticated feed:

```bash
uv run linkedin feed --max 10
uv run linkedin feed --max 10 --json
uv run linkedin feed --max 10 --json --output tmp/feed.json
```

Search people and posts:

```bash
uv run linkedin search "staff software engineer" --max 10
uv run linkedin search "MercadoLibre" --max 10 --json
uv run linkedin search "AI engineer" --max 10 --json --output tmp/search.json
```

Fetch a profile by public identifier or URL:

```bash
uv run linkedin profile satyanadella
uv run linkedin profile https://www.linkedin.com/in/satyanadella/ --json
```

Fetch posts from a profile:

```bash
uv run linkedin profile-posts satyanadella --max 10
uv run linkedin profile-posts satyanadella --max 10 --json
uv run linkedin profile-posts satyanadella --max 10 --json --output tmp/posts.json
```

Inspect one activity:

```bash
uv run linkedin activity urn:li:activity:123 --json
uv run linkedin activity 123 --json
uv run linkedin activity https://www.linkedin.com/feed/update/urn:li:activity:123/ --json
```

## Output Modes

Use the human-readable output when the user wants a quick answer in the terminal.

Use `--json` when:

- another tool will parse the result
- the user wants filtering, ranking, or persistence
- the output will be summarized into a report

Use `--output <file>` only on commands that implement it:

- `feed`
- `search`
- `profile-posts`

Do not assume `profile` or `activity` support `--output`; they do not.

## Identifier Handling

Profile commands accept:

- a public id like `lebrero-juan-francisco`
- a full profile URL like `https://www.linkedin.com/in/lebrero-juan-francisco/`

Activity-aware commands accept:

- a full URN like `urn:li:activity:123`
- a numeric id like `123`
- a full activity URL

When a user gives a profile URL, pass it directly or extract the final path segment.

When a user gives an activity URL, pass it directly or normalize it to the URN form.

## Examples

Read the latest 20 feed items as JSON:

```bash
uv run linkedin feed --max 20 --json
```

Inspect a profile and then fetch their last 5 posts:

```bash
uv run linkedin profile lebrero-juan-francisco --json
uv run linkedin profile-posts lebrero-juan-francisco --max 5 --json
```

Search a company name and persist results:

```bash
mkdir -p tmp
uv run linkedin search "MercadoLibre" --max 15 --json --output tmp/mercadolibre-search.json
```

Inspect one known activity:

```bash
uv run linkedin activity urn:li:activity:7323456789012345678 --json
```

## Stability Notes

Live end-to-end verification in the repository is strongest for:

- `auth-status`
- `feed`
- `profile`

The following are implemented and covered by tests, but are less battle-tested against live sessions:

- `search`
- `profile-posts`
- `activity`
- all write actions

When a read command fails unexpectedly, verify `auth-status` again before assuming a code regression.
