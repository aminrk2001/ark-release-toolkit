---
name: ark-release-publisher
description: Set up or activate the ARK Release Toolkit in a project, or publish verified ARK package ZIPs and SHA-256 sidecars to an existing GitHub tag when explicitly requested. Guides Codex through project setup and browser-free GitHub release publication.
---

# ARK Release Toolkit

Use this skill when the user asks to activate, install, configure, or use the
ARK Release Toolkit, or explicitly asks to publish a GitHub Release with it.
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
   `3a3769cc7cc95697eaf3fe038e6ec1ef647b1445`, using a project tools/cache
   location that will not enter the product archive. Never overwrite an
   existing checkout with local changes.
4. Copy this skill directory into the consumer project's
   `.agents/skills/ark-release-publisher/` for Codex discovery. Inspect an
   existing skill before changing it; preserve project-specific instructions.
   If the current AI environment does not discover project-local skills, use
   this skill's instructions in the current conversation and explain the
   supported persistence option for that environment.
5. Check Git, Python 3.10+, and GitHub CLI. Install missing tools using official
   platform instructions when terminal access, network access, and permissions
   allow. Do not claim an installation succeeded without checking the version.
6. Run `gh auth status --hostname github.com`. If sign-in is required, announce
   the need before starting, run
   `gh auth login --hostname github.com --git-protocol https`, wait while the
   user completes GitHub's authorization, check status again, and continue
   setup. Never print, request, or store credentials.
7. Configure the manifest and reusable workflow only from verified project
   files and its documented release policy. Do not invent an allowlist or
   silently change release rules. Do not create or move tags.
8. Verify setup and report the Toolkit commit, skill path, prerequisite
   versions, authentication status, project changes, and any remaining
   configuration or specific blocker.

The user's intended manual step is GitHub account authorization. If operating
system restrictions, network access, missing terminal/file tools, or agent
capabilities prevent another step, explain the exact limit and finish all
independent work.

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
4. Check `gh auth status --hostname github.com` without showing a token. If not
   authenticated, tell the user before starting the one-time sign-in, run
   `gh auth login --hostname github.com --git-protocol https`, pause while they
   complete GitHub authorization, then verify sign-in and resume publication.
   Do not ask the user to copy credentials into chat.
5. The command creates a draft, verifies the uploaded files and SHA-256 digests,
   then publishes without browser or computer-screen automation.
6. If any check fails or a draft is left behind, stop. Do not retry with
   overwrite, delete the draft, or alter the tag. Report the exact failure and
   preserve the draft for inspection.

Never request, print, or store a GitHub token. Never claim success until the
command confirms the published Release and all asset digests.
