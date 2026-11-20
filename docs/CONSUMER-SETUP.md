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
GitHub Release. The caller remains responsible for project tests, release
eligibility, stable/development classification, and factual release notes. The
optional local publisher checks source/tag identity and asset digests before it
publishes.

## Browser-free release publication

Publication is a separate, explicit command. The project must already have
passed its own release checks, and the target Git tag must already exist and
point to the current `HEAD`. The publisher reproduces the selected ZIPs from the
checked-in manifest, compares their bytes and sidecars, creates a GitHub draft,
checks every uploaded asset's SHA-256 digest, and only then publishes it. It
does not create or move tags, replace existing releases, or overwrite assets.

Install GitHub CLI (`gh`) and authenticate it for the target repository with
permission to create Releases. Authentication is stored by `gh`; do not put a
token in the manifest, command line, or repository. Run this from the consuming
project's source checkout, where `git rev-parse HEAD` identifies the intended
source commit:

```sh
python toolkit/scripts/publish.py --repository OWNER/REPOSITORY --tag v1.2.3 --title "Version 1.2.3" --notes-file RELEASE-1.2.3.md --manifest package-files.json --source-root . --asset dist/plugin-v1.2.3.zip --asset dist/plugin-v1.2.3.zip.sha256
```

Repeat `--asset` for each package and its matching `.sha256` sidecar. Add
`--prerelease` for a prerelease. This command can be run by an AI through its
terminal tool; it does not use a browser or computer-screen interaction. If
upload or verification fails, the publisher leaves any created Release as a
draft for inspection and does not replace or delete it.

## Review before enabling publication

Confirm that the allowlist includes all runtime files and excludes development
tools, local settings, credentials, caches, and test fixtures. Build twice
from the same source and compare archive hashes. Test the resulting package in
the project's supported runtime matrix. Keep the reusable workflow read-only;
the optional local publisher uses the operator's authenticated `gh` CLI only
after the consuming project's release gate has passed.

