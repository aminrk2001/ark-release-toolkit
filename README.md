# ARK Release Toolkit

Reusable GitHub Actions and a manifest-driven package builder for WordPress
plugin projects that need repeatable Free/Pro or single-product archives. This
repository is separate from product repositories; projects opt in by supplying
their package allowlist and a small workflow caller.

## Status

Initial implementation. The builder accepts the `schema_version: 1` product
manifest shape used by Media Auditor, emits normalized plugin ZIPs and SHA-256
sidecars, and rejects stale allowlists. Reusable workflow CI and fixture-based
verification are still required before creating a stable toolkit tag.

## Quick start

1. Copy `examples/manifest.wordpress-plugin.json` into the consuming project,
   or use its existing compatible `package-files.json` manifest.
2. Define one product entry for each installable ZIP. Set the plugin `slug` and
   explicit production file allowlist. Do not include secrets, local
   configuration, development dependencies, or generated test data.
3. Run `python scripts/build.py --manifest package-files.json --source-root . --output-dir dist --all-products`
   locally and inspect the archives and `.sha256` sidecars.
4. Add a workflow that calls the reusable workflow and pins both workflow and
   implementation to the same reviewed toolkit tag or commit.
5. Review the generated files and CI evidence before enabling stable Releases.

See `docs/CONSUMER-SETUP.md` for project-side requirements and security notes.

## Design rules

- Product selection and package files stay in a checked-in JSON manifest; no
  arbitrary shell commands are accepted from manifests.
- Packaging uses explicit file allowlists, rejects symlinks and paths outside
  the plugin root, and fails when managed `assets`, `includes`, or `languages`
  files are missing from or stale in the allowlist.
- ZIP entries use a fixed timestamp, stable ordering, and normalized Unix file
  permissions. SHA-256 sidecars are generated for every archive.
- The reusable workflow builds and uploads CI artifacts only. Each consuming
  project keeps its own tests and release eligibility gates; the toolkit does
  not infer stable status or publish a GitHub Release.

## License

MIT. See `LICENSE`.

