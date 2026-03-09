# Auth Troubleshooting

## Contents

1. Resolution order
2. Environment variables
3. Config shape
4. Interpreting `auth-status`
5. Common failures
6. Browser extraction
7. Proxy and headless notes

## Resolution Order

`linkedin-cli` tries authentication in this order:

1. `LINKEDIN_COOKIE_HEADER`
2. `LINKEDIN_LI_AT` and `LINKEDIN_JSESSIONID`
3. Browser cookie extraction

Recommended baseline:

```bash
export LINKEDIN_COOKIE_HEADER='li_at=...; JSESSIONID="ajax:..."; ...'
uv run linkedin auth-status
```

Minimal environment fallback:

```bash
export LINKEDIN_LI_AT='AQ...'
export LINKEDIN_JSESSIONID='"ajax:123456789"'
uv run linkedin auth-status
```

## Environment Variables

Relevant variables:

- `LINKEDIN_COOKIE_HEADER`
- `LINKEDIN_LI_AT`
- `LINKEDIN_JSESSIONID`
- `LINKEDIN_BROWSER`
- `LINKEDIN_HEADLESS`
- `LINKEDIN_PROXY`
- `LINKEDIN_CONFIG`

Supported browser names:

- `chrome`
- `chromium`
- `brave`
- `edge`
- `firefox`

## Config Shape

The repository-level config file defaults to `config.yaml` or `config.yml`.

Example:

```yaml
fetch:
  count: 20

filter:
  enabled: false
  mode: "recent"

browser:
  preferred: "chrome"
  fallback_enabled: true
  headless: true

rate_limit:
  request_delay: 1.25
  max_retries: 3
  retry_base_delay: 3.0
  write_delay_min: 1.5
  write_delay_max: 4.0
  timeout: 20.0
```

## Interpreting `auth-status`

Healthy output usually includes:

- `basic-probe=ok`
- `voyager_me=ok:200`
- `voyager_feed=ok:200`
- `voyager_profile=ok:200`

Important summary fields:

- `source=env-cookie-header`, `source=env`, or `source=browser`
- `browser=<name>` when browser extraction was used
- `identity=<public-id-or-name>` when validation was able to resolve the account
- `cookies=<count>` to gauge whether you only have the minimum pair or a fuller cookie jar

## Common Failures

`No LinkedIn cookies found`

- Set `LINKEDIN_COOKIE_HEADER`, or
- export `LINKEDIN_LI_AT` and `LINKEDIN_JSESSIONID`, or
- log into LinkedIn in a supported local browser

`LINKEDIN_COOKIE_HEADER was provided but does not include li_at and JSESSIONID`

- Replace the header with the full request `cookie` header from a logged-in session

`LinkedIn session is missing required cookies`

- The resolved cookie jar does not contain both `li_at` and `JSESSIONID`

Redirect loops, `authwall`, `checkpoint`, or `challenge`

- Prefer a full cookie header instead of the minimal pair
- Re-login in the browser to refresh cookies
- Retry with browser extraction if the full cookie header is not available
- Treat this as an auth problem first, not a feed/profile bug

`Basic auth did not complete cleanly. Review the probe details above.`

- Use the per-probe lines to isolate whether `/me`, feed, or profile access is failing

## Browser Extraction

Browser extraction uses `browser-cookie3` and filters for LinkedIn domains.

If extraction appears wrong:

- set `LINKEDIN_BROWSER` explicitly
- confirm the browser is logged into `linkedin.com`
- prefer Chrome or Chromium first unless the user already knows another browser is the live session source

## Proxy and Headless Notes

Use `LINKEDIN_PROXY` when LinkedIn traffic must go through a proxy.

Use `LINKEDIN_HEADLESS=1` or `0` to influence browser fallback behavior for Playwright-backed write flows.

Proxy configuration affects transport and auth validation, so re-run `uv run linkedin auth-status` after changing it.
