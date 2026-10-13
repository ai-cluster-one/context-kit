from __future__ import annotations

import json
import os
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

import codex_home  # noqa: F401  (isolates the Codex user config)


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTEXTKIT = REPO_ROOT / "bin" / "contextkit"


class MemoryRemovalTests(unittest.TestCase):
    """Project memory belongs to the `memory` capability; ContextKit only routes a leftover folder to it."""

    WARNING = (
        "legacy memory folder `memory/`: ContextKit does not compile project memory; "
        "run `memory adopt` to carry it into the `memory` capability"
    )

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.fragment = self.root / "fragment.md"
        self.fragment.write_text("# Capabilities\n")
        self.manager = self.root / "capabilities"
        self.manager.write_text('#!/bin/sh\ncat "$STUB_FRAGMENT"\n')
        self.manager.chmod(0o755)
        initialized = self.run_cli("init", "--with-layers", "--json")
        self.assertEqual(initialized.returncode, 0, initialized.stderr)

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env.update({"CAPABILITIES_MANAGER": str(self.manager), "STUB_FRAGMENT": str(self.fragment)})
        return subprocess.run(
            [str(CONTEXTKIT), *args],
            cwd=self.project, env=env, text=True, capture_output=True, check=False,
        )

    def write_memory(self) -> None:
        memory = self.project / "memory"
        memory.mkdir(exist_ok=True)
        (memory / "2026-10-13.md").write_text("# 2026-10-13\n\n## Note\n\nThe amber release window stays provisional.\n")

    def build(self) -> tuple[dict, str]:
        built = self.run_cli("build", "--json")
        self.assertEqual(built.returncode, 0, built.stderr)
        return json.loads(built.stdout), (self.project / ".contextkit" / "generated" / "context.md").read_text()

    def test_init_adopt_and_bootstrap_create_no_memory_folder(self) -> None:
        self.assertFalse((self.project / "memory").exists())
        adopted = self.run_cli("adopt", "--with-layers", "--json")
        self.assertEqual(adopted.returncode, 0, adopted.stderr)
        self.assertFalse((self.project / "memory").exists())

        fresh = self.root / "fresh"
        fresh.mkdir()
        bootstrapped = subprocess.run(
            [str(CONTEXTKIT), "bootstrap", "--yes", "--json"],
            cwd=fresh,
            env=dict(os.environ),
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(bootstrapped.returncode, 0, bootstrapped.stderr)
        self.assertFalse((fresh / "memory").exists())

    def test_memory_is_no_command_layer_or_guide(self) -> None:
        for args in (("memory", "add", "A note."), ("memory", "status")):
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertEqual(result.returncode, 2)
                self.assertIn("invalid choice: 'memory'", result.stderr)
        help_text = self.run_cli("help").stdout
        self.assertNotIn("contextkit memory", help_text)
        self.assertNotIn("CONTEXTKIT_MEMORY_DIR", help_text)
        self.assertNotIn("|memory|", help_text)
        self.assertEqual(self.run_cli("path", "memory").returncode, 2)
        guide = self.run_cli("guide", "memory")
        self.assertIn("unknown guide topic: memory", guide.stderr)
        self.assertFalse((REPO_ROOT / "guides" / "memory.md").exists())

    def test_a_memory_folder_is_never_compiled_and_build_warns_without_failing(self) -> None:
        result, generated = self.build()
        self.assertEqual(result["warnings"], [])
        self.assertNotIn("legacy memory folder", generated)

        self.write_memory()
        result, generated = self.build()
        self.assertEqual(result["warnings"], [self.WARNING])
        self.assertIn(f"- {self.WARNING}", generated)
        self.assertNotIn("# Project Memory", generated)
        self.assertNotIn("The amber release window", generated)
        self.assertNotIn("contextkit memory add", generated)
        self.assertNotIn("contextkit guide memory", generated)

    def test_audit_warns_on_a_memory_folder_and_routes_to_memory_adopt(self) -> None:
        clean = self.run_cli("audit", "--json")
        self.assertEqual(clean.returncode, 0, clean.stderr)
        self.assertEqual(json.loads(clean.stdout)["findings"], [])

        self.write_memory()
        (self.project / "memory" / "notes.txt").write_text("not Markdown\n")
        audit = self.run_cli("audit", "--json")
        self.assertEqual(audit.returncode, 0, audit.stderr)
        findings = json.loads(audit.stdout)["findings"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["code"], "legacy-memory-folder")
        self.assertEqual(findings[0]["severity"], "warning")
        self.assertEqual(findings[0]["path"], "memory")
        self.assertIn("`memory adopt`", findings[0]["hint"])
        report = self.run_cli("audit")
        self.assertEqual(report.returncode, 0, report.stderr)
        self.assertIn("### WARNING `legacy-memory-folder`", report.stdout)

    def test_audit_file_judges_a_memory_file_as_no_memory_layer(self) -> None:
        self.write_memory()
        audited = self.run_cli("audit-file", "memory/2026-10-13.md", "--json")
        self.assertEqual(audited.returncode, 0, audited.stderr)
        codes = {item["code"] for item in json.loads(audited.stdout)["findings"]}
        self.assertFalse([code for code in codes if "memory" in code], codes)

    def test_a_memory_folder_does_not_change_bootstrap_readiness(self) -> None:
        subprocess.run(["git", "init"], cwd=self.project, text=True, capture_output=True, check=True)
        self.write_memory()
        bootstrapped = self.run_cli("bootstrap", "--yes", "--json")
        self.assertEqual(bootstrapped.returncode, 0, bootstrapped.stderr)
        result = json.loads(bootstrapped.stdout)
        self.assertEqual([item["code"] for item in result["audit"]["findings"]], ["legacy-memory-folder"])
        self.assertEqual(result["ready"], result["doctor"]["ok"])
        self.assertTrue(result["ready"])

    def test_no_shipped_surface_routes_to_contextkit_memory(self) -> None:
        shipped = [REPO_ROOT / "README.md", REPO_ROOT / "THESIS.md"]
        for folder in ("bundle", "guides", "templates"):
            shipped += sorted((REPO_ROOT / folder).rglob("*.md"))
        for path in shipped:
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                text = path.read_text()
                self.assertNotIn("contextkit memory", text)
                self.assertNotIn("contextkit guide memory", text)
                self.assertNotIn("CONTEXTKIT_MEMORY_DIR", text)

    def test_new_claude_settings_disable_auto_memory_without_touching_codex_memory(self) -> None:
        installed = self.run_cli("install-hooks", "--target", "claude", "--target", "codex", "--json")
        self.assertEqual(installed.returncode, 0, installed.stderr)
        result = json.loads(installed.stdout)
        self.assertTrue(result["claude"]["auto_memory_disabled"])
        claude_settings = json.loads((self.project / ".claude" / "settings.json").read_text())
        self.assertIs(claude_settings["autoMemoryEnabled"], False)
        codex_config = tomllib.loads((self.project / ".codex" / "config.toml").read_text())
        self.assertEqual(set(codex_config), {"project_doc_fallback_filenames", "project_doc_max_bytes"})

    def test_existing_claude_memory_policy_is_preserved(self) -> None:
        settings_path = self.project / ".claude" / "settings.json"
        settings_path.parent.mkdir()
        settings_path.write_text(json.dumps({"autoMemoryEnabled": True, "custom": {"keep": "yes"}}))

        installed = self.run_cli("install-hooks", "--target", "claude", "--json")
        self.assertEqual(installed.returncode, 0, installed.stderr)
        result = json.loads(installed.stdout)
        self.assertFalse(result["claude"]["auto_memory_disabled"])
        settings = json.loads(settings_path.read_text())
        self.assertIs(settings["autoMemoryEnabled"], True)
        self.assertEqual(settings["custom"], {"keep": "yes"})
        self.assertIn("SessionStart", settings["hooks"])

    def test_invalid_existing_claude_settings_are_never_overwritten(self) -> None:
        settings_path = self.project / ".claude" / "settings.json"
        settings_path.parent.mkdir()
        settings_path.write_text("true\n")

        installed = self.run_cli("install-hooks", "--target", "claude", "--json")
        self.assertEqual(installed.returncode, 6)
        self.assertIn("must be a valid JSON object", installed.stderr)
        self.assertEqual(settings_path.read_text(), "true\n")

        combined = self.run_cli("install-hooks", "--target", "codex", "--target", "claude", "--json")
        self.assertEqual(combined.returncode, 6)
        self.assertFalse((self.project / ".codex" / "config.toml").exists())
        self.assertFalse((self.project / ".codex" / "hooks" / "build-context.sh").exists())

    def test_incompatible_nested_claude_hook_shape_is_preserved_and_blocked(self) -> None:
        settings_path = self.project / ".claude" / "settings.json"
        settings_path.parent.mkdir()
        invalid_shapes = [
            {"hooks": [], "custom": "keep"},
            {"hooks": None, "custom": "keep"},
            {"hooks": {"SessionStart": None}, "custom": "keep"},
            {"hooks": {"SessionStart": [{"hooks": None}]}, "custom": "keep"},
        ]
        for payload in invalid_shapes:
            with self.subTest(payload=payload):
                original = json.dumps(payload) + "\n"
                settings_path.write_text(original)
                installed = self.run_cli("install-hooks", "--target", "claude", "--json")
                self.assertEqual(installed.returncode, 6)
                self.assertNotIn("Traceback", installed.stderr)
                self.assertEqual(settings_path.read_text(), original)

    def test_existing_codex_config_is_left_to_its_owner(self) -> None:
        config = self.project / ".codex" / "config.toml"
        config.parent.mkdir()
        original = "project_doc_max_bytes = 131072\n\n[features]\nexperimental = true\n"
        config.write_text(original)

        installed = self.run_cli("install-hooks", "--target", "codex", "--json")
        self.assertEqual(installed.returncode, 0, installed.stderr)
        parsed = tomllib.loads(config.read_text())
        self.assertEqual(parsed["features"], {"experimental": True})
        self.assertEqual(set(parsed), {"features", "project_doc_fallback_filenames", "project_doc_max_bytes"})
        self.assertTrue(config.read_text().endswith("\n\n[features]\nexperimental = true\n"))


if __name__ == "__main__":
    unittest.main()
