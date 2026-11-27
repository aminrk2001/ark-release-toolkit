#!/usr/bin/env python3
"""Safely edit an existing GitHub Release without changing its tag or deleting it."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from urllib.parse import quote


REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
TAG_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class EditError(ValueError):
    """An expected validation or GitHub CLI failure."""


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(args, capture_output=True, text=True, check=False)
    except FileNotFoundError as error:
        raise EditError("GitHub CLI (gh) is required and must be on PATH") from error


def checked(args: list[str]) -> str:
    result = run(args)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
        raise EditError(f"Command failed ({args[0]}): {detail}")
    return result.stdout.strip()


def validate_identity(repository: str, tag: str) -> None:
    if not REPOSITORY_PATTERN.fullmatch(repository):
        raise EditError("Repository must use OWNER/REPOSITORY form")
    if not TAG_PATTERN.fullmatch(tag):
        raise EditError("Tag contains unsupported characters")


def read_regular_file(path: Path, label: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise EditError(f"{label} must be an existing regular, non-symlink file: {path}")
    try:
        return path.read_bytes()
    except OSError as error:
        raise EditError(f"Cannot read {label} {path}: {error}") from error


def normalize_notes(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def fetch_release(repository: str, tag: str) -> dict:
    endpoint = f"repos/{repository}/releases/tags/{quote(tag, safe='')}"
    try:
        release = json.loads(checked(["gh", "api", endpoint]))
    except json.JSONDecodeError as error:
        raise EditError("GitHub returned invalid release JSON") from error
    if not isinstance(release, dict) or release.get("tag_name") != tag:
        raise EditError("GitHub did not return the exact release for the requested tag")
    if not isinstance(release.get("id"), int):
        raise EditError("GitHub returned a release without a valid ID")
    if not isinstance(release.get("assets"), list):
        raise EditError("GitHub release response does not contain an asset list")
    return release


def assets_by_name(release: dict) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for asset in release["assets"]:
        if not isinstance(asset, dict):
            raise EditError("GitHub returned an invalid release asset record")
        name = asset.get("name")
        if not isinstance(name, str) or name in result:
            raise EditError("GitHub returned an invalid or duplicate release asset name")
        result[name] = asset
    return result


def parse_asset_labels(values: list[str]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for value in values:
        name, separator, label = value.partition("=")
        if not separator or not name:
            raise EditError("Asset labels must use NAME=LABEL with a non-empty asset name")
        if name in labels:
            raise EditError(f"Asset label was specified more than once: {name}")
        labels[name] = label
    return labels


def validate_uploads(paths: list[Path]) -> list[Path]:
    uploads: list[Path] = []
    names: set[str] = set()
    for path in paths:
        read_regular_file(path, "Asset")
        resolved = path.resolve()
        if resolved.name in names:
            raise EditError(f"Upload asset names must be unique: {resolved.name}")
        names.add(resolved.name)
        uploads.append(resolved)
    return uploads


def build_plan(
    release: dict,
    *,
    title: str | None,
    body: bytes | None,
    prerelease: bool | None,
    draft: bool | None,
    latest: bool | None,
    discussion_category: str | None,
    uploads: list[Path],
    removals: list[str],
    replacements: list[Path],
    labels: dict[str, str],
) -> dict:
    current_assets = assets_by_name(release)
    upload_names = {path.name for path in uploads}
    replacement_names = {path.name for path in replacements}
    removal_names = set(removals)

    if len(removal_names) != len(removals):
        raise EditError("An asset was selected for removal more than once")
    if len(replacement_names) != len(replacements):
        raise EditError("Replacement asset names must be unique")
    if upload_names & replacement_names:
        raise EditError("The same file cannot be both added and used as a replacement")
    if removal_names & replacement_names:
        raise EditError("Use --replace-asset instead of combining replacement and removal")
    if upload_names & removal_names:
        raise EditError("Adding and removing an asset with the same name is ambiguous")

    missing_removals = sorted(removal_names - set(current_assets))
    if missing_removals:
        raise EditError("Cannot remove assets that are not attached: " + ", ".join(missing_removals))
    missing_replacements = sorted(replacement_names - set(current_assets))
    if missing_replacements:
        raise EditError("Cannot replace assets that are not attached: " + ", ".join(missing_replacements))
    duplicate_uploads = sorted(upload_names & set(current_assets))
    if duplicate_uploads:
        raise EditError("Assets already exist; use --replace-asset explicitly: " + ", ".join(duplicate_uploads))
    unknown_labels = sorted(set(labels) - set(current_assets))
    if unknown_labels:
        raise EditError("Cannot edit labels for assets that are not attached: " + ", ".join(unknown_labels))

    has_asset_changes = bool(uploads or removals or replacements or labels)
    if has_asset_changes and release.get("immutable") is True:
        raise EditError("This Release is immutable; GitHub does not allow changes to its assets")
    if has_asset_changes and not isinstance(release.get("immutable"), bool):
        raise EditError("GitHub did not report whether this Release is immutable; refusing asset changes")

    wanted_draft = release.get("draft") if draft is None else draft
    wanted_prerelease = release.get("prerelease") if prerelease is None else prerelease
    if latest is True and (wanted_draft or wanted_prerelease):
        raise EditError("A draft or prerelease cannot be marked as the latest stable Release")

    metadata: dict[str, object] = {}
    if title is not None:
        if not title.strip():
            raise EditError("Release title must not be empty")
        if title != release.get("name"):
            metadata["title"] = title
    if body is not None and normalize_notes(body.decode("utf-8")) != normalize_notes(release.get("body") or ""):
        metadata["notes"] = body.decode("utf-8")
    if prerelease is not None and prerelease != release.get("prerelease"):
        metadata["prerelease"] = prerelease
    if draft is not None and draft != release.get("draft"):
        metadata["draft"] = draft
    if latest is not None:
        metadata["latest"] = latest
    if discussion_category is not None:
        if not discussion_category.strip():
            raise EditError("Discussion category must not be empty")
        metadata["discussion-category"] = discussion_category

    return {
        "metadata": metadata,
        "uploads": uploads,
        "removals": sorted(removal_names),
        "replacements": replacements,
        "labels": labels,
        "current_assets": current_assets,
    }


def digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_asset(release: dict, name: str, path: Path) -> dict:
    asset = assets_by_name(release).get(name)
    if not asset or asset.get("state") != "uploaded":
        raise EditError(f"GitHub did not confirm the uploaded asset: {name}")
    if asset.get("size") != path.stat().st_size:
        raise EditError(f"Uploaded asset size does not match: {name}")
    if asset.get("digest") != f"sha256:{digest_file(path)}":
        raise EditError(f"Uploaded asset digest does not match: {name}")
    return asset


def upload_asset(repository: str, tag: str, path: Path, upload_name: str | None = None) -> None:
    if upload_name is not None:
        staged = path.parent / upload_name
        try:
            with path.open("rb") as source, staged.open("xb") as output:
                shutil.copyfileobj(source, output)
            checked(["gh", "release", "upload", tag, str(staged), "--repo", repository])
        finally:
            staged.unlink(missing_ok=True)
    else:
        checked(["gh", "release", "upload", tag, str(path), "--repo", repository])


def apply_metadata(repository: str, tag: str, metadata: dict[str, object], notes_file: Path | None) -> None:
    if not metadata:
        return
    command = ["gh", "release", "edit", tag, "--repo", repository, "--verify-tag"]
    if "title" in metadata:
        command.extend(["--title", str(metadata["title"])])
    if notes_file is not None:
        command.extend(["--notes-file", str(notes_file.resolve())])
    for field in ("prerelease", "draft", "latest"):
        if field in metadata:
            command.append(f"--{field}={'true' if metadata[field] else 'false'}")
    if "discussion-category" in metadata:
        command.extend(["--discussion-category", str(metadata["discussion-category"])])
    if "notes" in metadata and notes_file is None:
        raise EditError("Internal error: changed notes do not have a notes file")
    checked(command)


def apply_replacement(repository: str, tag: str, path: Path) -> None:
    suffix = path.suffix
    temporary_name = f"arkrt-replacement-{uuid.uuid4().hex[:16]}{suffix}"
    upload_asset(repository, tag, path, temporary_name)
    release = fetch_release(repository, tag)
    temporary_asset = verify_asset(release, temporary_name, path)
    try:
        checked(["gh", "release", "delete-asset", tag, path.name, "--repo", repository, "--yes"])
    except EditError as error:
        raise EditError(f"Replacement upload is attached as {temporary_name}; old asset was preserved: {error}") from error
    asset_id = temporary_asset.get("id")
    if not isinstance(asset_id, int):
        raise EditError("GitHub did not return the staged replacement asset ID")
    try:
        checked(["gh", "api", "--method", "PATCH", f"repos/{repository}/releases/assets/{asset_id}",
                 "-f", f"name={path.name}"])
    except EditError as error:
        raise EditError(f"Old asset was removed; replacement remains attached as {temporary_name}: {error}") from error


def verify_metadata(repository: str, tag: str, release: dict, metadata: dict[str, object], body: bytes | None) -> None:
    checks = {
        "title": ("name", metadata.get("title")),
        "prerelease": ("prerelease", metadata.get("prerelease")),
        "draft": ("draft", metadata.get("draft")),
    }
    for requested, (remote_field, expected) in checks.items():
        if requested in metadata and release.get(remote_field) != expected:
            raise EditError(f"GitHub did not confirm the requested {requested} value")
    if (body is not None and "notes" in metadata
            and normalize_notes(release.get("body", "")) != normalize_notes(body.decode("utf-8"))):
        raise EditError("GitHub did not confirm the release notes")
    if metadata.get("latest") is not None:
        latest_result = run(["gh", "api", f"repos/{repository}/releases/latest"])
        if latest_result.returncode:
            if metadata["latest"]:
                detail = latest_result.stderr.strip() or "GitHub returned no latest release"
                raise EditError(f"Could not verify Latest Release: {detail}")
            if "404" not in latest_result.stderr and "Not Found" not in latest_result.stderr:
                detail = latest_result.stderr.strip() or f"exit code {latest_result.returncode}"
                raise EditError(f"Could not verify Latest Release: {detail}")
        else:
            try:
                latest_release = json.loads(latest_result.stdout)
            except json.JSONDecodeError as error:
                raise EditError("GitHub returned invalid JSON for the Latest Release") from error
            is_latest = isinstance(latest_release, dict) and latest_release.get("tag_name") == tag
            if is_latest != metadata["latest"]:
                raise EditError("GitHub Latest selection does not match the requested value")


def edit_release(
    repository: str,
    tag: str,
    *,
    title: str | None = None,
    notes_file: Path | None = None,
    prerelease: bool | None = None,
    draft: bool | None = None,
    latest: bool | None = None,
    discussion_category: str | None = None,
    asset_paths: list[Path] | None = None,
    remove_assets: list[str] | None = None,
    replace_assets: list[Path] | None = None,
    asset_labels: list[str] | None = None,
    apply: bool = False,
) -> str:
    validate_identity(repository, tag)
    assets = validate_uploads(asset_paths or [])
    replacements = validate_uploads(replace_assets or [])
    body = read_regular_file(notes_file, "Release notes") if notes_file is not None else None
    try:
        body_text = body.decode("utf-8") if body is not None else None
    except UnicodeError as error:
        raise EditError("Release notes must be UTF-8 text") from error
    labels = parse_asset_labels(asset_labels or [])
    removals = remove_assets or []
    if any(not item or Path(item).name != item for item in removals):
        raise EditError("Asset removals must use exact asset names without directory paths")
    if not any((title is not None, notes_file is not None, prerelease is not None, draft is not None,
                latest is not None, discussion_category is not None, assets, removals, replacements, labels)):
        raise EditError("Specify at least one Release field or asset change")

    release = fetch_release(repository, tag)
    plan = build_plan(release, title=title, body=body, prerelease=prerelease, draft=draft, latest=latest,
                      discussion_category=discussion_category, uploads=assets, removals=removals,
                      replacements=replacements, labels=labels)
    url = release.get("html_url")
    print(f"Release: {url or tag}")
    print(f"Mode: {'APPLY' if apply else 'DRY RUN'}")
    if plan["metadata"]:
        safe_metadata = {key: (f"<UTF-8 notes: {len(body_text or '')} characters>" if key == "notes" else value)
                         for key, value in plan["metadata"].items()}
        print("Metadata changes: " + json.dumps(safe_metadata, ensure_ascii=False, sort_keys=True))
    if plan["uploads"]:
        print("Assets to add: " + ", ".join(f"{path.name} ({path.stat().st_size} bytes)" for path in plan["uploads"]))
    if plan["replacements"]:
        print("Assets to replace: " + ", ".join(path.name for path in plan["replacements"]))
    if plan["removals"]:
        print("Assets to remove: " + ", ".join(plan["removals"]))
    if plan["labels"]:
        print("Asset labels to set: " + ", ".join(sorted(plan["labels"])))
    if not (plan["metadata"] or plan["uploads"] or plan["replacements"] or plan["removals"] or plan["labels"]):
        print("No changes are needed.")
        return str(url or tag)
    if not apply:
        print("No remote changes made. Re-run with --apply to apply this exact plan.")
        return str(url or tag)

    for path in plan["uploads"]:
        upload_asset(repository, tag, path)
        verify_asset(fetch_release(repository, tag), path.name, path)
    for path in plan["replacements"]:
        apply_replacement(repository, tag, path)
        verify_asset(fetch_release(repository, tag), path.name, path)
    for name in plan["removals"]:
        checked(["gh", "release", "delete-asset", tag, name, "--repo", repository, "--yes"])
        if name in assets_by_name(fetch_release(repository, tag)):
            raise EditError(f"GitHub still lists the removed asset: {name}")
    for name, label in plan["labels"].items():
        current_asset = assets_by_name(fetch_release(repository, tag)).get(name, {})
        asset_id = current_asset.get("id")
        if not isinstance(asset_id, int):
            raise EditError(f"GitHub did not return an asset ID for {name}")
        checked(["gh", "api", "--method", "PATCH", f"repos/{repository}/releases/assets/{asset_id}", "-f", f"label={label}"])
    apply_metadata(repository, tag, plan["metadata"], notes_file)

    updated = fetch_release(repository, tag)
    verify_metadata(repository, tag, updated, plan["metadata"], body)
    updated_assets = assets_by_name(updated)
    for path in [*plan["uploads"], *plan["replacements"]]:
        verify_asset(updated, path.name, path)
    for name in plan["removals"]:
        if name in updated_assets:
            raise EditError(f"Removed asset is still present after the update: {name}")
    for name, label in plan["labels"].items():
        if (updated_assets.get(name, {}).get("label") or "") != label:
            raise EditError(f"GitHub did not confirm the requested asset label: {name}")
    if not isinstance(updated.get("html_url"), str):
        raise EditError("GitHub did not return the edited Release URL")
    print(f"Updated Release: {updated['html_url']}")
    return updated["html_url"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True, help="GitHub OWNER/REPOSITORY")
    parser.add_argument("--tag", required=True, help="Existing Release tag; this tool does not move tags")
    parser.add_argument("--title", help="Set the Release title")
    parser.add_argument("--notes-file", type=Path, help="Replace Release notes with this UTF-8 file")
    parser.add_argument("--prerelease", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--draft", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--latest", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--discussion-category", help="Start a discussion in an existing category")
    parser.add_argument("--asset", action="append", type=Path, default=[], help="Add an asset; repeat as needed")
    parser.add_argument("--remove-asset", action="append", default=[], help="Remove an exact attached asset name")
    parser.add_argument("--replace-asset", action="append", type=Path, default=[],
                        help="Safely replace the asset with the same filename")
    parser.add_argument("--asset-label", action="append", default=[], metavar="NAME=LABEL",
                        help="Set an attached asset's display label; repeat as needed")
    parser.add_argument("--apply", action="store_true", help="Apply changes; without this flag, only show a dry-run plan")
    args = parser.parse_args()
    try:
        edit_release(args.repository, args.tag, title=args.title, notes_file=args.notes_file,
                     prerelease=args.prerelease, draft=args.draft, latest=args.latest,
                     discussion_category=args.discussion_category, asset_paths=args.asset,
                     remove_assets=args.remove_asset, replace_assets=args.replace_asset,
                     asset_labels=args.asset_label, apply=args.apply)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"release-toolkit: error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

