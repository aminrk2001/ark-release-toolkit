# Configure a consuming project

Each project owns its release policy and supplies a manifest. The toolkit owns
the reusable validation and packaging implementation. The first supported
profile is a WordPress plugin with one or more product slugs. Review every path
before adopting an example.

## Activate this Toolkit with an AI chat

This is the recommended path for a developer using Codex, Claude Code, Cursor,
GitHub Copilot, VS Code, Gemini CLI, or another AI coding agent with access to
the project's files and terminal. The Toolkit uses one shared Agent Skill; the
project folder where it is installed depends on the agent. The AI should carry
out the setup; the user should only need to complete GitHub's account
authorization if the GitHub CLI is not already signed in.

### Project skill locations

The Toolkit keeps one canonical skill at
`.agents/skills/ark-release-publisher/`. Copy that same folder, without
rewriting its instructions, to the project location supported by the AI agent:

| AI coding agent | Project skill folder |
| --- | --- |
| OpenAI Codex | `.agents/skills/ark-release-publisher/` |
| Claude Code | `.claude/skills/ark-release-publisher/` |
| Cursor | `.cursor/skills/ark-release-publisher/` |
| GitHub Copilot, including VS Code Agent mode and Copilot CLI | `.github/skills/ark-release-publisher/` |
| Gemini CLI | `.agents/skills/ark-release-publisher/` |

VS Code skill discovery depends on the selected agent harness. Use the row for
that harness; for GitHub Copilot in VS Code, use `.github/skills/`. The official
guides explain [Claude Code skills](https://code.claude.com/docs/en/skills),
[Cursor skills](https://cursor.com/docs/skills),
[GitHub Copilot skills](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills),
[VS Code Agent Skills](https://code.visualstudio.com/docs/agent-customization/agent-skills),
and [Gemini CLI Agent Skills](https://geminicli.com/docs/cli/skills/).

If the project uses more than one agent, install byte-identical copies in each
agent's listed folder and keep the Toolkit copy as the source of truth. Avoid
editing one copy independently. After installation, start a fresh chat (or
refresh skills using that agent's supported command) and confirm the skill is
available.

For cloud agents, commit the project-level skill in the repository. Do not rely
on a personal skill installed only on the developer's machine. Cloud sessions
may not share the local machine's `gh` installation or sign-in: check
`gh auth status --hostname github.com` inside the actual environment. If it
cannot run an interactive GitHub sign-in, finish project setup there and use a
local coding agent/terminal for the browser-free publisher after GitHub CLI is
authorized. Never copy a token into chat or cloud configuration.

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
   `a9cda703f26715d3904bc5e53261c02eb17f7fc7`. For example, from the project
   root, a clean setup can use:

   ```sh
   git clone https://github.com/aminrk2001/ark-release-toolkit.git .tools/ark-release-toolkit
   git -C .tools/ark-release-toolkit checkout --detach a9cda703f26715d3904bc5e53261c02eb17f7fc7
   ```

   Keep this checkout out of the product package and ordinary project commits.
   The AI may add `.tools/ark-release-toolkit/` to the project's local
   `.git/info/exclude`, or use the project's existing tools/cache location.
   If that exact checkout already exists, verify its commit instead of cloning
   over it. For later Toolkit updates, review the new source and pin the
   intended commit explicitly.
4. Identify the current AI agent and install the canonical
   `.agents/skills/ark-release-publisher/` folder from the pinned Toolkit
   checkout into the corresponding project skill folder in the table above.
   Preserve local project instructions and inspect any existing skill before
   changing it. If the user works with multiple agents, install identical copies
   for each. Verify discovery in a fresh chat or with that agent's refresh
   command. If the current chat can read the Toolkit skill but cannot make it
   available to future chats, explain the supported next step.
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
docs/CONSUMER-SETUP.md and its canonical
.agents/skills/ark-release-publisher/SKILL.md, along with this project's
AGENTS.md, README, release instructions, and relevant configuration before
changing anything. Identify the current AI agent and install the skill into
the project folder listed for that agent in the setup guide. For more than one
agent, install identical copies in each supported location.

At the start, tell me that GitHub CLI may require a one-time GitHub account
sign-in and that you will pause only for me to complete that authorization,
then continue. Do not ask me for a password, token, or authorization code.

Inspect the current Git status and existing setup. Preserve my work. Pin a clean
Toolkit checkout to commit
a9cda703f26715d3904bc5e53261c02eb17f7fc7, install the project skill in the
location this coding agent discovers, check/install Git, Python 3.10+, and
GitHub CLI where permitted, then verify gh authentication. If sign-in is
needed and this environment supports interactive authorization, start it, wait
for my GitHub authorization, verify it, and resume the remaining steps yourself.
If this is a cloud session that cannot complete sign-in, finish the independent
setup and tell me to authorize GitHub CLI from a local terminal before publishing.

Complete the project manifest/workflow setup only when the project's actual
files and release policy make the correct values clear. Do not guess allowlists,
change release policy, create or move tags, or publish a GitHub Release during
activation. Verify each setup step and report completed work and any precise
blocker.
```

If the chat does not have project terminal/file access, the user can follow the
manual setup below or switch to an AI coding environment with those tools. In
cloud sessions, check whether that session can run and authorize GitHub CLI; if
it cannot perform interactive sign-in, use a local terminal for Release
publication.

## Manual setup for a developer

1. Review this guide and `examples/manifest.wordpress-plugin.json`.
2. Clone the Toolkit and check out a reviewed immutable commit or tag. The
   current local publisher reference is
   `a9cda703f26715d3904bc5e53261c02eb17f7fc7`; do not track a floating branch
   for release use.
3. Copy the canonical Toolkit skill folder into the consuming project's
   corresponding project skill location from the table above. For multiple
   agents, install identical copies for each. Read the `SKILL.md` and follow
   your coding agent's official discovery instructions.
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

Both local Release commands (`publish.py` and `edit_release.py`) invoke
`gh` directly. Install and authenticate GitHub CLI in the same environment
where the Toolkit command will run. A Git executable or a connected GitHub app
in ChatGPT does not make the local `gh` executable or its saved credentials
available to that command. Package building and the reusable CI packaging
workflow do not require a local GitHub CLI installation. The one-time CLI
sign-in may open a browser or prompt for device authorization; Release actions
themselves do not automate browser interactions.

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

## Edit an existing GitHub Release

Use `scripts/edit_release.py` when the user explicitly asks to update a Release
that already exists. It can change the title and release notes, draft and
prerelease status, Latest selection, an existing discussion category, and
attached asset labels/files. It never creates or deletes a Release, renames a
tag, or changes a tag's target commit.

This is a local command that invokes `gh`; complete the
[one-time GitHub CLI setup](#one-time-github-cli-setup) in the same environment
before running it. Installing the ChatGPT GitHub app alone is not sufficient
for this local process.

The command first reads the exact Release by tag and prints a dry-run plan. No
changes are made unless `--apply` is present. Example:

```sh
python .tools/ark-release-toolkit/scripts/edit_release.py \
  --repository OWNER/REPOSITORY \
  --tag v1.2.3 \
  --title "Version 1.2.3" \
  --notes-file RELEASE-1.2.3.md
```

Review the plan, then add `--apply` to make those changes. Other supported
options include:

- `--prerelease` / `--no-prerelease`
- `--draft` / `--no-draft`
- `--latest` / `--no-latest`
- `--discussion-category CATEGORY`
- `--asset PATH` to add a new asset
- `--remove-asset EXACT_NAME` to remove an attached asset
- `--replace-asset PATH` to replace an asset with the same filename
- `--asset-label NAME=LABEL` to set a label, or `NAME=` to clear it

Existing assets are never overwritten implicitly. Replacement uploads a
uniquely named temporary asset, verifies its size and SHA-256 digest, and then
swaps it for the old asset. If GitHub rejects a later replacement step, the
error identifies any temporary asset left attached so it can be inspected.
Operations use separate GitHub requests and are not transactional: if a later
requested operation fails, earlier completed changes may remain. Review the
dry-run plan and check the Release after any failure.

GitHub immutable Releases still allow title, notes, prerelease and Latest
changes, but do not allow asset additions, replacements, or removals. The tool
checks the Release's immutable state and refuses asset changes when GitHub marks
it immutable or that state cannot be verified. See GitHub's
[release editing rules](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository#editing-a-release).

Editing requires GitHub CLI authentication and repository write access. Check
`gh auth status --hostname github.com`; never place a token in a command,
manifest, or repository file.

## Review before enabling publication

Confirm that the allowlist includes all runtime files and excludes development
tools, local settings, credentials, caches, and test fixtures. Build twice
from the same source and compare archive hashes. Test the resulting package in
the project's supported runtime matrix. Keep the reusable workflow read-only;
the optional local publisher uses the operator's authenticated `gh` CLI only
after the consuming project's release gate has passed.
