---
name: ark-release-publisher
description: Publish already verified ARK package ZIPs and SHA-256 sidecars to an existing GitHub tag without browser or screen automation.
---

# ARK Release Publisher

Use this skill only when the user explicitly asks to publish a GitHub Release.

1. Read the consuming repository's release instructions and confirm its required
   build, tests, source identity, release notes, maturity and package checks are
   complete. The toolkit does not decide whether a package is stable.
2. Run from the consuming source checkout so its current `HEAD` can be compared
   with the existing remote tag. Never create, move, or replace a tag.
3. Locate the installed `scripts/publish.py` from this toolkit and pass the
   consuming repository, existing tag, title, notes file, manifest, source
   root, each ZIP and its `.sha256` sidecar. Use the terminal command documented
   in `docs/CONSUMER-SETUP.md`.
4. The command requires authenticated GitHub CLI (`gh`). It creates a draft,
   verifies the uploaded files and SHA-256 digests, then publishes. It does not
   use browser or computer-screen automation.
5. If any check fails or a draft is left behind, stop. Do not retry with
   overwrite, delete the draft, or alter the tag. Report the exact failure and
   preserve the draft for inspection.

Never request, print, or store a GitHub token. Never claim success until the
command confirms the published Release and all asset digests.

