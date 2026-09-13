# AI Map research tools

This directory contains local-only research utilities. They are not part of the
public website build and must not be deployed to GitHub Pages.

## Installed tools

- Playwright 1.63.0 for Node and 1.62.0 for Python: browser validation,
  screenshots, and AI Map interaction testing.
- XActions 3.5.0: read-only lookup of public X profiles.
- linkedin-scraper 3.1.2: isolated evaluation only; disabled as a production
  data source.

The Python environment uses Python 3.12 because the patched dependency releases
are no longer compatible with the machine's older system Python.

## Safety rules

1. Use XActions only for public, read-only profile lookup. Do not enable posting,
   following, messaging, or engagement automation.
2. Do not store X or LinkedIn credentials in this repository.
3. Do not copy browser cookies from a personal account into a cloud task.
4. Keep Playwright authentication state, browser profiles, `.env`, and
   `session.json` in the ignored local paths defined in the root `.gitignore`.
5. Do not run automated LinkedIn collection. LinkedIn prohibits third-party
   scraping and automation; the package is retained only for isolated technical
   evaluation.
6. Treat every external result as a candidate. Require source evidence and
   identity matching before writing it to the company database.
7. Never automatically overwrite a verified database value with scraper output.

## Verification status

- Node dependency audit: zero known vulnerabilities after pinned security
  overrides.
- Node registry signatures: verified for the installed packages.
- Python dependency audit: zero known vulnerabilities.
- Playwright Node and Python smoke tests: passed in fresh, unauthenticated
  browser contexts.
- XActions public profile smoke test: passed without an X login.
- linkedin-scraper import test: passed without connecting to LinkedIn.

## License note

The `linkedin-scraper` 3.1.2 package metadata says Apache 2.0, while the source
repository's current `LICENSE` file is GPL-3.0. Do not copy or distribute its
source in this project until the upstream licensing inconsistency is resolved.
