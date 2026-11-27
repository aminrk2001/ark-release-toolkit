# ARK Release Toolkit

Build reproducible, allowlist-based ZIP packages for WordPress plugins and publish
verified assets to GitHub Releases. Use a checked-in JSON manifest with reusable
GitHub Actions, or ask an AI coding agent to set up the Toolkit in your project.

## What it does

- Creates deterministic ZIP files for one or more plugin products, including
  Free/Pro variants, with a SHA-256 checksum sidecar for each package.
- Runs the same package builder locally or through reusable GitHub Actions; the
  workflow uploads the ZIPs and checksums as CI artifacts.
- Optionally publishes verified packages to a GitHub Release through the
  local GitHub CLI publisher. It verifies the source commit, existing Git tag,
  reproducible package files, and uploaded asset digests before publishing.
- Edits existing Releases with `scripts/edit_release.py`: titles, release notes,
  draft/prerelease/latest status, discussion categories, and release assets.
  Changes default to a dry-run; asset edits respect GitHub immutable-release rules.
- Guides AI coding agents through project setup. The shared skill supports
  Codex, Claude Code, Cursor, GitHub Copilot/VS Code, and Gemini CLI.

The Toolkit is for WordPress plugin projects that need consistent release
archives from an explicit production file allowlist. It does not publish to the
WordPress.org plugin directory. The reusable workflow builds CI artifacts only;
the local publisher creates Releases after the project’s own release checks
pass, while the Release editor updates an existing Release without moving its
tag. Publication requires an existing tag that points to the current source
commit.

## Choose how to use it

### Set it up with an AI coding agent

In an AI coding chat with access to the project files and terminal, ask:

> Activate the ARK Release Toolkit for this project. Read its consumer setup
> guide and project instructions, install and pin the toolkit, add its project
> skill, check the prerequisites, and complete every setup step. Tell me before
> starting that I may need to approve GitHub CLI sign-in once. Pause only while
> I complete that account authorization, then continue and verify the setup.
> Do not publish a Release as part of activation.

The guide covers the supported project skill locations, one-time GitHub
authorization, cloud-agent limitations, and the complete step-by-step flow:
[AI-assisted activation](docs/CONSUMER-SETUP.md#activate-this-toolkit-with-an-ai-chat).

### Configure it manually

1. Copy `examples/manifest.wordpress-plugin.json` into the consuming project,
   or use an existing compatible `package-files.json` manifest.
2. Add one product entry for each installable archive. Set its plugin `slug`
   and explicit production file allowlist. Exclude secrets, local configuration,
   development dependencies, and generated test data.
3. Build and inspect the packages locally:

   ```sh
   python scripts/build.py --manifest package-files.json --source-root . --output-dir dist --all-products
   ```

4. Add a GitHub Actions caller workflow pinned to a reviewed, immutable Toolkit
   reference. See [consumer setup](docs/CONSUMER-SETUP.md) for the manifest,
   workflow, and optional GitHub Release publication requirements.
5. Run the consuming project's checks and release gates before publishing.

## Package safety and reproducibility

- Package contents come from a checked-in JSON allowlist; manifests do not
  accept arbitrary shell commands.
- The builder rejects symlinks and paths outside the plugin source directory,
  and blocks missing or stale entries in managed `assets/`, `includes/`, and
  `languages/` folders.
- ZIP entries use a fixed timestamp, stable ordering, and normalized Unix file
  permissions, so matching source and manifest inputs produce matching ZIPs.
- SHA-256 sidecars are generated for every archive.

## Validation status

The builder accepts the `schema_version: 1` manifest shape used by Media
Auditor. Toolkit CI runs the package-builder regression tests, and the
composite action has been exercised against Media Auditor's production manifest
with byte-for-byte Free/Pro package parity. The reusable workflow and action
can be pinned to commit `252b73b6383061006483fb44da5f842c63e4a7d6`.

## License

MIT. See [LICENSE](LICENSE).
