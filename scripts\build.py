#!/usr/bin/env python3
"""Build deterministic WordPress plugin ZIPs from an explicit JSON allowlist."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath


ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
PLUGIN_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
VERSION_PATTERN = re.compile(r"^ \* Version: ([0-9]+(?:\.[0-9]+)*)$", re.MULTILINE)
MANAGED_DIRECTORIES = {"assets", "includes", "languages"}


def fail(message: str) -> "NoReturn":
    raise ValueError(message)


def read_manifest(path: Path) -> dict:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"Cannot read manifest {path}: {error}")
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        fail("Manifest must be an object with schema_version: 1")
    products = manifest.get("products")
    if not isinstance(products, dict) or not products:
        fail("Manifest products must be a non-empty object")
    for product_id, product in products.items():
        if not isinstance(product_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", product_id):
            fail(f"Invalid product id: {product_id!r}")
        if not isinstance(product, dict):
            fail(f"Product {product_id} must be an object")
        slug = product.get("slug")
        files = product.get("files")
        if not isinstance(slug, str) or not PLUGIN_SLUG.fullmatch(slug):
            fail(f"Product {product_id} has an invalid plugin slug")
        if not isinstance(files, list) or not files or any(not isinstance(item, str) or not item for item in files):
            fail(f"Product {product_id} requires a non-empty files allowlist")
        if len(files) != len(set(files)):
            fail(f"Product {product_id} file allowlist contains duplicates")
    return manifest


def validate_product(source_root: Path, product_id: str, product: dict) -> tuple[str, list[tuple[str, Path]], str]:
    slug = product["slug"]
    plugin_candidate = source_root / slug
    if plugin_candidate.is_symlink():
        fail(f"Plugin source directory must not be a symlink: {plugin_candidate}")
    plugin_root = plugin_candidate.resolve()
    if not plugin_root.is_dir() or not plugin_root.is_relative_to(source_root.resolve()):
        fail(f"Invalid source directory for {product_id}: {plugin_root}")

    files: list[tuple[str, Path]] = []
    for raw_name in product["files"]:
        relative = PurePosixPath(raw_name.replace("\\", "/"))
        if relative.is_absolute() or not relative.parts or relative.parts[0].endswith(":") or ".." in relative.parts or "." in relative.parts:
            fail(f"Unsafe package path: {raw_name!r}")
        source = plugin_root.joinpath(*relative.parts)
        if source.is_symlink() or not source.is_file():
            fail(f"Manifest source is missing or not a regular file: {source}")
        if not source.resolve().is_relative_to(plugin_root):
            fail(f"Manifest source escapes plugin directory: {source}")
        archive_name = f"{slug}/docs/{relative.as_posix()}" if relative.suffix.lower() == ".md" else f"{slug}/{relative.as_posix()}"
        files.append((archive_name, source))

    declared_managed = {
        relative
        for relative in product["files"]
        if PurePosixPath(relative.replace("\\", "/")).parts[0] in MANAGED_DIRECTORIES
    }
    actual_managed: set[str] = set()
    for directory in MANAGED_DIRECTORIES:
        base = plugin_root / directory
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_symlink():
                fail(f"Symlink is not allowed in managed package directory: {path}")
            if path.is_file():
                actual_managed.add(path.relative_to(plugin_root).as_posix())
    if actual_managed != declared_managed:
        missing = sorted(actual_managed - declared_managed)
        stale = sorted(declared_managed - actual_managed)
        details = []
        if missing:
            details.append("unlisted production files: " + ", ".join(missing))
        if stale:
            details.append("missing allowlist files: " + ", ".join(stale))
        fail(f"{slug}: package allowlist is stale ({'; '.join(details)})")

    files.sort(key=lambda item: item[0])
    archive_names = [name for name, _ in files]
    if len(archive_names) != len(set(archive_names)):
        fail(f"{slug}: duplicate archive paths")

    header_path = plugin_root / f"{slug}.php"
    try:
        header = header_path.read_text(encoding="utf-8-sig")
    except OSError as error:
        fail(f"Cannot read plugin version header {header_path}: {error}")
    version_match = VERSION_PATTERN.search(header)
    if version_match is None:
        fail(f"Could not read a numeric version from {header_path}")
    return slug, files, version_match.group(1)


def write_archive(path: Path, files: list[tuple[str, Path]]) -> str:
    with zipfile.ZipFile(
        path,
        "x",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        strict_timestamps=True,
    ) as archive:
        for name, source in files:
            info = zipfile.ZipInfo(name, date_time=ZIP_TIMESTAMP)
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.flag_bits |= 0x800
            archive.writestr(info, source.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            fail(f"Generated ZIP failed its CRC check: {path}")
        if archive.namelist() != [name for name, _ in files]:
            fail(f"Generated ZIP contents do not match the allowlist: {path}")
        for name, source in files:
            if archive.read(name) != source.read_bytes():
                fail(f"Packaged file differs from source: {name}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(source_root: Path, output_dir: Path, products: dict[str, dict]) -> list[tuple[Path, Path, str, str]]:
    validated = [(product_id, *validate_product(source_root, product_id, product)) for product_id, product in products.items()]
    destinations: list[tuple[Path, Path, str, str]] = []
    for _, slug, files, version in validated:
        archive_path = output_dir / f"{slug}-v{version}.zip"
        sidecar_path = Path(str(archive_path) + ".sha256")
        if archive_path.exists() or sidecar_path.exists():
            fail(f"Refusing to overwrite package output: {archive_path}")
        destinations.append((archive_path, sidecar_path, slug, version))

    created: list[Path] = []
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        results = []
        for (product_id, slug, files, version), (archive_path, sidecar_path, _, _) in zip(validated, destinations):
            created.append(archive_path)
            digest = write_archive(archive_path, files)
            created.append(sidecar_path)
            with sidecar_path.open("x", encoding="ascii", newline="\n") as sidecar:
                sidecar.write(f"{digest}  {archive_path.name}\n")
            results.append((archive_path, sidecar_path, digest, product_id))
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--source-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", required=True, type=Path)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--product", action="append", help="Product ID to build; may be repeated")
    selection.add_argument("--all-products", action="store_true")
    args = parser.parse_args()

    try:
        manifest = read_manifest(args.manifest.resolve())
        products = manifest["products"]
        selected_ids = list(products) if args.all_products else args.product
        unknown = sorted(set(selected_ids) - set(products))
        if unknown:
            fail("Unknown product ID(s): " + ", ".join(unknown))
        source_root = args.source_root.resolve()
        output_dir = args.output_dir if args.output_dir.is_absolute() else Path.cwd() / args.output_dir
        results = build(source_root, output_dir.resolve(), {key: products[key] for key in selected_ids})
        for archive, sidecar, digest, product_id in results:
            print(f"{product_id}\t{archive}\t{sidecar}\t{digest}")
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"release-toolkit: error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
