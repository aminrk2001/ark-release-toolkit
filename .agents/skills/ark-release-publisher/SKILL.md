---
name: ark-release-publisher
description: Set up or activate the ARK Release Toolkit in a project using Codex, Claude Code, Cursor, GitHub Copilot, VS Code, Gemini CLI, or another agent that supports Agent Skills; publish verified ARK package ZIPs and SHA-256 sidecars to an existing GitHub tag, or edit an existing GitHub Release when explicitly requested.
---

# ARK Release Toolkit

Use this skill when the user asks to activate, install, configure, or use the
ARK Release Toolkit, or explicitly asks to publish a GitHub Release or edit an existing Release with it.
Read the Toolkit's `docs/CONSUMER-SETUP.md` and the consuming project's
instructions before acting.

## Activation

Activation configures the project and verifies prerequisites. It does not
publish a Release, create or move tags, or change the project's release policy.

1. Before installing or changing anything, tell the user that GitHub CLI may
   require a one-time GitHub account sign-in. Explain that you will pause while
   they complete that authorization, then resume setup. Never ask them to send
   a password, personal access token, or authorization code.
2. Inspect the project's `AGENTS.md`, README, release instructions, relevant
   configuration, current Git status, and existing Toolkit setup. Preserve
   uncommitted work. Stop only for a concrete conflict or action requiring
   permissions the environment does not grant; complete independent setup work
   and report the blocker.
3. Read `docs/CONSUMER-SETUP.md`. Install/reuse a clean Toolkit checkout at the
   documented immutable commit
   `a9cda703f26715d3904bc5e53261c02eb17f7fc7`, using a project tools/cache
   location that will not enter the product archive. Never overwrite an
   existing checkout with local changes.
4. Install the canonical skill directory into the project folder supported by
   the current AI host: Codex and Gemini CLI use
   `.agents/skills/ark-release-publisher/`; Claude Code uses
   `.claude/skills/ark-release-publisher/`; Cursor uses
   `.cursor/skills/ark-release-publisher/`; GitHub Copilot (including VS Code
   Agent mode and Copilot CLI) uses
   `.github/skills/ark-release-publisher/`. For VS Code, follow the selected
   harness's skill locations. If the project uses multiple agents, install
   byte-identical copies for each and keep the Toolkit copy canonical. Inspect
   any existing skill before changing it. In cloud sessions, use a committed
   project skill and verify that the cloud agent discovers it; personal local
   skills may not be available there.
5. Check Git, Python 3.10+, and GitHub CLI. The local publisher and Release
   editor invoke `gh`, so it must be installed on PATH in the same environment
   that runs those commands. A connected GitHub app in ChatGPT does not provide
   the local process with the CLI executable or its stored credentials. Local
   package building alone does not require GitHub CLI. Install missing tools
   using official platform instructions when terminal access, network access,
   and permissions allow. Do not claim an installation succeeded without
   checking the version.
6. Run `gh auth status --hostname github.com` in the command's execution
   environment. If sign-in is required, announce the need before starting, run
   `gh auth login --hostname github.com --git-protocol https`, wait while the
   user completes GitHub's authorization, check status again, and continue
   setup. Never print, request, or store credentials.
7. Configure the manifest and reusable workflow only from verified project
   files and its documented release policy. Do not invent an allowlist or
   silently change release rules. Do not create or move tags.
8. Verify setup and report the Toolkit commit, skill path, prerequisite
   versions, authentication status, project changes, and any remaining
   configuration or specific blocker.

The user's intended manual step is GitHub account authorization. Cloud agents
may not share the local machine's GitHub CLI installation or interactive sign-in
flow. Check `gh auth status` in the active environment; if it cannot authorize
GitHub, finish independent setup and continue publication from a local agent or
terminal after the user signs in there. If operating system restrictions,
network access, missing terminal/file tools, or agent capabilities prevent
another step, explain the exact limit and finish all independent work.

## Publish a GitHub Release

Only publish when the user explicitly asks for publication. Toolkit
activation, package building, or release preparation alone is not permission to
publish.

1. Read the consuming repository's release instructions and confirm its required
   build, tests, source identity, release notes, maturity and package checks are
   complete. The toolkit does not decide whether a package is stable.
2. Run from the consuming source checkout so its current `HEAD` can be compared
   with the existing remote tag. Never create, move, or replace a tag.
3. Locate the installed `scripts/publish.py` from this Toolkit and pass the
   consuming repository, existing tag, title, notes file, manifest, source
   root, each ZIP and its `.sha256` sidecar. Use the terminal command
   documented in `docs/CONSUMER-SETUP.md`.
4. Check `gh auth status --hostname github.com` in the same environment that
   runs the publisher, without showing a token. Authentication in ChatGPT's
   GitHub app does not count as local CLI authentication. If `gh` is not
   authenticated, tell the user before starting the one-time sign-in, run
   `gh auth login --hostname github.com --git-protocol https`, pause while they
   complete GitHub authorization, then verify sign-in and resume publication.
   If the current cloud session cannot perform interactive authorization, do
   not ask the user to copy credentials into it; finish publication from a
   local terminal after confirming `gh auth status`. Do not ask the user to copy
   credentials into chat.
5. The command creates a draft, verifies the uploaded files and SHA-256 digests,
   then publishes without browser or computer-screen automation.
6. If any check fails or a draft is left behind, stop. Do not retry with
   overwrite, delete the draft, or alter the tag. Report the exact failure and
   preserve the draft for inspection.

## Edit an existing GitHub Release

Only edit an existing Release when the user explicitly asks for that change.
Read the consuming project's release instructions first and identify the exact
repository and tag. Do not use an edit request as permission to publish a new
version, delete a Release, rename a tag, or change its target commit.

1. Check `gh auth status --hostname github.com` in the same environment that
   runs the editor, without showing credentials. A GitHub app connection in
   ChatGPT does not provide local CLI authentication. If `gh` is unavailable,
   follow the one-time installation and authorization steps above; never ask
   for a password or token in chat.
2. Run the installed `scripts/edit_release.py` with the exact Release tag and
   requested fields. The command defaults to a dry run. Inspect the plan before
   adding `--apply`.
3. It supports title and release notes, draft/prerelease and Latest status,
   discussion category, and attached asset labels, additions, removals, and
   explicit replacements. It does not change the tag or delete the Release.
4. Existing assets are never overwritten implicitly. For a replacement, the
   command uploads and verifies a temporary asset before removing the old one.
   If a later API step fails, inspect the Release and report any partial change
   or temporary asset; GitHub changes are not transactional.
5. Immutable Releases still permit some metadata edits, but GitHub blocks
   asset changes. The command checks immutability and refuses asset changes
   when the state is immutable or unavailable. Verify the final Release fields
   and asset digests before reporting success.

Never request, print, or store a GitHub token. Never claim success until the
command confirms the published Release and all asset digests.
