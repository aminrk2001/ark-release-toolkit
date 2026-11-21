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

### One-time setup on Windows

Install the official GitHub CLI with WinGet:

```powershell
winget install --id GitHub.cli --source winget
```

Close and reopen PowerShell or Windows Terminal, then sign in once:

```powershell
gh --version
gh auth login --hostname github.com --git-protocol https
```

Choose GitHub.com and HTTPS in the prompts, then complete the sign-in. GitHub
CLI's default sign-in may open a browser for this one-time authorization. After
that, the publisher runs from the terminal without browser or screen control.
Check that the intended account is active:

```powershell
gh auth status --hostname github.com
```

The account needs push access to the target repository. Fine-grained tokens need
the repository's `Contents: write` permission; if the tagged commit changes
files under `.github/workflows/` compared with the default branch, GitHub may
also require `Workflows: write` (or the corresponding `workflow` OAuth scope).
Use the official [Windows installation instructions](https://github.com/cli/cli/blob/trunk/docs/install_windows.md)
or [GitHub CLI authentication guide](https://docs.github.com/en/github-cli/github-cli/authenticating-with-github-cli)
for other setup details.

GitHub CLI stores credentials in the operating-system keyring when available;
otherwise it can fall back to a plain-text config file. Do not use
`--insecure-storage`. Never print the token with `gh auth token` or
`gh auth status --show-token`, and do not put a token in the manifest, command
line, or repository.

Use a reviewed, immutable Toolkit checkout. Run this from the consuming
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

