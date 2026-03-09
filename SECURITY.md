# Security Policy

## Scope

This policy covers vulnerabilities in the `linkedin-cli` codebase itself.

It does not cover:
- LinkedIn platform vulnerabilities
- account restrictions triggered by personal misuse
- exposure caused by intentionally sharing your own cookies or session data publicly

## Supported Versions

Security fixes are expected for the latest version on the default branch.

## Reporting a Vulnerability

Please report suspected vulnerabilities privately.

Preferred path:
- use GitHub private vulnerability reporting if it is enabled for the repository

Fallback:
- contact the maintainer privately through GitHub

Do not open a public issue for:
- leaked session cookies
- auth bypasses
- credential exposure
- account data disclosure
- remote code execution

## What to Include

Please include:
- a clear description of the problem
- impact and affected component
- reproduction steps
- any patch ideas if you have them

Please do not include live credentials.

## Sensitive Data Rules

Treat all of the following as secrets:
- `LINKEDIN_COOKIE_HEADER`
- `LINKEDIN_LI_AT`
- `LINKEDIN_JSESSIONID`
- browser state exports
- HAR files containing authenticated requests

Before sharing logs or screenshots:
- rotate or invalidate the session if needed
- remove account identifiers where possible
- remove cookie values entirely

## Response Expectations

The project will try to:
- acknowledge a report in a reasonable timeframe
- reproduce the issue
- fix or mitigate confirmed vulnerabilities
- credit the reporter if they want attribution

There is no guarantee of SLA, but responsible private reporting is appreciated.
