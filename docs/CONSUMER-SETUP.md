# Configure a consuming project

Each project owns its release policy and supplies a manifest. The toolkit owns
the reusable validation and packaging implementation. The first supported
profile is a WordPress plugin with one or more product slugs. Review every path
before adopting an example.

## Activate this Toolkit with an AI chat

This is the recommended path for a developer using Codex or another AI coding
chat with access to the project's files and terminal. The AI should carry out
the setup; the user should only need to complete GitHub's account authorization
if the GitHub CLI is not already signed in.

### What the AI must tell you first

Before it installs or changes anything, the AI should say:

> I can set up the ARK Release Toolkit in this project and verify it. The
> GitHub CLI may need a one-time sign-in to your GitHub account. If so, I will
> start that sign-in and pause while you approve it in GitHub; I will then
> continue the setup. I will not ask you to send me a password or token.
> Activating the Toolkit does not publish a Release.

This early notice matters because GitHub may open a browser or show a device
authorization step. The AI should wait for the user to finish that step, check
the sign-in, and then continue without asking the user to repeat the setup.

### What the AI does

1. Read the consuming project's `AGENTS.md`, README, release instructions,
   relevant configuration, and current Git status. Follow project-specific
   rules and preserve existing user changes.
2. Check whether the project already has a Toolkit checkout or skill. Reuse a
   valid installation; do not overwrite uncommitted work or replace a different
   Toolkit version without explaining the issue.
3. Install a reviewed, immutable Toolkit checkout for the local publisher. The
   current publisher implementation is at commit
   `142d6140d73e132398ca0deb330de1e50e7adec2`. For example, from the project
   root, a clean setup can use:

   ```sh
   git clone https://github.com/aminrk2001/ark-release-toolkit.git .tools/ark-release-toolkit
   git -C .tools/ark-release-toolkit checkout --detach 142d6140d73e132398ca0deb330de1e50e7adec2
   ```

   Keep this checkout out of the product package and ordinary project commits.
   The AI may add `.tools/ark-release-toolkit/` to the project's local
   `.git/info/exclude`, or use the project's existing tools/cache location.
   If that exact checkout already exists, verify its commit instead of cloning
   over it. For later Toolkit updates, review the new source and pin the
   intended commit explicitly.
4. Install the project skill by copying
   `.agents/skills/ark-release-publisher/` from the pinned Toolkit checkout
   into the consuming project's
   `.agents/skills/ark-release-publisher/`. Preserve local project
   instructions and inspect any existing skill before changing it. Codex uses
   repository-local skills under `.agents/skills/`; other coding agents may
   have a different discovery mechanism. If the current chat can read the
   Toolkit skill but cannot make it available to future chats, say so and give
   the supported next step for that agent.
5. Check for Git, Python 3.10 or later (the Toolkit CI currently tests Python
   3.12), and GitHub CLI (`gh`). Install missing prerequisites using the
   operating system's official method when the chat has the needed terminal
   and installation permissions. On Windows, the official GitHub CLI package
   can be installed with `winget install --id GitHub.cli --source winget`.
   See [GitHub CLI installation](https://github.com/cli/cli#installation) for
   other platforms. If network, operating-system policy, or permissions prevent
   an installation, complete the independent setup and report exactly what is
   blocked.
6. Check `gh auth status --hostname github.com`. If the intended account is
   not signed in, explain this before starting setup, then run
   `gh auth login --hostname github.com --git-protocol https`. Wait while the
   user completes GitHub's sign-in/authorization, then check the status again
   and continue. Do not ask the user to copy a token, password, or code into
   chat. Do not print or expose credentials.
7. Confirm the project manifest and caller workflow requirements below. Do not
   add guessed file allowlists, change release policy, create tags, or publish a
   Release just to finish activation.
8. Summarize the installed Toolkit commit, skill location, prerequisites and
   authentication result, plus any project configuration still needed.

The intended user interaction is the GitHub account authorization step. An AI
chat still needs working access to the project terminal and files; computer
administration policies, blocked network access, missing tools, or an agent
that cannot persist project files can require help outside the chat. The AI
must name such a concrete limitation rather than claim setup is complete.

### Copyable prompt

Paste this in the consuming project's AI coding chat:

```text
Activate the ARK Release Toolkit for this project. Read the Toolkit's
docs/CONSUMER-SETUP.md and .agents/skills/ark-release-publisher/SKILL.md,
along with this project's AGENTS.md, README, release instructions, and relevant
configuration before changing anything.

At the start, tell me that GitHub CLI may require a one-time GitHub account
sign-in and that you will pause only for me to complete that authorization,
then continue. Do not ask me for a password, token, or authorization code.

Inspect the current Git status and existing setup. Preserve my work. Pin a clean
Toolkit checkout to commit
142d6140d73e132398ca0deb330de1e50e7adec2, install the project skill in the
location this coding agent discovers, check/install Git, Python 3.10+, and
GitHub CLI where permitted, then verify gh authentication. If sign-in is
needed, start it, wait for my GitHub authorization, verify it, and resume the
remaining steps yourself.

Complete the project manifest/workflow setup only when the project's actual
files and release policy make the correct values clear. Do not guess allowlists,
change release policy, create or move tags, or publish a GitHub Release during
activation. Verify each setup step and report completed work and any precise
blocker.
```

If the chat does not have project terminal/file access, the user can follow the
manual setup below or switch to an AI coding environment with those tools.

## Manual setup for a developer

1. Review this guide and `examples/manifest.wordpress-plugin.json`.
2. Clone the Toolkit and check out a reviewed immutable commit or tag. The
   current local publisher reference is
   `142d6140d73e132398ca0deb330de1e50e7adec2`; do not track a floating branch
   for release use.
3. Copy the Toolkit skill folder into the project-local
   `.agents/skills/ark-release-publisher/` when using Codex. Read its
   `SKILL.md` and follow your coding agent's own project-skill installation
   rules if using a different agent.
4. Install Git, Python 3.10+, and GitHub CLI. Sign in with
   `gh auth login --hostname github.com --git-protocol https` and confirm with
   `gh auth status --hostname github.com`.
5. Configure the project manifest and caller workflow described below.
6. Build and verify packages, then follow the project's release gates. Toolkit
   activation alone does not publish a Release.

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

Publication is a separate, explicit action. The project must already have
passed its release checks, and the target Git tag must already exist and point
to the current `HEAD`. The publisher reproduces the selected ZIPs from the
checked-in manifest, compares their bytes and sidecars, creates a GitHub draft,
checks every uploaded asset's SHA-256 digest, and only then publishes it. It
does not create or move tags, replace existing releases, or overwrite assets.

### One-time GitHub CLI setup

Install GitHub CLI using the [official installation instructions](https://github.com/cli/cli#installation).
On Windows, WinGet can install it with:

```powershell
winget install --id GitHub.cli --source winget
```

Close and reopen PowerShell or Windows Terminal, then sign in once:

```sh
gh --version
gh auth login --hostname github.com --git-protocol https
```

Choose GitHub.com and HTTPS in the prompts, then complete the sign-in. GitHub
CLI's sign-in may open a browser or request device authorization for this
one-time approval. Once approved, the AI can continue by checking:

```sh
gh auth status --hostname github.com
```

The account needs push access to the target repository. Fine-grained tokens need
the repository's `Contents: write` permission; if the tagged commit changes
files under `.github/workflows/` compared with the default branch, GitHub may
also require `Workflows: write` (or the corresponding `workflow` OAuth scope).

GitHub CLI stores credentials in the operating-system keyring when available;
otherwise it can fall back to a plain-text config file. Do not use
`--insecure-storage`. Never print the token with `gh auth token` or
`gh auth status --show-token`, and do not put a token in the manifest, command
line, or repository.

Use a reviewed, immutable Toolkit checkout. Run this from the consuming
project's source checkout, where `git rev-parse HEAD` identifies the intended
source commit:

```sh
python .tools/ark-release-toolkit/scripts/publish.py --repository OWNER/REPOSITORY --tag v1.2.3 --title "Version 1.2.3" --notes-file RELEASE-1.2.3.md --manifest package-files.json --source-root . --asset dist/plugin-v1.2.3.zip --asset dist/plugin-v1.2.3.zip.sha256
```

Repeat `--asset` for each package and its matching `.sha256` sidecar. Add
`--prerelease` for a prerelease. This command can be run by an AI through its
terminal tool; it does not use browser or computer-screen interaction. If
upload or verification fails, the publisher leaves any created Release as a
draft for inspection and does not replace or delete it.

## Review before enabling publication

Confirm that the allowlist includes all runtime files and excludes development
tools, local settings, credentials, caches, and test fixtures. Build twice
from the same source and compare archive hashes. Test the resulting package in
the project's supported runtime matrix. Keep the reusable workflow read-only;
the optional local publisher uses the operator's authenticated `gh` CLI only
after the consuming project's release gate has passed.
