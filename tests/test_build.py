from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import unittest
import uuid
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build.py"


class PackageBuilderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = ROOT / ".test-runtime" / uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.plugin = self.root / "example-plugin"
        for directory in ("assets", "includes", "languages"):
            (self.plugin / directory).mkdir(parents=True, exist_ok=True)
        files = {
            "example-plugin.php": "<?php\n/*\n * Version: 2.3.4\n */\n",
            "assets/admin.js": "window.example = true;\n",
            "includes/class-example.php": "<?php\n",
            "languages/example-plugin.pot": "msgid \"\"\n",
            "readme.txt": "Stable plugin readme\n",
            "USER-GUIDE.en.md": "# User guide\n",
        }
        for name, content in files.items():
            path = self.plugin / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        self.manifest = self.root / "package-files.json"
        self.manifest.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "products": {
                        "free": {
                            "slug": "example-plugin",
                            "files": sorted(files),
                        }
                    },
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.root)

    def run_builder(self, output: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--manifest",
                str(self.manifest),
                "--source-root",
                str(self.root),
                "--output-dir",
                str(output),
                "--all-products",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_build_is_reproducible_and_remaps_markdown(self) -> None:
        first_dir = self.root / "first"
        second_dir = self.root / "second"
        first = self.run_builder(first_dir)
        second = self.run_builder(second_dir)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        archive = first_dir / "example-plugin-v2.3.4.zip"
        repeated = second_dir / archive.name
        self.assertEqual(archive.read_bytes(), repeated.read_bytes())
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        self.assertEqual((first_dir / (archive.name + ".sha256")).read_text(encoding="ascii"), f"{digest}  {archive.name}\n")
        with zipfile.ZipFile(archive) as package:
            self.assertIsNone(package.testzip())
            self.assertIn("example-plugin/docs/USER-GUIDE.en.md", package.namelist())
            self.assertEqual(package.namelist(), sorted(package.namelist()))
            self.assertTrue(all(item.date_time == (1980, 1, 1, 0, 0, 0) for item in package.infolist()))
            self.assertTrue(all((item.external_attr >> 16) == 0o100644 for item in package.infolist()))

    def test_unlisted_managed_file_blocks_package(self) -> None:
        (self.plugin / "assets" / "unlisted.js").write_text("// new source\n", encoding="utf-8")
        result = self.run_builder(self.root / "blocked")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unlisted production files", result.stderr)
        self.assertFalse((self.root / "blocked" / "example-plugin-v2.3.4.zip").exists())

    def test_unsafe_allowlist_path_is_rejected(self) -> None:
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        data["products"]["free"]["files"].append("../outside.php")
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        result = self.run_builder(self.root / "blocked")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unsafe package path", result.stderr)


if __name__ == "__main__":
    unittest.main()
