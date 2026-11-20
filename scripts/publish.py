#!/usr/bin/env python3
"""Publish verified package files to an existing GitHub tag via gh."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from urllib.parse import quote

import build as package_builder


REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
TAG_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class PublishError(ValueError):
    """An expected validation or GitHub CLI failure."""


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(args, capture_output=True, text=True, check=False)
    except FileNotFoundError as error:
        raise PublishError("GitHub CLI (gh) is required and must be on PATH") from error


def checked(args: list[str]) -> str:
    result = run(args)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
        raise PublishError(f"Command failed ({args[0]}): {detail}")
    return result.stdout.strip()


def validate_identity(repository: str, tag: str) -> None:
    if not REPOSITORY_PATTERN.fullmatch(repository):
        raise PublishError("Repository must use OWNER/REPOSITORY form")
    if not TAG_PATTERN.fullmatch(tag):
        raise PublishError("Tag contains unsupported characters")


def remote_tag_commit(repository: str, tag: str) -> str:
    endpoint = f"repos/{repository}/git/ref/tags/{quote(tag, safe='')}"
    response = json.loads(checked(["gh", "api", endpoint]))
    if not isinstance(response, dict):
        raise PublishError("GitHub returned an invalid tag reference")
    obj = response.get("object", {})
    seen: set[str] = set()
    for _ in range(8):
        sha, kind = obj.get("sha"), obj.get("type")
        if not isinstance(sha, str) or not isinstance(kind, str) or sha in seen:
            raise PublishError("GitHub returned an invalid or cyclic tag target")
        seen.add(sha)
        if kind == "commit":
            if not SHA_PATTERN.fullmatch(sha):
                raise PublishError("GitHub returned an invalid commit SHA for the tag")
            return sha
        if kind != "tag":
            raise PublishError("The GitHub tag does not resolve to a commit")
        tag_data = json.loads(checked(["gh", "api", f"repos/{repository}/git/tags/{sha}"]))
        if not isinstance(tag_data, dict):
            raise PublishError("GitHub returned an invalid annotated tag")
        obj = tag_data.get("object", {})
    raise PublishError("The annotated tag exceeds the supported nesting limit")


def local_head() -> str:
    sha = checked(["git", "rev-parse", "HEAD"])
    if not SHA_PATTERN.fullmatch(sha):
        raise PublishError("Could not determine the current source commit")
    return sha


def validate_assets(asset_args: list[Path]) -> list[Path]:
    if not asset_args:
        raise PublishError("At least one --asset is required")
    assets: list[Path] = []
    names: set[str] = set()
    for requested in asset_args:
        if requested.is_symlink() or not requested.is_file():
            raise PublishError(f"Asset must be a regular, non-symlink file: {requested}")
        asset = requested.resolve()
        if asset.name in names:
            raise PublishError(f"Asset names must be unique: {asset.name}")
        names.add(asset.name)
        assets.append(asset)

    asset_by_name = {asset.name: asset for asset in assets}
    for asset in assets:
        if asset.suffix.lower() == ".zip":
            sidecar_name = asset.name + ".sha256"
            sidecar = asset_by_name.get(sidecar_name)
            if sidecar is None:
                raise PublishError(f"Missing checksum sidecar asset: {sidecar_name}")
            digest = hashlib.sha256(asset.read_bytes()).hexdigest()
            expected = f"{digest}  {asset.name}"
            try:
                actual = sidecar.read_text(encoding="ascii").strip()
            except (OSError, UnicodeError) as error:
                raise PublishError(f"Cannot read checksum sidecar {sidecar.name}: {error}") from error
            if actual != expected:
                raise PublishError(f"Checksum sidecar does not match {asset.name}")
    return assets


def verify_package_sources(assets: list[Path], manifest_path: Path, source_root: Path) -> None:
    archives = [asset for asset in assets if asset.suffix.lower() == ".zip"]
    if not archives:
        raise PublishError("At least one package ZIP is required")
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise PublishError("Package manifest must be an existing regular, non-symlink file")
    if source_root.is_symlink() or not source_root.is_dir():
        raise PublishError("Source root must be an existing directory")

    manifest = package_builder.read_manifest(manifest_path.resolve())
    repository_root = Path(checked(["git", "rev-parse", "--show-toplevel"])).resolve()

    def verify_committed_file(path: Path) -> None:
        try:
            relative = path.resolve().relative_to(repository_root).as_posix()
        except ValueError as error:
            raise PublishError(f"Release input is outside the current Git repository: {path}") from error
        committed = checked(["git", "rev-parse", f"HEAD:{relative}"])
        working = checked(["git", "hash-object", "--path", relative, str(path.resolve())])
        if committed != working:
            raise PublishError(f"Release input differs from the current source commit: {relative}")

    verify_committed_file(manifest_path)
    for product_id, product in manifest["products"].items():
        _slug, files, _version = package_builder.validate_product(source_root.resolve(), product_id, product)
        for _archive_name, source in files:
            verify_committed_file(source)

    output_dir = source_root.resolve() / f".ark-release-verify-{uuid.uuid4().hex}"
    try:
        output_dir.mkdir()
        generated = package_builder.build(source_root.resolve(), output_dir, manifest["products"])
        generated_by_name = {archive.name: (archive, sidecar) for archive, sidecar, _digest, _product_id in generated}
        for archive in archives:
            built = generated_by_name.get(archive.name)
            if built is None or archive.read_bytes() != built[0].read_bytes():
                raise PublishError(f"Package does not match the current source and manifest: {archive.name}")
            sidecar = next((item for item in assets if item.name == archive.name + ".sha256"), None)
            if sidecar is None or sidecar.read_bytes() != built[1].read_bytes():
                raise PublishError(f"Package checksum sidecar does not match the current build: {archive.name}.sha256")
    except PublishError:
        raise
    except (OSError, ValueError) as error:
        raise PublishError(f"Could not reproduce the package from the current source: {error}") from error
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)


def fetch_release(repository: str, tag: str) -> dict:
    endpoint = f"repos/{repository}/releases/tags/{quote(tag, safe='')}"
    release = json.loads(checked(["gh", "api", endpoint]))
    if not isinstance(release, dict):
        raise PublishError("GitHub returned an invalid release")
    return release


def verify_release_assets(release: dict, assets: list[Path], *, draft: bool, prerelease: bool) -> None:
    if release.get("draft") is not draft or release.get("prerelease") is not prerelease:
        raise PublishError("GitHub release state does not match the requested publication state")
    expected = {asset.name: hashlib.sha256(asset.read_bytes()).hexdigest() for asset in assets}
    actual_assets = release.get("assets")
    if not isinstance(actual_assets, list):
        raise PublishError("GitHub release response does not contain an asset list")
    actual: dict[str, dict] = {}
    for asset in actual_assets:
        if not isinstance(asset, dict):
            raise PublishError("GitHub release contains an invalid asset record")
        name = asset.get("name")
        if not isinstance(name, str) or name in actual:
            raise PublishError("GitHub release contains an invalid or duplicate asset name")
        actual[name] = asset
    if set(actual) != set(expected):
        raise PublishError("Uploaded release assets do not exactly match the selected files")
    for name, digest in expected.items():
        remote = actual[name]
        if remote.get("state") != "uploaded" or remote.get("size") != next(a.stat().st_size for a in assets if a.name == name):
            raise PublishError(f"GitHub has not confirmed the uploaded asset: {name}")
        if remote.get("digest") != f"sha256:{digest}":
            raise PublishError(f"GitHub asset digest does not match the local file: {name}")


def publish(repository: str, tag: str, title: str, notes_file: Path, asset_args: list[Path],
            manifest_path: Path, source_root: Path, prerelease: bool = False) -> str:
    validate_identity(repository, tag)
    if not title.strip():
        raise PublishError("Release title must not be empty")
    if notes_file.is_symlink() or not notes_file.is_file():
        raise PublishError("Release notes must be an existing regular, non-symlink file")
    assets = validate_assets(asset_args)
    verify_package_sources(assets, manifest_path, source_root)

    expected_commit = local_head()
    tagged_commit = remote_tag_commit(repository, tag)
    if tagged_commit != expected_commit:
        raise PublishError(f"Remote tag {tag} points to {tagged_commit}, not the current source commit {expected_commit}")

    command = ["gh", "release", "create", tag, *(str(asset) for asset in assets), "--repo", repository,
               "--title", title, "--notes-file", str(notes_file), "--draft", "--verify-tag"]
    if prerelease:
        command.append("--prerelease")
    checked(command)

    release = fetch_release(repository, tag)
    verify_release_assets(release, assets, draft=True, prerelease=prerelease)
    release_id = release.get("id")
    if not isinstance(release_id, int):
        raise PublishError("GitHub did not return the draft release identity")
    checked(["gh", "api", "--method", "PATCH", f"repos/{repository}/releases/{release_id}", "-F", "draft=false"])

    published = fetch_release(repository, tag)
    verify_release_assets(published, assets, draft=False, prerelease=prerelease)
    url = published.get("html_url")
    if not isinstance(url, str):
        raise PublishError("GitHub did not return the published release URL")
    return url


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True, help="GitHub OWNER/REPOSITORY")
    parser.add_argument("--tag", required=True, help="Existing remote tag that points to the current HEAD")
    parser.add_argument("--title", required=True)
    parser.add_argument("--notes-file", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path, help="The checked-in package allowlist used to build the ZIPs")
    parser.add_argument("--source-root", type=Path, default=Path.cwd(), help="Directory containing plugin source directories (default: current directory)")
    parser.add_argument("--asset", required=True, action="append", type=Path, help="Release asset; provide ZIP and matching .sha256 sidecar")
    parser.add_argument("--prerelease", action="store_true")
    args = parser.parse_args()
    try:
        url = publish(args.repository, args.tag, args.title, args.notes_file, args.asset,
                      args.manifest, args.source_root, args.prerelease)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"release-toolkit: error: {error}", file=sys.stderr)
        return 2
    print(f"Published release: {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

