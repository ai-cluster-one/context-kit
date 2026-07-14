from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTEXTKIT = REPO_ROOT / "bin" / "contextkit"


class GlobalContextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        self.global_context = self.root / "global-context"
        self.project.mkdir()
        self.global_context.mkdir()
        initialized = self.run_cli("init", "--with-layers", "--json")
        self.assertEqual(initialized.returncode, 0, initialized.stderr)

    def run_cli(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        merged_env = dict(os.environ)
        if env:
            merged_env.update(env)
        return subprocess.run(
            [str(CONTEXTKIT), *args],
            cwd=self.project,
            env=merged_env,
            text=True,
            capture_output=True,
            check=False,
        )

    def configure_global(self, value: str | None = None) -> None:
        config = self.project / ".contextkit" / "config.toml"
        text = config.read_text()
        configured = value or self.global_context.as_posix()
        text = text.replace('# global_context = "~/contextkit-global"', f'global_context = "{configured}"')
        config.write_text(text)

    @staticmethod
    def context_file(title: str, description: str, load: str, order: int, body: str) -> str:
        return (
            "---\n"
            f"title: {title}\n"
            f"description: {description}\n"
            f"load: {load}\n"
            f"order: {order}\n"
            "---\n\n"
            f"# {title}\n\n"
            f"{body}\n"
        )

    def test_build_combines_recursive_global_and_project_context(self) -> None:
        self.configure_global()
        global_inline = self.global_context / "shared" / "BASE.md"
        global_inline.parent.mkdir()
        global_inline.write_text(self.context_file(
            "Shared Base",
            "Always load for shared rules inherited by participating projects.",
            "inline",
            10,
            "Follow the shared baseline.",
        ))
        global_stub = self.global_context / "reference" / "DETAILS.md"
        global_stub.parent.mkdir()
        global_stub.write_text(self.context_file(
            "Shared Details",
            "Load when work requires the shared cross-project reference model.",
            "stub",
            30,
            "This file owns the shared reference model.",
        ))
        project_inline = self.project / "context" / "identity" / "PROJECT.md"
        project_inline.parent.mkdir()
        project_inline.write_text(self.context_file(
            "Project Identity",
            "Always load for the identity and boundaries of this specific project.",
            "inline",
            10,
            "This project owns its local identity.",
        ))

        build = self.run_cli("build", "--target", "all", "--json")
        self.assertEqual(build.returncode, 0, build.stderr)

        for target in [
            self.project / ".codex" / "generated" / "context.md",
            self.project / ".claude" / "rules" / "CONTEXT.md",
        ]:
            generated = target.read_text()
            resolved_global = self.global_context.resolve()
            resolved_inline = global_inline.resolve()
            resolved_stub = global_stub.resolve()
            self.assertIn(f"- Global context: `{resolved_global}`", generated)
            self.assertIn("`contextkit guide global-context`", generated)
            self.assertIn(f"## Global Source: `{resolved_inline}`", generated)
            self.assertIn("## Source: `context/identity/PROJECT.md`", generated)
            self.assertLess(generated.index("# Shared Base"), generated.index("# Project Identity"))
            self.assertIn(f"(`{resolved_stub}`, global)", generated)

        doctor = self.run_cli("doctor", "--json")
        self.assertEqual(doctor.returncode, 0, doctor.stderr)
        report = json.loads(doctor.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["global_context"]["path"], str(self.global_context.resolve()))
        self.assertTrue(report["global_context"]["directory"])
        self.assertIn("contextkit guide global-context", report["rule_sources"])

        audit = self.run_cli("audit", "--json")
        self.assertEqual(audit.returncode, 0, audit.stderr)
        self.assertEqual(json.loads(audit.stdout)["findings"], [])

    def test_default_config_keeps_global_context_disabled_and_discoverable(self) -> None:
        build = self.run_cli("build", "--target", "codex")
        self.assertEqual(build.returncode, 0, build.stderr)
        generated = (self.project / ".codex" / "generated" / "context.md").read_text()
        self.assertNotIn("- Global context:", generated)
        self.assertIn("`contextkit guide global-context`", generated)

        doctor = self.run_cli("doctor", "--json")
        self.assertEqual(doctor.returncode, 0, doctor.stderr)
        self.assertIsNone(json.loads(doctor.stdout)["global_context"])

    def test_missing_global_directory_is_reported(self) -> None:
        missing = self.root / "missing-global-context"
        self.configure_global(missing.as_posix())

        doctor = self.run_cli("doctor", "--json")
        self.assertEqual(doctor.returncode, 0, doctor.stderr)
        report = json.loads(doctor.stdout)
        self.assertFalse(report["ok"])
        self.assertIn(f"missing global context source: {missing.resolve()}", report["problems"])

        build = self.run_cli("build", "--target", "codex")
        self.assertEqual(build.returncode, 6)
        self.assertIn("global context source directory not found", build.stderr)

    def test_global_context_must_live_outside_project(self) -> None:
        local_source = self.project / "shared-context"
        local_source.mkdir()
        self.configure_global(local_source.as_posix())

        doctor = self.run_cli("doctor", "--json")
        self.assertEqual(doctor.returncode, 6)
        self.assertIn("Global context and the project must be separate", doctor.stderr)

    def test_global_context_cannot_contain_project(self) -> None:
        self.configure_global(self.root.as_posix())

        doctor = self.run_cli("doctor", "--json")
        self.assertEqual(doctor.returncode, 6)
        self.assertIn("Global context and the project must be separate", doctor.stderr)

    def test_environment_anchor_resolves_global_context(self) -> None:
        self.configure_global("${TEST_CONTEXTKIT_GLOBAL}")
        context = self.global_context / "BASE.md"
        context.write_text(self.context_file(
            "Environment Shared Base",
            "Always load for shared doctrine resolved through an environment anchor.",
            "inline",
            10,
            "Follow the environment-anchored shared baseline.",
        ))

        build = self.run_cli(
            "build",
            "--target",
            "codex",
            env={"TEST_CONTEXTKIT_GLOBAL": str(self.global_context)},
        )
        self.assertEqual(build.returncode, 0, build.stderr)
        self.assertIn(f"## Global Source: `{context.resolve()}`", (self.project / ".codex" / "generated" / "context.md").read_text())

    def test_invalid_global_frontmatter_blocks_build(self) -> None:
        self.configure_global()
        broken = self.global_context / "BROKEN.md"
        broken.write_text(
            "---\n"
            "title: Broken Global Context\n"
            "description: Load when validating malformed shared context metadata.\n"
            "load: inline\n"
            "---\n\n"
            "# Broken Global Context\n"
        )

        build = self.run_cli("build", "--target", "codex")
        self.assertEqual(build.returncode, 6)
        self.assertIn("Invalid frontmatter order", build.stderr)

        audit = self.run_cli("audit-file", str(broken), "--json")
        self.assertEqual(audit.returncode, 0, audit.stderr)
        findings = json.loads(audit.stdout)["findings"]
        self.assertEqual(findings[0]["code"], "metadata")
        self.assertEqual(findings[0]["path"], str(broken.resolve()))

    def test_audit_compares_claims_across_global_and_project_context(self) -> None:
        self.configure_global()
        repeated_claim = "Every participating agent preserves this exact durable cross-project claim in one live owner only."
        (self.global_context / "SHARED.md").write_text(self.context_file(
            "Shared Claim",
            "Always load for a durable claim shared by all participating projects.",
            "inline",
            10,
            repeated_claim,
        ))
        local = self.project / "context" / "guidelines" / "DUPLICATE.md"
        local.parent.mkdir()
        local.write_text(self.context_file(
            "Duplicated Claim",
            "Always load when checking duplicate doctrine across configured context sources.",
            "inline",
            20,
            repeated_claim,
        ))

        audit = self.run_cli("audit", "--json")
        self.assertEqual(audit.returncode, 0, audit.stderr)
        findings = json.loads(audit.stdout)["findings"]
        duplicates = [item for item in findings if item["code"] == "duplicate-live-fact"]
        self.assertEqual(len(duplicates), 1)
        self.assertIn(str((self.global_context / "SHARED.md").resolve()), duplicates[0]["path"])
        self.assertIn("context/guidelines/DUPLICATE.md", duplicates[0]["path"])


if __name__ == "__main__":
    unittest.main()
