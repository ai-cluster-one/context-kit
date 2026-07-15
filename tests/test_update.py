import hashlib
import http.client
import importlib.machinery
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTEXTKIT = REPO_ROOT / "bin" / "contextkit"


def load_contextkit_module():
    name = "contextkit_update_test_module"
    loader = importlib.machinery.SourceFileLoader(name, str(CONTEXTKIT))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


class UpdateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.home = self.root / "home"
        self.install_home = self.root / "installed"
        self.bin_dir = self.root / "bin"
        self.remote = self.root / "remote"
        self.ref = "test-ref"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def env(self) -> dict[str, str]:
        env = dict(os.environ)
        env.update({
            "HOME": str(self.home),
            "CONTEXTKIT_HOME": str(self.install_home),
            "CONTEXTKIT_BIN": str(self.bin_dir),
            "CONTEXTKIT_RAW_BASE": self.remote.as_uri(),
            "CONTEXTKIT_REF": self.ref,
        })
        return env

    def run_cli(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(CONTEXTKIT), *args],
            cwd=str(cwd or REPO_ROOT),
            env=self.env(),
            text=True,
            capture_output=True,
            timeout=30,
        )

    def write_release(self, version: str = "1.0.0", manager: bytes | None = None) -> dict:
        release = self.remote / self.ref
        payloads = {
            "bin/contextkit": manager or b"#!/usr/bin/env python3\nprint('fixture contextkit')\n",
            "bundle/runtime.md": b"# Runtime\n",
            "guides/authoring.md": b"# Authoring Guide\n",
            "templates/README.md": b"# Templates\n",
        }
        files: dict[str, str] = {}
        for rel, content in payloads.items():
            destination = release / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            files[rel] = hashlib.sha256(content).hexdigest()
        manifest = {"schema": 1, "version": version, "files": files}
        (release / "release.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        return manifest

    def test_help_discovers_check_and_apply(self) -> None:
        result = self.run_cli("help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("contextkit update --check [--json]", result.stdout)
        self.assertIn("contextkit update --apply [--yes] [--json]", result.stdout)
        self.assertIn("otherwise installed provenance, then public repository", result.stdout)
        self.assertIn("otherwise installed provenance, then main", result.stdout)
        self.assertIn("CONTEXTKIT_SHA256", result.stdout)

    def test_check_is_read_only_and_reports_update_available(self) -> None:
        self.write_release()
        result = self.run_cli("update", "--check", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "update_available")
        self.assertIsNone(report["current"])
        self.assertEqual(report["available"]["version"], "1.0.0")
        self.assertEqual(report["source"]["ref"], self.ref)
        self.assertFalse(self.install_home.exists())

    def test_noninteractive_apply_requires_yes(self) -> None:
        self.write_release()
        result = self.run_cli("update", "--apply", "--json")
        self.assertEqual(result.returncode, 6)
        self.assertIn("requires --yes", result.stderr)
        self.assertFalse(self.install_home.exists())

    def test_apply_installs_complete_release_and_converges(self) -> None:
        manifest = self.write_release()
        project = self.root / "project"
        project.mkdir()
        marker = project / "doctrine.md"
        marker.write_text("unchanged\n")
        result = self.run_cli("update", "--apply", "--yes", "--json", cwd=project)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "updated")
        self.assertTrue(report["changed"])
        self.assertEqual(marker.read_text(), "unchanged\n")
        self.assertEqual(json.loads((self.install_home / "release.json").read_text()), manifest)
        self.assertTrue((self.install_home / ".manager" / "contextkit").is_file())
        self.assertEqual((self.install_home / "bundle" / "runtime.md").read_text(), "# Runtime\n")
        self.assertEqual((self.install_home / "guides" / "authoring.md").read_text(), "# Authoring Guide\n")
        self.assertEqual((self.install_home / "templates" / "README.md").read_text(), "# Templates\n")
        self.assertEqual((self.bin_dir / "contextkit").resolve(), (self.install_home / ".manager" / "contextkit").resolve())

        checked = self.run_cli("update", "--check", "--json")
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual(json.loads(checked.stdout)["status"], "up_to_date")

        repeated = self.run_cli("update", "--apply", "--yes", "--json")
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        repeated_report = json.loads(repeated.stdout)
        self.assertEqual(repeated_report["status"], "up_to_date")
        self.assertFalse(repeated_report["changed"])

    def test_payload_drift_is_repaired_by_apply(self) -> None:
        self.write_release()
        installed = self.run_cli("update", "--apply", "--yes", "--json")
        self.assertEqual(installed.returncode, 0, installed.stderr)
        runtime = self.install_home / "bundle" / "runtime.md"
        runtime.write_text("drift\n")
        checked = self.run_cli("update", "--check", "--json")
        self.assertEqual(checked.returncode, 0, checked.stderr)
        report = json.loads(checked.stdout)
        self.assertEqual(report["status"], "update_available")
        self.assertIn("differs", report["reason"])
        repaired = self.run_cli("update", "--apply", "--yes", "--json")
        self.assertEqual(repaired.returncode, 0, repaired.stderr)
        self.assertEqual(runtime.read_text(), "# Runtime\n")

    def test_ambiguous_same_version_and_network_failure_are_errors(self) -> None:
        self.write_release()
        installed = self.run_cli("update", "--apply", "--yes", "--json")
        self.assertEqual(installed.returncode, 0, installed.stderr)
        self.write_release(manager=b"#!/usr/bin/env python3\nprint('changed')\n")
        ambiguous = self.run_cli("update", "--check", "--json")
        self.assertEqual(ambiguous.returncode, 7)
        self.assertIn("different release manifests", ambiguous.stderr)

        shutil.rmtree(self.remote)
        missing = self.run_cli("update", "--check", "--json")
        self.assertEqual(missing.returncode, 5)
        self.assertIn("fetch failed", missing.stderr)

    def test_checksum_failure_does_not_replace_installed_release(self) -> None:
        self.write_release()
        installed = self.run_cli("update", "--apply", "--yes", "--json")
        self.assertEqual(installed.returncode, 0, installed.stderr)
        manager = self.install_home / ".manager" / "contextkit"
        before = manager.read_bytes()
        manifest = self.write_release(version="1.1.0")
        manifest["files"]["bin/contextkit"] = "0" * 64
        release_manifest = self.remote / self.ref / "release.json"
        release_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        failed = self.run_cli("update", "--apply", "--yes", "--json")
        self.assertEqual(failed.returncode, 6)
        self.assertIn("checksum mismatch", failed.stderr)
        self.assertEqual(manager.read_bytes(), before)
        self.assertEqual(json.loads((self.install_home / "release.json").read_text())["version"], "1.0.0")

    def test_missing_provenance_and_symlink_are_repairable_managed_drift(self) -> None:
        self.write_release()
        installed = self.run_cli("update", "--apply", "--yes", "--json")
        self.assertEqual(installed.returncode, 0, installed.stderr)
        (self.install_home / "install.json").unlink()
        (self.bin_dir / "contextkit").unlink()
        checked = self.run_cli("update", "--check", "--json")
        self.assertEqual(checked.returncode, 0, checked.stderr)
        report = json.loads(checked.stdout)
        self.assertEqual(report["status"], "update_available")
        self.assertTrue(any("provenance" in item for item in report["findings"]))
        self.assertTrue(any("symlink" in item for item in report["findings"]))
        repaired = self.run_cli("update", "--apply", "--yes", "--json")
        self.assertEqual(repaired.returncode, 0, repaired.stderr)
        self.assertTrue((self.install_home / "install.json").is_file())
        self.assertEqual((self.bin_dir / "contextkit").resolve(), (self.install_home / ".manager" / "contextkit").resolve())

    def test_invalid_provenance_and_foreign_symlink_need_review(self) -> None:
        self.write_release()
        installed = self.run_cli("update", "--apply", "--yes", "--json")
        self.assertEqual(installed.returncode, 0, installed.stderr)
        provenance = json.loads((self.install_home / "install.json").read_text())
        provenance["manifest_sha256"] = "0" * 64
        (self.install_home / "install.json").write_text(json.dumps(provenance))
        invalid = self.run_cli("update", "--check", "--json")
        self.assertEqual(invalid.returncode, 7)
        self.assertIn("provenance manifest hash", invalid.stderr)

        (self.install_home / "install.json").unlink()
        foreign = self.root / "foreign-contextkit"
        foreign.write_text("foreign\n")
        (self.bin_dir / "contextkit").unlink()
        (self.bin_dir / "contextkit").symlink_to(foreign)
        wrong_link = self.run_cli("update", "--check", "--json")
        self.assertEqual(wrong_link.returncode, 7)
        self.assertIn("owned by another target", wrong_link.stderr)

    def test_installed_source_persists_and_explicit_source_wins(self) -> None:
        self.write_release()
        installed = self.run_cli("update", "--apply", "--yes", "--json")
        self.assertEqual(installed.returncode, 0, installed.stderr)
        persisted_env = self.env()
        persisted_env.pop("CONTEXTKIT_RAW_BASE")
        persisted_env.pop("CONTEXTKIT_REF")
        persisted = subprocess.run(
            [str(CONTEXTKIT), "update", "--check", "--json"],
            cwd=str(REPO_ROOT), env=persisted_env, text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(persisted.returncode, 0, persisted.stderr)
        persisted_report = json.loads(persisted.stdout)
        self.assertEqual(persisted_report["source"]["base_origin"], "installed")
        self.assertEqual(persisted_report["source"]["ref_origin"], "installed")

        other = self.root / "other-remote"
        original_remote = self.remote
        self.remote = other
        self.write_release(version="1.1.0")
        override_env = self.env()
        overridden = subprocess.run(
            [str(CONTEXTKIT), "update", "--check", "--json"],
            cwd=str(REPO_ROOT), env=override_env, text=True, capture_output=True, timeout=30,
        )
        self.remote = original_remote
        self.assertEqual(overridden.returncode, 0, overridden.stderr)
        override_report = json.loads(overridden.stdout)
        self.assertEqual(override_report["available"]["version"], "1.1.0")
        self.assertEqual(override_report["source"]["base_origin"], "environment")

    def test_same_release_channel_switch_is_drift_and_apply_reports_post_state(self) -> None:
        manifest = self.write_release()
        installed = self.run_cli("update", "--apply", "--yes", "--json")
        self.assertEqual(installed.returncode, 0, installed.stderr)
        other = self.root / "same-release-mirror"
        release = other / self.ref
        for rel in manifest["files"]:
            destination = release / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.remote / self.ref / rel, destination)
        (release / "release.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        env = self.env()
        env["CONTEXTKIT_RAW_BASE"] = other.as_uri()
        checked = subprocess.run(
            [str(CONTEXTKIT), "update", "--check", "--json"],
            cwd=str(REPO_ROOT), env=env, text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(checked.returncode, 0, checked.stderr)
        check_report = json.loads(checked.stdout)
        self.assertEqual(check_report["status"], "update_available")
        self.assertTrue(any("selected update source" in item for item in check_report["findings"]))
        self.assertNotEqual(check_report["installed_source"]["source"]["base"], other.as_uri())

        applied = subprocess.run(
            [str(CONTEXTKIT), "update", "--apply", "--yes", "--json"],
            cwd=str(REPO_ROOT), env=env, text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(applied.returncode, 0, applied.stderr)
        apply_report = json.loads(applied.stdout)
        self.assertEqual(apply_report["status"], "updated")
        self.assertEqual(apply_report["current"]["version"], manifest["version"])
        self.assertEqual(apply_report["installed_source"]["source"]["base"], other.as_uri())
        self.assertNotIn("findings", apply_report)

    def test_credential_bearing_source_is_rejected_without_echoing_secret(self) -> None:
        env = self.env()
        env["CONTEXTKIT_RAW_BASE"] = "https://user:top-secret@example.invalid/context-kit"
        result = subprocess.run(
            [str(CONTEXTKIT), "update", "--check", "--json"],
            cwd=str(REPO_ROOT), env=env, text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(result.returncode, 6)
        self.assertNotIn("top-secret", result.stdout + result.stderr)
        self.assertIn("credentials", result.stderr)

        installer = subprocess.run(
            ["sh", str(REPO_ROOT / "install.sh")],
            cwd=str(REPO_ROOT), env=env, text=True, capture_output=True, timeout=30,
        )
        self.assertNotEqual(installer.returncode, 0)
        self.assertNotIn("top-secret", installer.stdout + installer.stderr)
        self.assertIn("invalid", installer.stderr)

    def test_source_base_manager_installer_validation_parity(self) -> None:
        module = load_contextkit_module()
        at_remote = self.root / "remote@mirror"
        canonical_file = at_remote.as_uri()
        self.assertEqual(module._validate_source_base(f"file://localhost{at_remote.as_posix()}/", "test"), canonical_file)
        self.assertEqual(
            module._validate_source_base("HTTPS://EXAMPLE.COM:443/context@kit/", "test"),
            "https://example.com:443/context@kit",
        )

        manifest = json.loads((REPO_ROOT / "release.json").read_text())
        release = at_remote / self.ref
        for rel in manifest["files"]:
            destination = release / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / rel, destination)
        (release / "release.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        env = self.env()
        env["CONTEXTKIT_RAW_BASE"] = f"file://localhost{at_remote.as_posix()}/"
        accepted_file = subprocess.run(
            ["sh", str(REPO_ROOT / "install.sh")], cwd=str(REPO_ROOT), env=env,
            text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(accepted_file.returncode, 0, accepted_file.stderr)
        provenance = json.loads((self.install_home / "install.json").read_text())
        self.assertEqual(provenance["source"]["base"], canonical_file)

        fake_bin = self.root / "fake-bin"
        fake_bin.mkdir()
        curl_log = self.root / "curl.log"
        fake_curl = fake_bin / "curl"
        fake_curl.write_text("#!/bin/sh\nprintf '%s\\n' \"$*\" > \"$CURL_LOG\"\nexit 22\n")
        fake_curl.chmod(0o755)
        http_env = self.env()
        http_env["PATH"] = str(fake_bin) + os.pathsep + http_env["PATH"]
        http_env["CURL_LOG"] = str(curl_log)
        http_env["CONTEXTKIT_RAW_BASE"] = "HTTPS://EXAMPLE.COM:443/context@kit/"
        accepted_http = subprocess.run(
            ["sh", str(REPO_ROOT / "install.sh")], cwd=str(REPO_ROOT), env=http_env,
            text=True, capture_output=True, timeout=30,
        )
        self.assertNotEqual(accepted_http.returncode, 0)
        self.assertIn("https://example.com:443/context@kit", curl_log.read_text())

        rejected = (
            "ftp://example.com/context-kit",
            "http://example.com:invalid/context-kit",
            "https://[::1/context-kit",
            "https://bad_host.example/context-kit",
            " https://example.com/context-kit",
            "https://example.com/context-kit ",
            "https://user:secret@example.com/context-kit",
            "https://example.com/context-kit?token=secret",
            "https://example.com/context-kit#fragment",
            "file:relative/context-kit",
            "file://other-host/absolute/context-kit",
        )
        for base in rejected:
            rejected_env = self.env()
            rejected_env["CONTEXTKIT_RAW_BASE"] = base
            manager = subprocess.run(
                [str(CONTEXTKIT), "update", "--check"], cwd=str(REPO_ROOT), env=rejected_env,
                text=True, capture_output=True, timeout=30,
            )
            installer = subprocess.run(
                ["sh", str(REPO_ROOT / "install.sh")], cwd=str(REPO_ROOT), env=rejected_env,
                text=True, capture_output=True, timeout=30,
            )
            self.assertEqual(manager.returncode, 6, (base, manager.stderr))
            self.assertNotEqual(installer.returncode, 0, (base, installer.stderr))
            self.assertIn("source", manager.stderr.lower())
            self.assertIn("invalid", installer.stderr.lower())
            if "secret" in base:
                self.assertNotIn("secret", manager.stdout + manager.stderr)
                self.assertNotIn("secret", installer.stdout + installer.stderr)

    def test_explicit_empty_source_is_rejected_before_installer_fetch(self) -> None:
        fake_bin = self.root / "empty-source-fake-bin"
        fake_bin.mkdir()
        curl_marker = self.root / "curl-was-called"
        fake_curl = fake_bin / "curl"
        fake_curl.write_text("#!/bin/sh\nprintf called > \"$CURL_MARKER\"\nexit 99\n")
        fake_curl.chmod(0o755)
        env = self.env()
        env["CONTEXTKIT_RAW_BASE"] = ""
        env["PATH"] = str(fake_bin) + os.pathsep + env["PATH"]
        env["CURL_MARKER"] = str(curl_marker)
        manager = subprocess.run(
            [str(CONTEXTKIT), "update", "--check"], cwd=str(REPO_ROOT), env=env,
            text=True, capture_output=True, timeout=30,
        )
        installer = subprocess.run(
            ["sh", str(REPO_ROOT / "install.sh")], cwd=str(REPO_ROOT), env=env,
            text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(manager.returncode, 6, manager.stderr)
        self.assertNotEqual(installer.returncode, 0, installer.stderr)
        self.assertIn("source", manager.stderr.lower())
        self.assertIn("invalid", installer.stderr.lower())
        self.assertNotIn("Traceback", manager.stderr + installer.stderr)
        self.assertFalse(curl_marker.exists())

    def test_http_client_url_failures_are_controlled(self) -> None:
        module = load_contextkit_module()
        source = module.UpdateSource("https://example.com/context@kit", "main", "environment", "environment")
        with mock.patch.object(module.urllib.request, "urlopen", side_effect=http.client.InvalidURL("injected invalid URL")):
            with self.assertRaises(module.ContextKitError) as raised:
                module._fetch_update_bytes(source, "release.json")
        self.assertEqual(raised.exception.exit_code, 5)
        self.assertIn("fetch failed", str(raised.exception))
        self.assertNotIn("Traceback", str(raised.exception))

    def test_sha_pin_constrains_manifest_and_downloaded_manager(self) -> None:
        manifest = self.write_release()
        env = self.env()
        env["CONTEXTKIT_SHA256"] = "f" * 64
        mismatch = subprocess.run(
            [str(CONTEXTKIT), "update", "--apply", "--yes", "--json"],
            cwd=str(REPO_ROOT), env=env, text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(mismatch.returncode, 6)
        self.assertIn("does not match CONTEXTKIT_SHA256", mismatch.stderr)
        self.assertFalse(self.install_home.exists())

        env["CONTEXTKIT_SHA256"] = manifest["files"]["bin/contextkit"]
        (self.remote / self.ref / "bin" / "contextkit").write_bytes(b"#!/usr/bin/env python3\nprint('moved')\n")
        moved = subprocess.run(
            [str(CONTEXTKIT), "update", "--apply", "--yes", "--json"],
            cwd=str(REPO_ROOT), env=env, text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(moved.returncode, 6)
        self.assertIn("checksum mismatch", moved.stderr)
        self.assertFalse(self.install_home.exists())

    def test_path_guards_reject_overlap_symlinks_and_foreign_managed_trees(self) -> None:
        self.write_release()
        for home, bin_dir in (
            (self.root / "same", self.root / "same"),
            (self.root / "nested", self.root / "nested" / "bin"),
            (self.root / "outer" / "home", self.root / "outer"),
        ):
            env = self.env()
            env["CONTEXTKIT_HOME"] = str(home)
            env["CONTEXTKIT_BIN"] = str(bin_dir)
            result = subprocess.run(
                [str(CONTEXTKIT), "update", "--check"], cwd=str(REPO_ROOT), env=env,
                text=True, capture_output=True, timeout=30,
            )
            self.assertEqual(result.returncode, 7)
            self.assertIn("must not overlap", result.stderr)

        actual = self.root / "actual"
        actual.mkdir()
        alias = self.root / "alias"
        alias.symlink_to(actual, target_is_directory=True)
        env = self.env()
        env["CONTEXTKIT_HOME"] = str(alias / "installed")
        symlinked = subprocess.run(
            [str(CONTEXTKIT), "update", "--check"], cwd=str(REPO_ROOT), env=env,
            text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(symlinked.returncode, 7)
        self.assertIn("symlink ancestor", symlinked.stderr)

        self.install_home.mkdir()
        foreign_bundle = self.root / "foreign-bundle"
        foreign_bundle.mkdir()
        (self.install_home / "bundle").symlink_to(foreign_bundle, target_is_directory=True)
        foreign_tree = self.run_cli("update", "--check")
        self.assertEqual(foreign_tree.returncode, 7)
        self.assertIn("foreign shape", foreign_tree.stderr)

    def test_relative_install_paths_are_normalized(self) -> None:
        self.write_release()
        env = self.env()
        env["CONTEXTKIT_HOME"] = "relative-home"
        env["CONTEXTKIT_BIN"] = "relative-bin"
        result = subprocess.run(
            [str(CONTEXTKIT), "update", "--check", "--json"],
            cwd=str(self.root), env=env, text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["install_home"], str(self.root / "relative-home"))

    def test_manifest_duplicate_keys_collisions_and_unsafe_paths_are_controlled(self) -> None:
        self.write_release()
        release = self.remote / self.ref / "release.json"
        release.write_text('{"schema":1,"schema":1,"version":"1.0.0","files":{}}')
        duplicate = self.run_cli("update", "--check")
        self.assertEqual(duplicate.returncode, 6)
        self.assertIn("duplicate JSON object key", duplicate.stderr)
        self.assertNotIn("Traceback", duplicate.stderr)

        for bad_path in ("guides/authoring.md/child", "guides/../escape.md"):
            manifest = self.write_release()
            manifest["files"][bad_path] = "0" * 64
            release.write_text(json.dumps(manifest))
            malformed = self.run_cli("update", "--check")
            self.assertEqual(malformed.returncode, 6)
            self.assertIn("invalid ContextKit release", malformed.stderr)
            self.assertNotIn("Traceback", malformed.stderr)

    def test_ref_grammar_blocks_traversal_with_manager_installer_parity(self) -> None:
        self.write_release()
        invalid_refs = ("", "/main", "main/", "feature//x", ".", "..", "feature/../x", "feature\\x", "%2e%2e")
        for ref in invalid_refs:
            env = self.env()
            env["CONTEXTKIT_REF"] = ref
            manager = subprocess.run(
                [str(CONTEXTKIT), "update", "--check"], cwd=str(REPO_ROOT), env=env,
                text=True, capture_output=True, timeout=30,
            )
            installer = subprocess.run(
                ["sh", str(REPO_ROOT / "install.sh")], cwd=str(REPO_ROOT), env=env,
                text=True, capture_output=True, timeout=30,
            )
            self.assertEqual(manager.returncode, 6, (ref, manager.stderr))
            self.assertNotEqual(installer.returncode, 0, (ref, installer.stderr))
            self.assertIn("ref", manager.stderr.lower())
            self.assertIn("ref", installer.stderr.lower())
            self.assertFalse(self.install_home.exists())

        valid_ref = "feature/release-1.0"
        self.ref = valid_ref
        self.write_release()
        valid = self.run_cli("update", "--check", "--json")
        self.assertEqual(valid.returncode, 0, valid.stderr)

    def test_legacy_remote_routes_use_the_same_ref_validation(self) -> None:
        copied = self.root / "standalone" / "contextkit"
        copied.parent.mkdir()
        shutil.copyfile(CONTEXTKIT, copied)
        copied.chmod(0o755)
        env = self.env()
        env["CONTEXTKIT_REF"] = "../escape"
        env["CONTEXTKIT_GUIDES_DIR"] = str(self.root / "missing-guides")
        result = subprocess.run(
            [str(copied), "guide", "authoring"], cwd=str(self.root), env=env,
            text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(result.returncode, 6)
        self.assertIn("ref", result.stderr.lower())
        self.assertNotIn("Traceback", result.stderr)

    def test_manifest_and_provenance_require_strict_bounded_types(self) -> None:
        manifest = self.write_release()
        release_path = self.remote / self.ref / "release.json"
        for schema, version in ((True, "1.0.0"), (1.0, "1.0.0"), (1, "1234567.0.0"), (1, "01.0.0")):
            malformed = dict(manifest)
            malformed["schema"] = schema
            malformed["version"] = version
            release_path.write_text(json.dumps(malformed))
            result = self.run_cli("update", "--check")
            self.assertEqual(result.returncode, 6, (schema, version, result.stderr))
            self.assertNotIn("Traceback", result.stderr)

        self.write_release()
        installed = self.run_cli("update", "--apply", "--yes", "--json")
        self.assertEqual(installed.returncode, 0, installed.stderr)
        installed_release_path = self.install_home / "release.json"
        installed_release = json.loads(installed_release_path.read_text())
        installed_release["schema"] = True
        installed_release_path.write_text(json.dumps(installed_release))
        bad_installed_manifest = self.run_cli("update", "--check")
        self.assertEqual(bad_installed_manifest.returncode, 7)
        self.assertNotIn("Traceback", bad_installed_manifest.stderr)
        installed_release["schema"] = 1
        installed_release_path.write_text(json.dumps(installed_release, indent=2, sort_keys=True) + "\n")

        provenance_path = self.install_home / "install.json"
        provenance = json.loads(provenance_path.read_text())
        provenance["schema"] = True
        provenance_path.write_text(json.dumps(provenance))
        bad_schema = self.run_cli("update", "--check")
        self.assertEqual(bad_schema.returncode, 7)
        self.assertNotIn("Traceback", bad_schema.stderr)

        provenance["schema"] = 1
        provenance["version"] = "9999999.0.0"
        provenance_path.write_text(json.dumps(provenance))
        bad_version = self.run_cli("update", "--check")
        self.assertEqual(bad_version.returncode, 7)
        self.assertNotIn("Traceback", bad_version.stderr)

    def test_installer_uses_the_same_release_contract(self) -> None:
        self.assertNotIn("ln -sf", (REPO_ROOT / "install.sh").read_text())
        manifest = json.loads((REPO_ROOT / "release.json").read_text())
        release = self.remote / self.ref
        for rel in manifest["files"]:
            destination = release / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / rel, destination)
        (release / "release.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        env = self.env()
        env["CONTEXTKIT_TAG"] = self.ref
        result = subprocess.run(
            ["sh", str(REPO_ROOT / "install.sh")],
            cwd=str(REPO_ROOT),
            env=env,
            text=True,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.install_home / "release.json").read_text()), manifest)
        self.assertEqual((self.bin_dir / "contextkit").resolve(), (self.install_home / ".manager" / "contextkit").resolve())


class ReleaseManifestTests(unittest.TestCase):
    def test_manifest_covers_the_installed_distribution(self) -> None:
        manifest = json.loads((REPO_ROOT / "release.json").read_text())
        self.assertEqual(manifest["schema"], 1)
        expected = {"bin/contextkit", "bundle/runtime.md"}
        for directory in ("guides", "templates"):
            expected.update(
                path.relative_to(REPO_ROOT).as_posix()
                for path in (REPO_ROOT / directory).rglob("*")
                if path.is_file()
            )
        self.assertEqual(set(manifest["files"]), expected)
        for rel, expected_hash in manifest["files"].items():
            actual = hashlib.sha256((REPO_ROOT / rel).read_bytes()).hexdigest()
            self.assertEqual(actual, expected_hash, rel)


class UpdateTransactionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.module = load_contextkit_module()
        self.paths = self.module.InstallPaths(
            home=self.root / "home",
            bin_dir=self.root / "bin",
            manager=self.root / "home" / ".manager" / "contextkit",
            link=self.root / "bin" / "contextkit",
        )
        self.paths.home.mkdir()
        self.paths.bin_dir.mkdir()
        self.stage = self.root / "stage"
        self.stage.mkdir()
        for name in (".manager", "bundle", "guides", "templates"):
            old = self.paths.home / name
            new = self.stage / name
            old.mkdir()
            new.mkdir()
            (old / "marker").write_text("old\n")
            (new / "marker").write_text("new\n")
        for name in ("release.json", "install.json"):
            (self.paths.home / name).write_text("old\n")
            (self.stage / name).write_text("new\n")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_replacement_failure_restores_old_distribution(self) -> None:
        real_replace = os.replace

        def fail_during_replacement(source, destination):
            if Path(source) == self.stage / "guides" and Path(destination) == self.paths.home / "guides":
                raise OSError("injected replacement failure")
            return real_replace(source, destination)

        with mock.patch.object(self.module.os, "replace", side_effect=fail_during_replacement):
            with self.assertRaises(OSError):
                self.module._replace_install(self.paths, self.stage)
        for name in (".manager", "bundle", "guides", "templates"):
            self.assertEqual((self.paths.home / name / "marker").read_text(), "old\n")
        self.assertFalse(list(self.root.glob("*backup-*")))

    def test_incomplete_rollback_preserves_and_reports_backup(self) -> None:
        real_replace = os.replace

        def fail_replacement_and_restore(source, destination):
            source_path = Path(source)
            destination_path = Path(destination)
            if source_path == self.stage / "guides" and destination_path == self.paths.home / "guides":
                raise OSError("injected replacement failure")
            if source_path.name == "bundle" and "-backup-" in source_path.parent.name:
                raise OSError("injected rollback failure")
            return real_replace(source, destination)

        with mock.patch.object(self.module.os, "replace", side_effect=fail_replacement_and_restore):
            with self.assertRaises(self.module.ContextKitError) as raised:
                self.module._replace_install(self.paths, self.stage)
        self.assertIn("backup preserved at", str(raised.exception))
        backups = list(self.root.glob("*backup-*"))
        self.assertEqual(len(backups), 1)
        self.assertTrue((backups[0] / "bundle" / "marker").is_file())

    def test_apply_wrapper_cleans_stage_when_replacement_fails(self) -> None:
        source = self.module.UpdateSource("file:///fixture", "main", "environment", "environment")
        with mock.patch.object(self.module, "_stage_update", return_value=self.stage), mock.patch.object(
            self.module, "_replace_install", side_effect=OSError("injected")
        ):
            with self.assertRaises(OSError):
                self.module._apply_update(self.paths, source, {}, b"{}")
        self.assertFalse(self.stage.exists())

    def test_successful_install_with_backup_cleanup_residue_is_reported(self) -> None:
        real_rmtree = shutil.rmtree

        def fail_backup_cleanup(path, *args, **kwargs):
            if "-backup-" in Path(path).name:
                raise OSError("injected backup cleanup failure")
            return real_rmtree(path, *args, **kwargs)

        with mock.patch.object(self.module.shutil, "rmtree", side_effect=fail_backup_cleanup):
            with self.assertRaises(self.module.ContextKitError) as raised:
                self.module._replace_install(self.paths, self.stage)
        self.assertIn("was installed, but backup cleanup is incomplete", str(raised.exception))
        backups = list(self.root.glob("*backup-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual((self.paths.home / "bundle" / "marker").read_text(), "new\n")
        with self.assertRaises(self.module.ContextKitError) as residue:
            self.module._validate_no_update_residue(self.paths)
        self.assertIn(str(backups[0]), str(residue.exception))

    def test_successful_install_with_stage_cleanup_residue_is_reported(self) -> None:
        source = self.module.UpdateSource("file:///fixture", "main", "environment", "environment")
        owned_stage = self.root / (self.module._residue_prefix(self.paths, "stage") + "fixture")
        self.stage.rename(owned_stage)
        self.stage = owned_stage
        real_cleanup = self.module._cleanup_tree

        def fail_stage_cleanup(path):
            if Path(path) == self.stage:
                return "injected stage cleanup failure"
            return real_cleanup(path)

        with mock.patch.object(self.module, "_stage_update", return_value=self.stage), mock.patch.object(
            self.module, "_replace_install", return_value=str(self.paths.link)
        ), mock.patch.object(self.module, "_cleanup_tree", side_effect=fail_stage_cleanup):
            with self.assertRaises(self.module.ContextKitError) as raised:
                self.module._apply_update(self.paths, source, {}, b"{}")
        self.assertIn("was installed, but stage cleanup is incomplete", str(raised.exception))
        self.assertTrue(self.stage.exists())
        with self.assertRaises(self.module.ContextKitError) as residue:
            self.module._validate_no_update_residue(self.paths)
        self.assertIn(str(self.stage), str(residue.exception))


if __name__ == "__main__":
    unittest.main()
