from __future__ import annotations

import json
import os
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTEXTKIT = REPO_ROOT / "bin" / "contextkit"


class MemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        initialized = self.run_cli("init", "--with-layers", "--json")
        self.assertEqual(initialized.returncode, 0, initialized.stderr)

    def run_cli(
        self,
        *args: str,
        stdin: str | None = None,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        merged_env = dict(os.environ)
        if env:
            merged_env.update(env)
        return subprocess.run(
            [str(CONTEXTKIT), *args],
            cwd=self.project,
            env=merged_env,
            input=stdin,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_init_adopt_and_bootstrap_do_not_create_empty_memory(self) -> None:
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

    @staticmethod
    def context_file(body: str) -> str:
        return (
            "---\n"
            "title: Project Rule\n"
            "description: Always load for the stable rule used by this memory test.\n"
            "load: inline\n"
            "order: 10\n"
            "---\n\n"
            "# Project Rule\n\n"
            f"{body}\n"
        )

    def test_memory_is_absent_until_first_add_and_context_is_canonical(self) -> None:
        self.assertFalse((self.project / "memory").exists())

        status = self.run_cli("memory", "status", "--json")
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertFalse(json.loads(status.stdout)["present"])

        empty_context = self.run_cli("memory", "context", "--json")
        self.assertEqual(empty_context.returncode, 0, empty_context.stderr)
        self.assertEqual(json.loads(empty_context.stdout)["context"], "")
        self.assertFalse((self.project / "memory").exists())

        added = self.run_cli(
            "memory", "add", "A provisional constraint must survive into the next agent session.",
            "--title", "Session constraint", "--json",
        )
        self.assertEqual(added.returncode, 0, added.stderr)
        added_result = json.loads(added.stdout)
        self.assertEqual(added_result["status"], "created")
        memory_file = self.project / added_result["path"]
        self.assertTrue(memory_file.is_file())
        self.assertEqual(memory_file.parent, self.project / "memory")

        context = self.run_cli("memory", "context")
        self.assertEqual(context.returncode, 0, context.stderr)
        self.assertIn("# Project Memory", context.stdout)
        self.assertIn("A provisional constraint must survive", context.stdout)
        self.assertNotIn("contextkit-memory-id", context.stdout)

        for target in [
            self.project / ".codex" / "generated" / "context.md",
            self.project / ".claude" / "rules" / "CONTEXT.md",
        ]:
            generated = target.read_text()
            self.assertIn(context.stdout.strip(), generated)
            self.assertLess(generated.index("# Project Memory"), generated.index("# Inline Context"))

        duplicate = self.run_cli(
            "memory", "add", "A provisional constraint must survive into the next agent session.", "--json",
        )
        self.assertEqual(duplicate.returncode, 0, duplicate.stderr)
        self.assertEqual(json.loads(duplicate.stdout)["status"], "skipped")
        self.assertEqual(memory_file.read_text().count("A provisional constraint must survive"), 1)

    def test_recursive_memory_search_status_and_audit(self) -> None:
        nested = self.project / "memory" / "imports" / "claude" / "notes.md"
        nested.parent.mkdir(parents=True)
        nested.write_text("# Imported\n\nThe cobalt deployment observation remains provisional for the next review.\n")

        build = self.run_cli("build", "--target", "all")
        self.assertEqual(build.returncode, 0, build.stderr)
        generated = (self.project / ".codex" / "generated" / "context.md").read_text()
        self.assertIn("## Memory Source: `memory/imports/claude/notes.md`", generated)
        self.assertIn("The cobalt deployment observation", generated)

        search = self.run_cli("memory", "search", "COBALT", "--json")
        self.assertEqual(search.returncode, 0, search.stderr)
        matches = json.loads(search.stdout)["matches"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["path"], "memory/imports/claude/notes.md")

        status = self.run_cli("memory", "status", "--json")
        self.assertEqual(status.returncode, 0, status.stderr)
        report = json.loads(status.stdout)
        self.assertTrue(report["present"])
        self.assertEqual(report["files"], 1)

        audit = self.run_cli("audit", "--json")
        self.assertEqual(audit.returncode, 0, audit.stderr)
        self.assertEqual(json.loads(audit.stdout)["findings"], [])

    def test_environment_memory_directory_survives_project_redeployment(self) -> None:
        persistent = self.root / "persistent-memory"
        memory_env = {"CONTEXTKIT_MEMORY_DIR": str(persistent)}
        added = self.run_cli(
            "memory", "add", "The persistent deployment observation must survive project replacement.", "--json",
            env=memory_env,
        )
        self.assertEqual(added.returncode, 0, added.stderr)
        result = json.loads(added.stdout)
        self.assertTrue(result["path"].startswith("$CONTEXTKIT_MEMORY_DIR/"))
        self.assertEqual(result["memory_directory"], str(persistent.resolve()))
        self.assertFalse((self.project / "memory").exists())
        self.assertEqual(len(list(persistent.glob("*.md"))), 1)

        generated = (self.project / ".codex" / "generated" / "context.md").read_text()
        self.assertNotIn("- Project memory: `$CONTEXTKIT_MEMORY_DIR`", generated)
        self.assertIn("## Memory Source: `$CONTEXTKIT_MEMORY_DIR/", generated)
        self.assertNotIn(str(persistent), generated)

        redeployed = self.root / "redeployed-project"
        redeployed.mkdir()
        initialized = subprocess.run(
            [str(CONTEXTKIT), "init", "--with-layers"],
            cwd=redeployed,
            env={**os.environ, **memory_env},
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        rebuilt = subprocess.run(
            [str(CONTEXTKIT), "build", "--target", "codex"],
            cwd=redeployed,
            env={**os.environ, **memory_env},
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(rebuilt.returncode, 0, rebuilt.stderr)
        redeployed_context = (redeployed / ".codex" / "generated" / "context.md").read_text()
        self.assertIn("The persistent deployment observation", redeployed_context)

        status = self.run_cli("memory", "status", "--json", env=memory_env)
        status_result = json.loads(status.stdout)
        self.assertTrue(status_result["external"])
        self.assertEqual(status_result["source"], "$CONTEXTKIT_MEMORY_DIR")
        self.assertEqual(status_result["directory"], str(persistent.resolve()))

    def test_environment_memory_directory_cannot_overlap_project_layers(self) -> None:
        for relative in ["context", "assets/persistent-memory", ".codex"]:
            with self.subTest(relative=relative):
                status = self.run_cli(
                    "memory", "status", "--json",
                    env={"CONTEXTKIT_MEMORY_DIR": relative},
                )
                self.assertEqual(status.returncode, 6)
                self.assertIn("overlaps", status.stderr)
        self.assertFalse((self.project / "memory").exists())

    def test_import_plan_is_read_only_and_apply_converges(self) -> None:
        source = self.root / "provider-memory"
        (source / "nested").mkdir(parents=True)
        original = "# Provider Note\n\nKeep this Markdown byte-for-byte.\n"
        (source / "nested" / "note.md").write_text(original)
        (source / "ignored.txt").write_text("not imported")

        plan = self.run_cli(
            "memory", "import", str(source), "--provider", "claude", "--plan", "--json",
        )
        self.assertEqual(plan.returncode, 0, plan.stderr)
        plan_result = json.loads(plan.stdout)
        self.assertEqual([item["status"] for item in plan_result["entries"]], ["create"])
        self.assertFalse((self.project / "memory").exists())

        applied = self.run_cli(
            "memory", "import", str(source), "--provider", "claude", "--apply", "--json",
        )
        self.assertEqual(applied.returncode, 0, applied.stderr)
        destination = self.project / "memory" / "imports" / "claude" / "nested" / "note.md"
        self.assertEqual(destination.read_text(), original)
        self.assertFalse((destination.parent / "ignored.txt").exists())

        repeated = self.run_cli(
            "memory", "import", str(source), "--provider", "claude", "--apply", "--json",
        )
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        repeated_result = json.loads(repeated.stdout)
        self.assertEqual(repeated_result["created"], [])
        self.assertEqual(repeated_result["skipped"], ["memory/imports/claude/nested/note.md"])

        destination.write_text("# Local Review\n\nPreserve this conflicting project copy.\n")
        conflict = self.run_cli(
            "memory", "import", str(source), "--provider", "claude", "--apply", "--json",
        )
        self.assertEqual(conflict.returncode, 6)
        self.assertIn("blocked by destination conflicts", conflict.stderr)
        self.assertIn("Preserve this conflicting project copy", destination.read_text())

    def test_audit_reports_empty_memory_directory_as_noise(self) -> None:
        (self.project / "memory").mkdir()
        audit = self.run_cli("audit", "--json")
        self.assertEqual(audit.returncode, 0, audit.stderr)
        findings = json.loads(audit.stdout)["findings"]
        self.assertEqual([item["code"] for item in findings], ["empty-memory-layer"])
        self.assertEqual(findings[0]["rule_source"], "contextkit guide memory")

    def test_audit_does_not_emit_memory_semantic_duplicate_findings(self) -> None:
        claim = "Every release candidate preserves this exact durable operational constraint before any production deployment begins"
        context_path = self.project / "context" / "guidelines" / "RELEASE.md"
        context_path.parent.mkdir(parents=True)
        context_path.write_text(self.context_file(claim + "."))
        memory_root = self.project / "memory"
        memory_root.mkdir()
        (memory_root / "note.md").write_text("# Note\n\n" + claim + ".\n")
        (memory_root / "duplicate.md").write_text("# Duplicate\n\n" + claim + ".\n")

        audit = self.run_cli("audit", "--json")
        self.assertEqual(audit.returncode, 0, audit.stderr)
        findings = json.loads(audit.stdout)["findings"]
        removed_semantic_codes = {"memory-duplicates-live-fact", "duplicate-memory-claim"}
        self.assertTrue(removed_semantic_codes.isdisjoint(item["code"] for item in findings))

    def test_bootstrap_uses_memory_audit_findings(self) -> None:
        subprocess.run(["git", "init"], cwd=self.project, text=True, capture_output=True, check=True)
        memory_path = self.project / "memory" / "unexpected.txt"
        memory_path.parent.mkdir()
        memory_path.write_text("This file type is not compiled into project memory.\n")

        bootstrapped = self.run_cli("bootstrap", "--yes", "--json")
        self.assertEqual(bootstrapped.returncode, 0, bootstrapped.stderr)
        result = json.loads(bootstrapped.stdout)
        self.assertFalse(result["ready"])
        codes = [item["code"] for item in result["audit"]["findings"]]
        self.assertIn("uncompiled-memory-file", codes)

    def test_new_claude_settings_disable_auto_memory_without_touching_codex_memory(self) -> None:
        installed = self.run_cli("install-hooks", "--target", "claude", "--target", "codex", "--json")
        self.assertEqual(installed.returncode, 0, installed.stderr)
        result = json.loads(installed.stdout)
        self.assertTrue(result["claude"]["auto_memory_disabled"])
        claude_settings = json.loads((self.project / ".claude" / "settings.json").read_text())
        self.assertIs(claude_settings["autoMemoryEnabled"], False)
        codex_config = (self.project / ".codex" / "config.toml").read_text()
        self.assertNotIn("memory", codex_config.casefold())

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

    def test_codex_settings_are_inserted_before_existing_toml_tables(self) -> None:
        config = self.project / ".codex" / "config.toml"
        config.parent.mkdir()
        config.write_text("[features]\nexperimental = true\n")

        installed = self.run_cli("install-hooks", "--target", "codex", "--json")
        self.assertEqual(installed.returncode, 0, installed.stderr)
        parsed = tomllib.loads(config.read_text())
        self.assertEqual(parsed["project_doc_fallback_filenames"], [".codex/generated/context.md"])
        self.assertEqual(parsed["project_doc_max_bytes"], 131072)
        self.assertEqual(parsed["features"], {"experimental": True})
        self.assertLess(config.read_text().index("project_doc_max_bytes"), config.read_text().index("[features]"))

    def test_nested_codex_context_limit_is_preserved_and_blocked(self) -> None:
        config = self.project / ".codex" / "config.toml"
        config.parent.mkdir()
        original = "[features]\nproject_doc_max_bytes = 131072\n"
        config.write_text(original)

        installed = self.run_cli("install-hooks", "--target", "codex", "--json")
        self.assertEqual(installed.returncode, 6)
        self.assertIn("must be top-level", installed.stderr)
        self.assertEqual(config.read_text(), original)
        self.assertFalse((self.project / ".codex" / "hooks" / "build-context.sh").exists())

        built = self.run_cli("build", "--target", "codex")
        self.assertEqual(built.returncode, 6)
        self.assertIn("must be top-level", built.stderr)

    def test_memory_paths_cannot_escape_through_symlinks(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        (self.project / "memory").symlink_to(outside, target_is_directory=True)

        added = self.run_cli("memory", "add", "This must remain inside the configured memory tree.")
        self.assertEqual(added.returncode, 6)
        self.assertIn("must not be a symlink", added.stderr)
        self.assertEqual(list(outside.iterdir()), [])

        built = self.run_cli("build", "--target", "codex")
        self.assertEqual(built.returncode, 6)
        context = self.run_cli("memory", "context")
        self.assertEqual(context.returncode, 6)

        audit = self.run_cli("audit", "--json")
        self.assertEqual(audit.returncode, 0, audit.stderr)
        self.assertEqual(json.loads(audit.stdout)["findings"][0]["code"], "memory-symlink")

    def test_broken_project_memory_symlink_is_never_treated_as_absent(self) -> None:
        missing = self.root / "missing-memory-target"
        (self.project / "memory").symlink_to(missing, target_is_directory=True)

        status = self.run_cli("memory", "status", "--json")
        self.assertEqual(status.returncode, 6)
        self.assertIn("must not be a symlink", status.stderr)

        built = self.run_cli("build", "--target", "codex")
        self.assertEqual(built.returncode, 6)
        self.assertIn("must not be a symlink", built.stderr)

        audit = self.run_cli("audit", "--json")
        self.assertEqual(audit.returncode, 0, audit.stderr)
        findings = json.loads(audit.stdout)["findings"]
        self.assertEqual([item["code"] for item in findings], ["memory-symlink"])

    def test_import_rejects_symlinked_destination_components(self) -> None:
        source = self.root / "source-memory"
        source.mkdir()
        (source / "note.md").write_text("# Source\n\nImported note.\n")
        outside = self.root / "outside-import"
        outside.mkdir()
        memory = self.project / "memory"
        memory.mkdir()
        (memory / "imports").symlink_to(outside, target_is_directory=True)

        imported = self.run_cli(
            "memory", "import", str(source), "--provider", "claude", "--apply", "--json",
        )
        self.assertEqual(imported.returncode, 6)
        self.assertIn("must not be symlinks", imported.stderr)
        self.assertEqual(list(outside.iterdir()), [])

    def test_codex_build_blocks_before_silent_context_truncation(self) -> None:
        installed = self.run_cli("install-hooks", "--target", "codex", "--json")
        self.assertEqual(installed.returncode, 0, installed.stderr)
        large_note = "x" * 140000

        added = self.run_cli("memory", "add", "--stdin", stdin=large_note)
        self.assertEqual(added.returncode, 6)
        self.assertIn("project_doc_max_bytes is 131072", added.stderr)
        self.assertIn("will not write a target that Codex may truncate", added.stderr)
        self.assertTrue(any((self.project / "memory").glob("*.md")))

        rendered = self.run_cli("memory", "context")
        self.assertEqual(rendered.returncode, 0, rendered.stderr)
        self.assertGreater(len(rendered.stdout), 140000)


if __name__ == "__main__":
    unittest.main()
