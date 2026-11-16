# Configure a consuming project

Each project owns its release policy and supplies a manifest. The toolkit owns
the reusable validation and packaging implementation. The first supported
profile is a WordPress plugin with one or more product slugs. Review every path
before adopting an example.

## Required project configuration

- A checked-in JSON manifest with `schema_version: 1` and a `products` object.
- One product entry per installable archive, with a lowercase WordPress plugin
  `slug` and a non-empty `files` allowlist relative to that plugin directory.
- A source directory named exactly as each product slug. Its main plugin file
  must be `<slug>.php` and contain a numeric `Version:` header.
- All production files in `assets/`, `includes/` and `languages/` must be listed;
  stale entries and unlisted files in those directories block package creation.
- Markdown files are placed under `<slug>/docs/` in the ZIP; other allowlisted
  files keep their relative path under `<slug>/`.
- A GitHub Actions workflow that calls the reusable workflow at a reviewed,
  immutable toolkit tag. Avoid floating `main` references for releases.
- Project-specific automated checks and an explicit stable/development release
  policy. The manifest does not by itself mark a build stable.

## Private repository access

If this toolkit repository is private, enable GitHub's repository Actions
setting that permits the consuming repository to access its reusable workflows
and actions. Grant access only to the intended repositories. A public toolkit
does not need this setting. Never put a personal access token or other secret
in the manifest or workflow source.

## Caller workflow shape

The consuming project should call the toolkit's reusable workflow from a pinned
release tag and pass the manifest path plus the same tag in `toolkit-ref`. The
reusable workflow checks out the caller's source and the pinned toolkit code,
then uploads ZIPs and SHA-256 sidecars as CI artifacts. It does not publish a
GitHub Release. The caller remains responsible for project tests, source/tag
matching, release notes, stable/development classification, and asset digest
checks.

## Review before enabling publication

Confirm that the allowlist includes all runtime files and excludes development
tools, local settings, credentials, caches, and test fixtures. Build twice
from the same source and compare archive hashes. Test the resulting package in
the project's supported runtime matrix. Keep the reusable workflow read-only;
do not grant write access to Releases unless the consuming project has its own
verified release gate.
