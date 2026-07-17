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
            self.assertNotIn(f"- Global context: `{resolved_global}`", generated)
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

    def test_global_context_init_is_explicit_convergent_and_valid(self) -> None:
        destination = self.root / "initialized-global-context"
        config = self.project / ".contextkit" / "config.toml"
        original_config = config.read_bytes()

        initialized = self.run_cli("global-context", "init", str(destination), "--json")
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        result = json.loads(initialized.stdout)
        starter = destination / "GLOBAL-CONTEXT.md"
        self.assertEqual(result["global_context"], str(destination.resolve()))
        self.assertEqual(result["created"], [str(destination.resolve()), str(starter.resolve())])
        self.assertEqual(result["skipped"], [])
        self.assertEqual(result["guide"], "contextkit guide global-context")
        self.assertEqual(config.read_bytes(), original_config)
        first_body = starter.read_bytes()
        self.assertIn(b"load: stub", first_body)
        self.assertNotIn(str(destination).encode(), first_body)

        audit = self.run_cli("audit-file", str(starter), "--json")
        self.assertEqual(audit.returncode, 0, audit.stderr)
        self.assertEqual(json.loads(audit.stdout)["findings"], [])

        rerun = self.run_cli("global-context", "init", str(destination), "--json")
        self.assertEqual(rerun.returncode, 0, rerun.stderr)
        rerun_result = json.loads(rerun.stdout)
        self.assertEqual(rerun_result["created"], [])
        self.assertEqual(rerun_result["skipped"], [str(destination.resolve()), str(starter.resolve())])
        self.assertEqual(starter.read_bytes(), first_body)
        self.assertEqual(config.read_bytes(), original_config)

    def test_global_context_init_preserves_existing_starter_and_project_templates_exclude_it(self) -> None:
        destination = self.root / "existing-global-context"
        destination.mkdir()
        starter = destination / "GLOBAL-CONTEXT.md"
        existing = b"personal global context\n"
        starter.write_bytes(existing)

        initialized = self.run_cli("global-context", "init", str(destination), "--json")
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        result = json.loads(initialized.stdout)
        self.assertEqual(result["created"], [])
        self.assertEqual(result["skipped"], [str(destination.resolve()), str(starter.resolve())])
        self.assertEqual(starter.read_bytes(), existing)

        project = self.root / "template-project"
        project.mkdir()
        template_init = subprocess.run(
            [str(CONTEXTKIT), "init", "--with-template", "--json"],
            cwd=project,
            env=dict(os.environ),
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(template_init.returncode, 0, template_init.stderr)
        self.assertFalse((project / "global-context" / "GLOBAL-CONTEXT.md").exists())

    def test_global_context_init_rejects_active_project_root_without_mutation(self) -> None:
        config = self.project / ".contextkit" / "config.toml"
        body = self.project / "context" / "preserve.txt"
        body.write_bytes(b"preserve project body\n")
        original_config = config.read_bytes()
        original_body = body.read_bytes()

        initialized = self.run_cli("global-context", "init", ".", "--json")
        self.assertEqual(initialized.returncode, 6)
        self.assertIn("overlaps the active ContextKit project", initialized.stderr)
        self.assertFalse((self.project / "GLOBAL-CONTEXT.md").exists())
        self.assertEqual(config.read_bytes(), original_config)
        self.assertEqual(body.read_bytes(), original_body)

    def test_global_context_init_rejects_destination_inside_active_project_without_mutation(self) -> None:
        destination = self.project / "shared-context"
        config = self.project / ".contextkit" / "config.toml"
        original_config = config.read_bytes()

        initialized = self.run_cli("global-context", "init", str(destination), "--json")
        self.assertEqual(initialized.returncode, 6)
        self.assertIn("overlaps the active ContextKit project", initialized.stderr)
        self.assertFalse(destination.exists())
        self.assertEqual(config.read_bytes(), original_config)

    def test_global_context_init_rejects_destination_containing_active_project_without_mutation(self) -> None:
        destination = self.root
        config = self.project / ".contextkit" / "config.toml"
        original_config = config.read_bytes()

        initialized = self.run_cli("global-context", "init", str(destination), "--json")
        self.assertEqual(initialized.returncode, 6)
        self.assertIn("overlaps the active ContextKit project", initialized.stderr)
        self.assertFalse((destination / "GLOBAL-CONTEXT.md").exists())
        self.assertEqual(config.read_bytes(), original_config)

    def test_global_context_init_rejects_destination_inside_another_managed_project(self) -> None:
        managed = self.root / "other-project"
        managed.mkdir()
        initialized_project = subprocess.run(
            [str(CONTEXTKIT), "init", "--json"],
            cwd=managed,
            env=dict(os.environ),
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(initialized_project.returncode, 0, initialized_project.stderr)
        config = managed / ".contextkit" / "config.toml"
        original_config = config.read_bytes()
        destination = managed / "shared-context"
        standalone = self.root / "standalone"
        standalone.mkdir()

        initialized = subprocess.run(
            [str(CONTEXTKIT), "global-context", "init", str(destination), "--json"],
            cwd=standalone,
            env=dict(os.environ),
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(initialized.returncode, 6)
        self.assertIn("inside a ContextKit-managed project", initialized.stderr)
        self.assertFalse(destination.exists())
        self.assertEqual(config.read_bytes(), original_config)

    def test_global_context_init_allows_standalone_destination(self) -> None:
        standalone = self.root / "standalone-project"
        standalone.mkdir()
        destination = self.root / "standalone-global-context"

        initialized = subprocess.run(
            [str(CONTEXTKIT), "global-context", "init", str(destination), "--json"],
            cwd=standalone,
            env=dict(os.environ),
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        result = json.loads(initialized.stdout)
        self.assertEqual(result["global_context"], str(destination.resolve()))
        self.assertTrue((destination / "GLOBAL-CONTEXT.md").is_file())

    def test_global_context_init_allows_existing_ordinary_repository(self) -> None:
        destination = self.root / "ordinary-repository"
        destination.mkdir()
        (destination / ".git").mkdir()
        marker = destination / "README.md"
        marker.write_bytes(b"ordinary repository\n")
        standalone = self.root / "standalone-ordinary-check"
        standalone.mkdir()

        initialized = subprocess.run(
            [str(CONTEXTKIT), "global-context", "init", str(destination), "--json"],
            cwd=standalone,
            env=dict(os.environ),
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        self.assertEqual(marker.read_bytes(), b"ordinary repository\n")
        self.assertTrue((destination / "GLOBAL-CONTEXT.md").is_file())

    def test_global_context_init_rejects_existing_parent_containing_managed_project_without_mutation(self) -> None:
        destination = self.root / "shared-parent"
        managed = destination / "neighbor-project"
        managed.mkdir(parents=True)
        initialized_project = subprocess.run(
            [str(CONTEXTKIT), "init", "--with-layers", "--json"],
            cwd=managed,
            env=dict(os.environ),
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(initialized_project.returncode, 0, initialized_project.stderr)
        config = managed / ".contextkit" / "config.toml"
        body = managed / "context" / "preserve.txt"
        body.write_bytes(b"preserve nested project body\n")
        original_config = config.read_bytes()
        original_body = body.read_bytes()
        standalone = self.root / "standalone-parent-check"
        standalone.mkdir()

        initialized = subprocess.run(
            [str(CONTEXTKIT), "global-context", "init", str(destination), "--json"],
            cwd=standalone,
            env=dict(os.environ),
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(initialized.returncode, 6)
        self.assertIn("contains a ContextKit-managed project", initialized.stderr)
        self.assertFalse((destination / "GLOBAL-CONTEXT.md").exists())
        self.assertEqual(config.read_bytes(), original_config)
        self.assertEqual(body.read_bytes(), original_body)

    def test_global_context_init_rejects_directory_starter_without_mutation(self) -> None:
        destination = self.root / "directory-starter-collision"
        starter = destination / "GLOBAL-CONTEXT.md"
        starter.mkdir(parents=True)
        marker = starter / "preserve.txt"
        marker.write_bytes(b"preserve directory contents\n")
        before = marker.read_bytes()

        initialized = self.run_cli("global-context", "init", str(destination), "--json")
        self.assertEqual(initialized.returncode, 6)
        self.assertIn("must be a regular file", initialized.stderr)
        self.assertTrue(starter.is_dir())
        self.assertEqual(marker.read_bytes(), before)
        self.assertEqual(list(destination.iterdir()), [starter])

    def test_global_context_init_rejects_symlink_starters_without_mutation(self) -> None:
        target = self.root / "personal-global-context.md"
        target.write_bytes(b"preserve symlink target\n")
        dangling_target = self.root / "missing-global-context.md"
        destinations = [
            (self.root / "regular-symlink-collision", target),
            (self.root / "dangling-symlink-collision", dangling_target),
        ]
        try:
            for destination, link_target in destinations:
                destination.mkdir()
                (destination / "GLOBAL-CONTEXT.md").symlink_to(link_target)
        except (NotImplementedError, OSError) as exc:
            self.skipTest(f"symlinks are unavailable: {exc}")

        for destination, link_target in destinations:
            with self.subTest(destination=destination.name):
                starter = destination / "GLOBAL-CONTEXT.md"
                original_link = starter.readlink()
                initialized = self.run_cli("global-context", "init", str(destination), "--json")
                self.assertEqual(initialized.returncode, 6)
                self.assertIn("must be a regular file", initialized.stderr)
                self.assertTrue(starter.is_symlink())
                self.assertEqual(starter.readlink(), original_link)
                self.assertEqual(list(destination.iterdir()), [starter])

        self.assertEqual(target.read_bytes(), b"preserve symlink target\n")
        self.assertFalse(dangling_target.exists())

    def test_global_context_init_rejects_destination_symlinks_without_mutation(self) -> None:
        target = self.root / "existing-global-context-target"
        target.mkdir()
        marker = target / "preserve.txt"
        marker.write_bytes(b"preserve destination target\n")
        dangling_target = self.root / "missing-global-context-target"
        destinations = [
            (self.root / "existing-destination-link", target),
            (self.root / "dangling-destination-link", dangling_target),
        ]
        try:
            destinations[0][0].symlink_to(target, target_is_directory=True)
            destinations[1][0].symlink_to(dangling_target, target_is_directory=True)
        except (NotImplementedError, OSError) as exc:
            self.skipTest(f"symlinks are unavailable: {exc}")

        for destination, link_target in destinations:
            with self.subTest(destination=destination.name):
                original_link = destination.readlink()
                initialized = self.run_cli("global-context", "init", str(destination), "--json")
                self.assertEqual(initialized.returncode, 6)
                self.assertIn("destination must not be a symlink", initialized.stderr)
                self.assertTrue(destination.is_symlink())
                self.assertEqual(destination.readlink(), original_link)
                self.assertEqual(original_link, link_target)

        self.assertEqual(marker.read_bytes(), b"preserve destination target\n")
        self.assertEqual(list(target.iterdir()), [marker])
        self.assertFalse(dangling_target.exists())

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

    def test_audit_does_not_emit_content_semantic_findings(self) -> None:
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
            repeated_claim + " Formerly this runtime container deployment used different service architecture; pending work follows assets/sessions/example.md.",
        ))

        audit = self.run_cli("audit", "--json")
        self.assertEqual(audit.returncode, 0, audit.stderr)
        findings = json.loads(audit.stdout)["findings"]
        removed_semantic_codes = {
            "asset-as-live-doctrine",
            "taxonomy-fit",
            "historical-framing",
            "running-state-in-context",
            "duplicate-live-fact",
        }
        self.assertTrue(removed_semantic_codes.isdisjoint(item["code"] for item in findings))

    def test_internal_context_link_routes_to_live_semantic_discovery(self) -> None:
        linked = self.project / "context" / "guidelines" / "LINKED.md"
        linked.parent.mkdir()
        linked.write_text(self.context_file(
            "Linked Procedure",
            "Load when work needs a procedure that may have an available owner.",
            "stub",
            20,
            "Use the [transfer routine](../../routines/transfer.md).",
        ))

        audit = self.run_cli("audit", "--json")
        self.assertEqual(audit.returncode, 0, audit.stderr)
        finding = next(item for item in json.loads(audit.stdout)["findings"] if item["code"] == "internal-context-link")
        self.assertEqual(finding["rule_source"], "contextkit guide authoring")
        self.assertIn("capability, procedure, or knowledge needed", finding["hint"])
        self.assertIn("discover an available owner at use time", finding["hint"])
        self.assertIn("fallback, stop, or escalation path", finding["hint"])


if __name__ == "__main__":
    unittest.main()
