from __future__ import annotations

import hashlib
import json
import sys
import shutil
import unittest
import uuid
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from edit_release import EditError, edit_release


class ReleaseEditorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1] / ".test-runtime" / f"release-editor-{uuid.uuid4().hex}"
        self.root.mkdir(parents=True)
        self.notes = self.root / "notes.md"
        self.notes.write_text("Corrected notes\n", encoding="utf-8")
        self.asset = self.root / "installer.zip"
        self.asset.write_bytes(b"new package bytes")
        self.release = {
            "id": 23,
            "tag_name": "v1.2.3",
            "name": "Version 1.2.3",
            "body": "Old notes\n",
            "draft": False,
            "prerelease": False,
            "immutable": False,
            "html_url": "https://github.com/example/plugin/releases/tag/v1.2.3",
            "assets": [],
        }
        self.calls: list[list[str]] = []

    def tearDown(self) -> None:
        shutil.rmtree(self.root)

    def gh(self, args: list[str]) -> str:
        self.calls.append(args)
        if args[:2] == ["gh", "api"] and "--method" not in args:
            if args[-1] == "repos/example/plugin/releases/latest":
                if self.release.get("latest"):
                    return json.dumps(self.release)
                return json.dumps({"tag_name": "v1.0.0"})
            if args[-1] == "repos/example/plugin/releases/tags/v1.2.3":
                return json.dumps(self.release)
        if args[:3] == ["gh", "release", "edit"]:
            for index, value in enumerate(args):
                if value == "--title":
                    self.release["name"] = args[index + 1]
                elif value == "--notes-file":
                    self.release["body"] = Path(args[index + 1]).read_text(encoding="utf-8")
                elif value.startswith("--prerelease="):
                    self.release["prerelease"] = value.endswith("=true")
                elif value.startswith("--draft="):
                    self.release["draft"] = value.endswith("=true")
                elif value.startswith("--latest="):
                    self.release["latest"] = value.endswith("=true")
            return ""
        if args[:3] == ["gh", "release", "upload"]:
            path = Path(args[4])
            content = path.read_bytes()
            self.release["assets"].append({
                "id": len(self.release["assets"]) + 100,
                "name": path.name,
                "state": "uploaded",
                "size": len(content),
                "digest": "sha256:" + hashlib.sha256(content).hexdigest(),
                "label": None,
            })
            return ""
        if args[:3] == ["gh", "release", "delete-asset"]:
            self.release["assets"] = [asset for asset in self.release["assets"] if asset["name"] != args[4]]
            return ""
        if args[:3] == ["gh", "api", "--method"] and args[3] == "PATCH":
            asset = next(asset for asset in self.release["assets"] if str(asset["id"]) == args[4].rsplit("/", 1)[-1])
            field, value = args[6].split("=", 1) if args[6] != "-f" else args[7].split("=", 1)
            asset[field] = value
            return "{}"
        self.fail(f"Unexpected GitHub command: {args}")

    def checked_side_effect(self, args: list[str]) -> str:
        return self.gh(args)

    def run_side_effect(self, args: list[str]) -> CompletedProcess[str]:
        if args[:2] == ["gh", "api"] and args[-1] == "repos/example/plugin/releases/latest":
            if self.release.get("latest"):
                return CompletedProcess(args, 0, json.dumps(self.release), "")
            return CompletedProcess(args, 0, json.dumps({"tag_name": "v1.0.0"}), "")
        self.fail(f"Unexpected GitHub command: {args}")

    def run_edit(self, **kwargs) -> str:
        with patch("edit_release.checked", side_effect=self.checked_side_effect):
            with patch("edit_release.run", side_effect=self.run_side_effect):
                return edit_release("example/plugin", "v1.2.3", **kwargs)

    def test_default_is_dry_run_and_does_not_print_release_notes(self) -> None:
        with patch("edit_release.checked", side_effect=self.checked_side_effect), patch("edit_release.run", side_effect=self.run_side_effect):
            result = edit_release("example/plugin", "v1.2.3", notes_file=self.notes)
        self.assertIn("releases/tag/v1.2.3", result)
        self.assertFalse(any(call[:3] == ["gh", "release", "edit"] for call in self.calls))
        self.assertFalse(any(call[:3] == ["gh", "release", "upload"] for call in self.calls))

    def test_metadata_edit_is_applied_and_verified(self) -> None:
        self.run_edit(title="Corrected title", notes_file=self.notes, prerelease=True, apply=True)
        self.assertEqual(self.release["name"], "Corrected title")
        self.assertEqual(self.release["body"], "Corrected notes\n")
        self.assertTrue(self.release["prerelease"])
        self.assertTrue(any(call[:3] == ["gh", "release", "edit"] for call in self.calls))

    def test_asset_addition_is_verified_by_digest(self) -> None:
        self.run_edit(asset_paths=[self.asset], apply=True)
        self.assertEqual([item["name"] for item in self.release["assets"]], ["installer.zip"])
        self.assertEqual(self.release["assets"][0]["digest"], "sha256:" + hashlib.sha256(self.asset.read_bytes()).hexdigest())

    def test_replacement_stages_new_asset_before_removing_old_asset(self) -> None:
        self.release["assets"] = [{"id": 41, "name": "installer.zip", "state": "uploaded", "size": 3,
                                    "digest": "sha256:" + hashlib.sha256(b"old").hexdigest(), "label": None}]
        self.run_edit(replace_assets=[self.asset], apply=True)
        self.assertEqual([item["name"] for item in self.release["assets"]], ["installer.zip"])
        self.assertEqual(self.release["assets"][0]["digest"], "sha256:" + hashlib.sha256(self.asset.read_bytes()).hexdigest())
        upload_index = next(i for i, call in enumerate(self.calls) if call[:3] == ["gh", "release", "upload"])
        delete_index = next(i for i, call in enumerate(self.calls) if call[:3] == ["gh", "release", "delete-asset"])
        self.assertLess(upload_index, delete_index)

    def test_immutable_release_allows_metadata_but_blocks_asset_mutation(self) -> None:
        self.release["immutable"] = True
        self.run_edit(title="Immutable title", apply=True)
        self.assertEqual(self.release["name"], "Immutable title")
        self.calls.clear()
        with patch("edit_release.checked", side_effect=self.checked_side_effect):
            with self.assertRaisesRegex(EditError, "immutable"):
                edit_release("example/plugin", "v1.2.3", asset_paths=[self.asset], apply=True)
        self.assertFalse(any(call[:3] == ["gh", "release", "upload"] for call in self.calls))

    def test_latest_cannot_be_set_for_prerelease(self) -> None:
        with patch("edit_release.checked", side_effect=self.checked_side_effect):
            with self.assertRaisesRegex(EditError, "prerelease cannot be marked"):
                edit_release("example/plugin", "v1.2.3", latest=True, prerelease=True, apply=True)
        self.assertFalse(any(call[:3] == ["gh", "release", "edit"] for call in self.calls))

    def test_existing_asset_is_not_overwritten_implicitly(self) -> None:
        self.release["assets"] = [{"id": 42, "name": "installer.zip", "state": "uploaded", "size": 1,
                                    "digest": "sha256:" + hashlib.sha256(b"x").hexdigest(), "label": None}]
        with patch("edit_release.checked", side_effect=self.checked_side_effect):
            with self.assertRaisesRegex(EditError, "use --replace-asset explicitly"):
                edit_release("example/plugin", "v1.2.3", asset_paths=[self.asset], apply=True)
        self.assertFalse(any(call[:3] == ["gh", "release", "upload"] for call in self.calls))

    def test_asset_can_be_removed_by_exact_name(self) -> None:
        self.release["assets"] = [{"id": 51, "name": "old.zip", "state": "uploaded", "size": 1,
                                    "digest": "sha256:" + hashlib.sha256(b"x").hexdigest(), "label": None}]
        self.run_edit(remove_assets=["old.zip"], apply=True)
        self.assertEqual(self.release["assets"], [])
        self.assertTrue(any(call[:3] == ["gh", "release", "delete-asset"] for call in self.calls))

    def test_asset_label_can_be_updated_or_cleared(self) -> None:
        self.release["assets"] = [{"id": 52, "name": "installer.zip", "state": "uploaded", "size": 1,
                                    "digest": "sha256:" + hashlib.sha256(b"x").hexdigest(), "label": None}]
        self.run_edit(asset_labels=["installer.zip=Windows installer"], apply=True)
        self.assertEqual(self.release["assets"][0]["label"], "Windows installer")

    def test_latest_flag_is_applied_and_verified(self) -> None:
        self.run_edit(latest=True, apply=True)
        self.assertTrue(self.release["latest"])
        self.assertTrue(any("--latest=true" in call for call in self.calls))


if __name__ == "__main__":
    unittest.main()

