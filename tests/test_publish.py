from __future__ import annotations

import hashlib
import json
import sys
import unittest
import uuid
from pathlib import Path
import shutil
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build as package_builder
from publish import PublishError, publish


COMMIT = "a" * 40
RELEASE_ID = 17
ROOT = Path(__file__).resolve().parents[1]


class PublisherTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = ROOT / ".test-runtime" / uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.source_root = self.root / "source"
        plugin = self.source_root / "example-plugin"
        plugin.mkdir(parents=True)
        (plugin / "example-plugin.php").write_text("<?php\n/*\n * Version: 1.2.3\n */\n", encoding="utf-8")
        (plugin / "readme.txt").write_text("Package source\n", encoding="utf-8")
        self.manifest = self.root / "package-files.json"
        self.manifest.write_text(json.dumps({"schema_version": 1, "products": {"free": {
            "slug": "example-plugin", "files": ["example-plugin.php", "readme.txt"]
        }}}), encoding="utf-8")
        generated_dir = self.root / "generated"
        package_builder.build(self.source_root, generated_dir, {"free": package_builder.read_manifest(self.manifest)["products"]["free"]})
        self.archive = self.root / "example-plugin-v1.2.3.zip"
        shutil.copyfile(generated_dir / self.archive.name, self.archive)
        self.digest = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        self.sidecar = Path(str(self.archive) + ".sha256")
        shutil.copyfile(generated_dir / (self.archive.name + ".sha256"), self.sidecar)
        self.notes = self.root / "notes.md"
        self.notes.write_text("Release notes\n", encoding="utf-8")
        self.assets = [self.archive, self.sidecar]

    def tearDown(self) -> None:
        shutil.rmtree(self.root)

    def run_publish(self, *, prerelease: bool = False) -> str:
        return publish("example/plugin", "v1.2.3", "Version 1.2.3", self.notes, self.assets,
                       self.manifest, self.source_root, prerelease)

    def release(self, draft: bool) -> dict:
        return {
            "id": RELEASE_ID,
            "draft": draft,
            "prerelease": False,
            "html_url": "https://github.com/example/plugin/releases/tag/v1.2.3",
            "assets": [
                {"name": asset.name, "state": "uploaded", "size": asset.stat().st_size,
                 "digest": "sha256:" + hashlib.sha256(asset.read_bytes()).hexdigest()}
                for asset in self.assets
            ],
        }

    @staticmethod
    def result(stdout: str = "", returncode: int = 0, stderr: str = ""):
        from subprocess import CompletedProcess
        return CompletedProcess([], returncode, stdout, stderr)

    def git_result(self, args):
        if args[:3] == ["git", "rev-parse", "HEAD"]:
            return self.result(COMMIT + "\n")
        if args[:3] == ["git", "rev-parse", "--show-toplevel"]:
            return self.result(str(self.root) + "\n")
        if len(args) == 3 and args[:2] == ["git", "rev-parse"] and args[2].startswith("HEAD:"):
            return self.result("d" * 40 + "\n")
        if args[:2] == ["git", "hash-object"]:
            return self.result("d" * 40 + "\n")
        return None

    def test_publishes_only_after_draft_assets_are_verified(self) -> None:
        release_responses = [json.dumps(self.release(True)), json.dumps(self.release(False))]

        def fake_run(args, **kwargs):
            git = self.git_result(args)
            if git:
                return git
            if args[:3] == ["git", "rev-parse", "HEAD"]:
                return self.result(COMMIT + "\n")
            if args[:3] == ["gh", "api", "repos/example/plugin/git/ref/tags/v1.2.3"]:
                return self.result(json.dumps({"object": {"sha": COMMIT, "type": "commit"}}))
            if args[:3] == ["gh", "release", "create"]:
                return self.result("draft created\n")
            if args[:3] == ["gh", "api", "repos/example/plugin/releases/tags/v1.2.3"]:
                return self.result(release_responses.pop(0))
            if args[:3] == ["gh", "api", "--method"]:
                return self.result("{}")
            self.fail(f"Unexpected command: {args}")

        with patch("publish.subprocess.run", side_effect=fake_run) as mocked:
            url = self.run_publish()

        self.assertEqual(url, "https://github.com/example/plugin/releases/tag/v1.2.3")
        commands = [item.args[0] for item in mocked.call_args_list]
        create = next(command for command in commands if command[:3] == ["gh", "release", "create"])
        self.assertIn("--draft", create)
        self.assertIn("--verify-tag", create)
        self.assertNotIn("--clobber", create)
        self.assertLess(commands.index(create), next(i for i, command in enumerate(commands) if command[:3] == ["gh", "api", "--method"]))

    def test_tag_mismatch_blocks_release_creation(self) -> None:
        def fake_run(args, **kwargs):
            git = self.git_result(args)
            if git:
                return git
            if args[:3] == ["git", "rev-parse", "HEAD"]:
                return self.result(COMMIT)
            if args[:3] == ["gh", "api", "repos/example/plugin/git/ref/tags/v1.2.3"]:
                return self.result(json.dumps({"object": {"sha": "b" * 40, "type": "commit"}}))
            self.fail(f"Unexpected command: {args}")

        with patch("publish.subprocess.run", side_effect=fake_run) as mocked:
            with self.assertRaisesRegex(PublishError, "not the current source commit"):
                self.run_publish()
        self.assertFalse(any(item.args[0][:3] == ["gh", "release", "create"] for item in mocked.call_args_list))

    def test_remote_asset_mismatch_keeps_release_unpublished(self) -> None:
        bad = self.release(True)
        bad["assets"][0]["digest"] = "sha256:" + "0" * 64

        def fake_run(args, **kwargs):
            git = self.git_result(args)
            if git:
                return git
            if args[:3] == ["git", "rev-parse", "HEAD"]:
                return self.result(COMMIT)
            if args[:3] == ["gh", "api", "repos/example/plugin/git/ref/tags/v1.2.3"]:
                return self.result(json.dumps({"object": {"sha": COMMIT, "type": "commit"}}))
            if args[:3] == ["gh", "release", "create"]:
                return self.result()
            if args[:3] == ["gh", "api", "repos/example/plugin/releases/tags/v1.2.3"]:
                return self.result(json.dumps(bad))
            self.fail(f"Unexpected command: {args}")

        with patch("publish.subprocess.run", side_effect=fake_run) as mocked:
            with self.assertRaisesRegex(PublishError, "digest does not match"):
                self.run_publish()
        self.assertFalse(any(item.args[0][:3] == ["gh", "api", "--method"] for item in mocked.call_args_list))

    def test_checksum_mismatch_fails_before_any_command(self) -> None:
        self.sidecar.write_text("0" * 64 + "  " + self.archive.name + "\n", encoding="ascii")
        with patch("publish.subprocess.run") as mocked:
            with self.assertRaisesRegex(PublishError, "sidecar does not match"):
                self.run_publish()
        self.assertFalse(any(item.args[0][0] == "gh" for item in mocked.call_args_list))

    def test_annotated_tag_is_resolved_to_commit(self) -> None:
        release_responses = [json.dumps(self.release(True)), json.dumps(self.release(False))]

        def fake_run(args, **kwargs):
            git = self.git_result(args)
            if git:
                return git
            if args[:3] == ["git", "rev-parse", "HEAD"]:
                return self.result(COMMIT)
            if args[:3] == ["gh", "api", "repos/example/plugin/git/ref/tags/v1.2.3"]:
                return self.result(json.dumps({"object": {"sha": "c" * 40, "type": "tag"}}))
            if args[:3] == ["gh", "api", "repos/example/plugin/git/tags/" + "c" * 40]:
                return self.result(json.dumps({"object": {"sha": COMMIT, "type": "commit"}}))
            if args[:3] == ["gh", "release", "create"]:
                return self.result()
            if args[:3] == ["gh", "api", "repos/example/plugin/releases/tags/v1.2.3"]:
                return self.result(release_responses.pop(0))
            if args[:3] == ["gh", "api", "--method"]:
                return self.result("{}")
            self.fail(f"Unexpected command: {args}")

        with patch("publish.subprocess.run", side_effect=fake_run):
            self.assertIn("github.com/example/plugin/releases", self.run_publish())

    def test_package_that_does_not_match_current_source_is_not_published(self) -> None:
        self.archive.write_bytes(b"different package")
        self.digest = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        self.sidecar.write_text(f"{self.digest}  {self.archive.name}\n", encoding="ascii")
        def fake_run(args, **kwargs):
            git = self.git_result(args)
            if git:
                return git
            self.fail(f"Unexpected command: {args}")

        with patch("publish.subprocess.run", side_effect=fake_run) as mocked:
            with self.assertRaisesRegex(PublishError, "does not match the current source"):
                self.run_publish()
        self.assertFalse(any(item.args[0][0] == "gh" for item in mocked.call_args_list))

    def test_uncommitted_manifest_content_blocks_publication(self) -> None:
        def fake_run(args, **kwargs):
            if args[:3] == ["git", "rev-parse", "--show-toplevel"]:
                return self.result(str(self.root))
            if args[:3] == ["git", "rev-parse", "HEAD:package-files.json"]:
                return self.result("e" * 40)
            if args[:2] == ["git", "hash-object"]:
                return self.result("d" * 40)
            self.fail(f"Unexpected command: {args}")

        with patch("publish.subprocess.run", side_effect=fake_run) as mocked:
            with self.assertRaisesRegex(PublishError, "differs from the current source commit"):
                self.run_publish()
        self.assertEqual(len(mocked.call_args_list), 3)

    def test_existing_verification_directory_is_preserved(self) -> None:
        output_dir = self.source_root / ".ark-release-verify-collision"
        output_dir.mkdir()
        marker = output_dir / "user-data.txt"
        marker.write_text("preserve", encoding="utf-8")
        fake_uuid = type("FixedUUID", (), {"hex": "collision"})()

        def fake_run(args, **kwargs):
            git = self.git_result(args)
            if git:
                return git
            self.fail(f"Unexpected command: {args}")

        with patch("publish.uuid.uuid4", return_value=fake_uuid):
            with patch("publish.subprocess.run", side_effect=fake_run) as mocked:
                with self.assertRaisesRegex(PublishError, "Could not reproduce the package"):
                    self.run_publish()
        self.assertTrue(marker.exists())
        self.assertEqual(marker.read_text(encoding="utf-8"), "preserve")
        self.assertFalse(any(item.args[0][0] == "gh" for item in mocked.call_args_list))


if __name__ == "__main__":
    unittest.main()

