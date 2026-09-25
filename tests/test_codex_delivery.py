from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

import codex_home  # noqa: F401  (isolates the Codex user config)


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTEXTKIT = REPO_ROOT / "bin" / "contextkit"
HOOK_COMMAND_NEEDLE = ".codex/hooks/build-context.sh"
OUTPUT = Path(".contextkit") / "generated" / "context.md"
CODEX_LINK = Path(".contextkit.md")
CLAUDE_LINK = Path(".claude") / "rules" / "CONTEXT.md"
MARKER = "MIDDLE-MARKER-4f2c"


def load_manager():
    name = "contextkit_codex_delivery_test_module"
    if name in sys.modules:
        return sys.modules[name]
    loader = importlib.machinery.SourceFileLoader(name, str(CONTEXTKIT))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


class CodexBindingCase(unittest.TestCase):
    """Fixture for a project whose Codex binding ContextKit owns."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / "project"
        self.project.mkdir()
        self.codex_home = self.root / "codex-home"
        self.codex_home.mkdir()
        subprocess.run(["git", "init", "-q", "."], cwd=self.project, check=True)
        initialized = self.run_cli("init", "--with-layers", "--json")
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        self.manager = self.project / ".contextkit" / "manager"
        self.manager.mkdir(parents=True, exist_ok=True)
        (self.manager / "contextkit").symlink_to(CONTEXTKIT)

    def env(self) -> dict[str, str]:
        return {**os.environ, "CODEX_HOME": str(self.codex_home)}

    def run_cli(self, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(CONTEXTKIT), *args],
            cwd=self.project,
            env=self.env(),
            input=stdin,
            text=True,
            capture_output=True,
            check=False,
        )

    def run_adapter(self, path_prefix: Path | None = None) -> subprocess.CompletedProcess[str]:
        env = self.env()
        if path_prefix is not None:
            env["PATH"] = f"{path_prefix}{os.pathsep}{env['PATH']}"
        return subprocess.run(
            ["/bin/bash", str(self.project / ".codex" / "hooks" / "build-context.sh")],
            cwd=self.project,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def install(self, *extra: str) -> dict:
        installed = self.run_cli("install-hooks", "--target", "codex", *extra, "--json")
        self.assertEqual(installed.returncode, 0, installed.stderr)
        return json.loads(installed.stdout)["codex"]

    def installed_hook(self) -> dict:
        hooks = json.loads((self.project / ".codex" / "hooks.json").read_text())
        return next(
            hook
            for entry in hooks["hooks"]["SessionStart"]
            for hook in entry["hooks"]
            if HOOK_COMMAND_NEEDLE in hook["command"]
        )

    def codex_problems(self) -> list[str]:
        report = json.loads(self.run_cli("doctor", "--json").stdout)
        return [p for p in report["problems"] if "Codex" in p or "codex" in p or ".contextkit.md" in p]

    def codex_user_config(self) -> dict:
        path = self.codex_home / "config.toml"
        return tomllib.loads(path.read_text()) if path.exists() else {}


class CodexDeliveryTests(CodexBindingCase):
    """Codex loads the generated context itself through the `.contextkit.md` project doc."""

    def test_install_links_the_generated_context_as_a_codex_project_doc(self) -> None:
        self.install()
        link = self.project / CODEX_LINK
        self.assertTrue(link.is_symlink())
        self.assertEqual(link.resolve(), (self.project / OUTPUT).resolve())
        self.assertIn("# Project Context", link.read_text())
        config = tomllib.loads((self.project / ".codex" / "config.toml").read_text())
        self.assertEqual(config["project_doc_fallback_filenames"], [".contextkit.md"])
        self.assertEqual(config["project_doc_max_bytes"], 524288)

    def test_the_hook_refreshes_without_delivering_the_context(self) -> None:
        self.install()
        hook = self.installed_hook()
        self.assertNotIn("additionalContextLimit", hook)
        self.assertNotIn("async", hook)
        entry = json.loads((self.project / ".codex" / "hooks.json").read_text())["hooks"]["SessionStart"][0]
        self.assertEqual(entry["matcher"], "startup|resume|clear")
        emitted = self.run_adapter()
        self.assertEqual(emitted.returncode, 0, emitted.stderr)
        self.assertEqual(emitted.stdout, "")

    def test_a_context_change_since_the_session_loaded_it_is_announced_once(self) -> None:
        self.install()
        added = self.run_cli("memory", "add", "fresh fact")
        self.assertEqual(added.returncode, 0, added.stderr)
        (self.project / "context" / "late.md").write_text(
            "---\ntitle: Late\ndescription: A context file written after the last build ran.\nload: inline\norder: 90\n---\n\n# Late\n"
        )
        emitted = self.run_adapter()
        self.assertEqual(emitted.returncode, 0, emitted.stderr)
        self.assertIn("# ContextKit Session Notice", emitted.stdout)
        self.assertIn("changed after this session loaded it", emitted.stdout)
        self.assertEqual(self.run_adapter().stdout, "")

    def test_a_root_agents_file_that_shadows_the_link_is_announced_and_reported(self) -> None:
        self.install()
        (self.project / "AGENTS.md").write_text("# Team notes\n")
        emitted = self.run_adapter()
        self.assertIn("did not load in this session", emitted.stdout)
        self.assertIn("root `AGENTS.md`", emitted.stdout)
        self.assertTrue(any("root `AGENTS.md`" in p for p in self.codex_problems()))

    def test_large_context_reaches_the_linked_file_whole(self) -> None:
        self.install()
        note = f"{'x' * 70000}\n{MARKER}\n{'y' * 70000}"
        added = self.run_cli("memory", "add", "--stdin", stdin=note)
        self.assertEqual(added.returncode, 0, added.stderr)
        linked = (self.project / CODEX_LINK).read_text()
        self.assertGreater(len(linked.encode()), 140000)
        self.assertIn(MARKER, linked)
        self.assertIn("y" * 70000, linked)
        self.assertEqual(self.codex_problems(), [])

    def test_a_context_beyond_the_codex_budget_is_reported(self) -> None:
        self.install()
        config = self.project / ".codex" / "config.toml"
        config.write_text(config.read_text().replace("524288", "1024"))
        problems = self.codex_problems()
        self.assertTrue(any("truncates project docs" in p for p in problems))

    def test_install_records_folder_and_hook_trust_for_headless_codex(self) -> None:
        result = self.install()
        self.assertEqual(len(result["trust"]["recorded"]), 2)
        config = self.codex_user_config()
        self.assertEqual(config["projects"][str(self.project)]["trust_level"], "trusted")
        key = f"{self.project / '.codex' / 'hooks.json'}:session_start:0:0"
        manager = load_manager()
        hook = self.installed_hook()
        self.assertEqual(
            config["hooks"]["state"][key]["trusted_hash"],
            manager._codex_hook_hash("startup|resume|clear", hook),
        )
        self.assertEqual(self.codex_problems(), [])
        again = self.install()
        self.assertEqual(again["trust"]["recorded"], [])

    def test_existing_codex_user_settings_survive_trust_recording(self) -> None:
        original = (
            'model = "gpt-test"\n\n'
            '[projects."/elsewhere"]\ntrust_level = "trusted"\n\n'
            "[hooks.state]\n\n"
            '[hooks.state."/elsewhere/.codex/hooks.json:session_start:0:0"]\n'
            'trusted_hash = "sha256:abc"\n'
        )
        (self.codex_home / "config.toml").write_text(original)
        self.install()
        text = (self.codex_home / "config.toml").read_text()
        self.assertTrue(text.startswith(original))
        config = tomllib.loads(text)
        self.assertEqual(config["model"], "gpt-test")
        self.assertEqual(config["projects"]["/elsewhere"], {"trust_level": "trusted"})
        self.assertEqual(config["projects"][str(self.project)], {"trust_level": "trusted"})

    def test_an_explicitly_untrusted_folder_stays_untrusted(self) -> None:
        (self.codex_home / "config.toml").write_text(f'[projects."{self.project}"]\ntrust_level = "untrusted"\n')
        result = self.install()
        self.assertIn("untrusted", result["trust"]["skipped"])
        self.assertEqual(self.codex_user_config()["projects"][str(self.project)]["trust_level"], "untrusted")
        self.assertTrue(any("marks this project folder untrusted" in p for p in self.codex_problems()))

    def test_no_trust_leaves_the_codex_user_config_alone_and_doctor_names_the_gap(self) -> None:
        self.install("--no-trust")
        self.assertFalse((self.codex_home / "config.toml").exists())
        problems = self.codex_problems()
        self.assertTrue(any("no trust record for this project folder" in p for p in problems))
        self.assertTrue(any("no trust record for the current ContextKit hook" in p for p in problems))

    def test_a_foreign_codex_hooks_file_raises_no_contextkit_problem(self) -> None:
        hooks = self.project / ".codex" / "hooks.json"
        hooks.parent.mkdir(parents=True, exist_ok=True)
        hooks.write_text(json.dumps({"hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "echo hi"}]}]}}) + "\n")
        self.assertEqual(self.codex_problems(), [])

    def test_a_stale_adapter_is_reported_even_when_the_hook_looks_healthy(self) -> None:
        self.install()
        adapter = self.project / ".codex" / "hooks" / "build-context.sh"
        adapter.write_text("#!/usr/bin/env bash\n# Generated by `contextkit install-hooks --target codex`; do not edit by hand.\ncontextkit build --target codex >/dev/null\n")
        self.assertTrue(any("not the current ContextKit adapter" in p for p in self.codex_problems()))
        plan = self.run_cli("migrate", "--plan")
        self.assertIn("Codex build adapter", plan.stdout)

    def test_a_narrowed_matcher_is_reported_and_repaired(self) -> None:
        self.install()
        hooks_path = self.project / ".codex" / "hooks.json"
        hooks = json.loads(hooks_path.read_text())
        hooks["hooks"]["SessionStart"][0]["matcher"] = "startup"
        hooks_path.write_text(json.dumps(hooks, indent=2) + "\n")
        self.assertTrue(any("does not run at: resume, clear" in p for p in self.codex_problems()))

        result = self.install()
        self.assertTrue(result["hook_changed"])
        self.assertEqual(json.loads(hooks_path.read_text())["hooks"]["SessionStart"][0]["matcher"], "startup|resume|clear")
        self.assertEqual(self.codex_problems(), [])

        again = self.install()
        self.assertFalse(again["hook_changed"])
        self.assertFalse(again["hook_added"])

    def test_a_shared_entry_matcher_is_not_promised_as_an_install_repair(self) -> None:
        self.install()
        hooks_path = self.project / ".codex" / "hooks.json"
        hooks = json.loads(hooks_path.read_text())
        entry = hooks["hooks"]["SessionStart"][0]
        entry["matcher"] = "startup"
        entry["hooks"].append({"type": "command", "command": "echo project hook"})
        hooks_path.write_text(json.dumps(hooks, indent=2) + "\n")
        self.assertTrue(any("its own SessionStart entry" in p for p in self.codex_problems()))

        result = self.install()
        self.assertFalse(result["hook_changed"])
        self.assertEqual(json.loads(hooks_path.read_text())["hooks"]["SessionStart"][0]["matcher"], "startup")

    def test_a_project_local_hook_is_adopted_instead_of_duplicated(self) -> None:
        hooks_path = self.project / ".codex" / "hooks.json"
        hooks_path.parent.mkdir(parents=True, exist_ok=True)
        hooks_path.write_text(json.dumps({
            "hooks": {
                "SessionStart": [{
                    "matcher": "startup",
                    "hooks": [{"type": "command", "command": "bash .codex/hooks/build-context.sh"}],
                }],
            },
        }, indent=2) + "\n")

        result = self.install()
        self.assertTrue(result["hook_changed"])
        self.assertFalse(result["hook_added"])
        hooks = json.loads(hooks_path.read_text())
        managed = [hook for entry in hooks["hooks"]["SessionStart"] for hook in entry["hooks"]
                   if "build-context.sh" in hook["command"]]
        self.assertEqual(len(managed), 1)
        self.assertEqual(hooks["hooks"]["SessionStart"][0]["matcher"], "startup|resume|clear")
        self.assertEqual(self.codex_problems(), [])
        again = self.install()
        self.assertFalse(again["hook_changed"])
        self.assertFalse(again["hook_added"])

    def test_duplicate_adapter_hooks_are_reported_and_reduced_to_one(self) -> None:
        self.install()
        hooks_path = self.project / ".codex" / "hooks.json"
        hooks = json.loads(hooks_path.read_text())
        hooks["hooks"]["SessionStart"].append({
            "matcher": "startup",
            "hooks": [{"type": "command", "command": "bash .codex/hooks/build-context.sh"}],
        })
        hooks_path.write_text(json.dumps(hooks, indent=2) + "\n")
        self.assertTrue(any("more than once" in p for p in self.codex_problems()))

        result = self.install()
        self.assertTrue(result["hook_changed"])
        session = json.loads(hooks_path.read_text())["hooks"]["SessionStart"]
        managed = [hook for entry in session for hook in entry["hooks"] if "build-context.sh" in hook["command"]]
        self.assertEqual(len(managed), 1)
        self.assertEqual(len(session), 1)
        self.assertEqual(self.codex_problems(), [])

    def test_a_foreign_hook_sharing_the_entry_is_preserved(self) -> None:
        hooks_path = self.project / ".codex" / "hooks.json"
        hooks_path.parent.mkdir(parents=True, exist_ok=True)
        hooks_path.write_text(json.dumps({
            "hooks": {
                "SessionStart": [{
                    "hooks": [
                        {"type": "command", "command": "bash .codex/hooks/build-context.sh"},
                        {"type": "command", "command": "echo project hook"},
                    ],
                }],
            },
        }, indent=2) + "\n")
        self.install()
        entry = json.loads(hooks_path.read_text())["hooks"]["SessionStart"][0]
        self.assertEqual([hook["command"] for hook in entry["hooks"]][1], "echo project hook")
        self.assertIn(HOOK_COMMAND_NEEDLE, entry["hooks"][0]["command"])

    def test_an_appended_adapter_edit_is_reported_by_doctor_and_migrate(self) -> None:
        self.install()
        adapter = self.project / ".codex" / "hooks" / "build-context.sh"
        adapter.write_text(adapter.read_text() + "\necho extra\n")
        self.assertTrue(any("not the current ContextKit adapter" in p for p in self.codex_problems()))
        plan = self.run_cli("migrate", "--plan")
        self.assertEqual(plan.returncode, 0, plan.stderr)
        self.assertNotIn("is the current ContextKit adapter", plan.stdout)
        self.assertIn("ContextKit adapter from an earlier release", plan.stdout)

    def test_an_unreadable_hooks_file_is_reported(self) -> None:
        self.install()
        (self.project / ".codex" / "hooks.json").write_text("not json\n")
        self.assertTrue(any("not a readable JSON object" in p for p in self.codex_problems()))

    def test_a_current_binding_reports_no_migration_work(self) -> None:
        self.install()
        self.assertEqual(self.codex_problems(), [])
        plan = self.run_cli("migrate", "--plan")
        self.assertEqual(plan.returncode, 0, plan.stderr)
        self.assertNotIn("is a project-local compiler", plan.stdout)
        self.assertIn("reads the generated context through this link", plan.stdout)

    def test_the_generated_context_reads_back_with_exactly_one_newline(self) -> None:
        self.install()
        read = self.run_cli("context")
        self.assertEqual(read.returncode, 0, read.stderr)
        self.assertTrue(read.stdout.endswith("\n"))
        self.assertFalse(read.stdout.endswith("\n\n"))
        self.assertEqual(read.stdout, (self.project / OUTPUT).read_text())

    def test_a_generated_context_with_a_nul_byte_is_refused(self) -> None:
        self.install()
        (self.project / OUTPUT).write_bytes(b"# Project Context\n\x00broken\n")
        read = self.run_cli("context")
        self.assertEqual(read.returncode, 6)
        self.assertIn("NUL byte", read.stderr)
        self.assertEqual(read.stdout, "")

    def test_reading_a_missing_context_fails_with_a_repair_route(self) -> None:
        self.install()
        (self.project / OUTPUT).unlink()
        read = self.run_cli("context")
        self.assertEqual(read.returncode, 6)
        self.assertIn("contextkit build", read.stderr)
        self.assertEqual(read.stdout, "")
        self.assertTrue(any("generated context is missing" in p for p in json.loads(self.run_cli("doctor", "--json").stdout)["problems"]))

    def test_a_failed_rebuild_is_announced_to_the_session(self) -> None:
        self.install()
        (self.project / ".contextkit" / "config.toml").write_text("not = [valid\n")
        emitted = self.run_adapter()
        self.assertEqual(emitted.returncode, 0, emitted.stderr)
        self.assertIn("could not rebuild the generated context", emitted.stdout)

    def test_hooks_from_earlier_releases_keep_building_the_shared_file(self) -> None:
        self.install()
        for target in ("codex", "claude", "all"):
            with self.subTest(target=target):
                built = self.run_cli("build", "--target", target)
                self.assertEqual(built.returncode, 0, built.stderr)
                read = self.run_cli("context", "--target", "codex")
                self.assertEqual(read.returncode, 0, read.stderr)


class HostLinkTests(CodexBindingCase):
    """Every host reads one generated file; ContextKit replaces only what it owns."""

    def install_claude(self) -> dict:
        installed = self.run_cli("install-hooks", "--target", "claude", "--json")
        self.assertEqual(installed.returncode, 0, installed.stderr)
        return json.loads(installed.stdout)

    def test_codex_and_claude_share_one_generated_file(self) -> None:
        self.install()
        self.install_claude()
        for link in (CODEX_LINK, CLAUDE_LINK):
            path = self.project / link
            self.assertTrue(path.is_symlink(), link)
            self.assertEqual(path.resolve(), (self.project / OUTPUT).resolve())
        self.assertFalse((self.project / ".codex" / "generated").exists())

    def test_generated_files_from_earlier_releases_are_replaced(self) -> None:
        legacy_codex = self.project / ".codex" / "generated" / "context.md"
        legacy_claude = self.project / CLAUDE_LINK
        for path in (legacy_codex, legacy_claude):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# Codex Context\n\n<!-- Generated by ContextKit. Do not edit by hand. -->\n")
        result = self.install()
        self.assertTrue(result["legacy_output_removed"])
        self.assertFalse(legacy_codex.exists())
        self.install_claude()
        self.assertTrue(legacy_claude.is_symlink())

    def test_a_file_contextkit_does_not_own_keeps_its_place(self) -> None:
        rules = self.project / CLAUDE_LINK
        rules.parent.mkdir(parents=True, exist_ok=True)
        rules.write_text("# Team rules\n")
        result = self.install_claude()
        self.assertTrue(result["build"]["links"]["claude"].startswith("blocked"))
        self.assertEqual(rules.read_text(), "# Team rules\n")
        report = json.loads(self.run_cli("doctor", "--json").stdout)
        self.assertTrue(any("CONTEXT.md` does not link" in p for p in report["problems"]))

    def test_a_claude_hook_from_an_earlier_release_is_adopted(self) -> None:
        settings = self.project / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(json.dumps({"hooks": {"SessionStart": [{"hooks": [{
            "type": "command",
            "command": "/bin/bash -lc 'contextkit build --target claude >/dev/null'",
        }]}]}}) + "\n")
        report = json.loads(self.run_cli("doctor", "--json").stdout)
        self.assertTrue(any("not the current ContextKit hook" in p for p in report["problems"]))
        self.install_claude()
        hooks = json.loads(settings.read_text())["hooks"]["SessionStart"]
        commands = [hook["command"] for entry in hooks for hook in entry["hooks"]]
        self.assertEqual(len(commands), 1)
        self.assertIn("contextkit session-start --host claude", commands[0])

    def test_foreign_instruction_files_are_named_in_the_context_and_by_doctor(self) -> None:
        self.install()
        self.install_claude()
        (self.project / "CLAUDE.md").write_text("# Old notes\n")
        nested = self.project / "service"
        nested.mkdir()
        (nested / "AGENTS.md").write_text("# Service notes\n")
        (self.project / ".claude" / "rules" / "style.md").write_text("Use tabs.\n")
        built = json.loads(self.run_cli("build", "--json").stdout)
        self.assertEqual(built["foreign_instructions"], [".claude/rules/style.md", "CLAUDE.md", "service/AGENTS.md"])
        context = (self.project / OUTPUT).read_text()
        self.assertIn("# Foreign Instruction Files", context)
        self.assertIn("- `service/AGENTS.md`", context)
        self.assertNotIn("CONTEXT.md`", context.split("# Foreign Instruction Files")[1].split("---")[0])
        doctor = self.run_cli("doctor")
        self.assertIn("Foreign instruction files", doctor.stdout)
        self.assertIn("`CLAUDE.md`", doctor.stdout)

    def test_the_generated_context_can_live_where_the_project_chooses(self) -> None:
        config = self.project / ".contextkit" / "config.toml"
        config.write_text(config.read_text().replace(
            'context = ".contextkit/generated/context.md"', 'context = "agent/runtime/context.md"'
        ))
        self.install()
        self.assertEqual((self.project / CODEX_LINK).resolve(), (self.project / "agent" / "runtime" / "context.md").resolve())
        self.assertEqual(self.codex_problems(), [])

    def test_an_output_path_outside_the_project_is_refused(self) -> None:
        config = self.project / ".contextkit" / "config.toml"
        config.write_text(config.read_text().replace(
            'context = ".contextkit/generated/context.md"', 'context = "../elsewhere.md"'
        ))
        built = self.run_cli("build")
        self.assertEqual(built.returncode, 6)
        self.assertIn("invalid output.context", built.stderr)

    def test_legacy_target_tables_are_reported_for_removal(self) -> None:
        config = self.project / ".contextkit" / "config.toml"
        config.write_text(config.read_text() + '\n[targets.codex]\noutput = ".codex/generated/context.md"\n')
        report = json.loads(self.run_cli("doctor", "--json").stdout)
        self.assertTrue(any("`[targets]` tables" in p for p in report["problems"]))
        plan = self.run_cli("migrate", "--plan")
        self.assertIn("`[targets]` tables are not read", plan.stdout)


class ReviewRegressionTests(CodexBindingCase):
    """Edges found in review: fresh clones, foreign files, and files ContextKit does not own."""

    def test_a_fresh_clone_session_is_told_it_has_no_context_yet(self) -> None:
        self.install()
        (self.project / CODEX_LINK).unlink()
        (self.project / OUTPUT).unlink()
        emitted = self.run_adapter()
        self.assertEqual(emitted.returncode, 0, emitted.stderr)
        self.assertIn("created the project context after this session started", emitted.stdout)
        self.assertTrue((self.project / CODEX_LINK).is_symlink())
        self.assertEqual(self.run_adapter().stdout, "")

    def test_an_output_path_on_a_user_file_is_refused_and_the_file_kept(self) -> None:
        (self.project / "README.md").write_text("# Mine\n")
        config = self.project / ".contextkit" / "config.toml"
        config.write_text(config.read_text().replace(
            'context = ".contextkit/generated/context.md"', 'context = "README.md"'
        ))
        built = self.run_cli("build")
        self.assertEqual(built.returncode, 6)
        self.assertIn("not ContextKit-generated context", built.stderr)
        self.assertEqual((self.project / "README.md").read_text(), "# Mine\n")

    def test_an_output_path_inside_the_source_body_is_refused(self) -> None:
        config = self.project / ".contextkit" / "config.toml"
        config.write_text(config.read_text().replace(
            'context = ".contextkit/generated/context.md"', 'context = "context/generated.md"'
        ))
        built = self.run_cli("build")
        self.assertEqual(built.returncode, 6)
        self.assertIn("inside the source body", built.stderr)

    def test_ignored_local_instruction_files_are_still_named(self) -> None:
        (self.project / ".gitignore").write_text("CLAUDE.local.md\nAGENTS.override.md\n")
        (self.project / "CLAUDE.local.md").write_text("# Local\n")
        built = json.loads(self.run_cli("build", "--json").stdout)
        self.assertIn("CLAUDE.local.md", built["foreign_instructions"])

    def test_a_symlinked_codex_user_config_stays_linked(self) -> None:
        dotfiles = self.root / "dotfiles"
        dotfiles.mkdir()
        (dotfiles / "codex.toml").write_text('model = "gpt-test"\n')
        (self.codex_home / "config.toml").symlink_to(dotfiles / "codex.toml")
        self.install()
        self.assertTrue((self.codex_home / "config.toml").is_symlink())
        linked = tomllib.loads((dotfiles / "codex.toml").read_text())
        self.assertEqual(linked["projects"][str(self.project)]["trust_level"], "trusted")

    def test_a_symlinked_claude_folder_gets_a_link_that_resolves(self) -> None:
        elsewhere = self.root / "claude-config"
        elsewhere.mkdir()
        (self.project / ".claude").symlink_to(elsewhere, target_is_directory=True)
        installed = self.run_cli("install-hooks", "--target", "claude", "--json")
        self.assertEqual(installed.returncode, 0, installed.stderr)
        self.assertEqual((self.project / CLAUDE_LINK).resolve(), (self.project / OUTPUT).resolve())
        again = json.loads(self.run_cli("build", "--json").stdout)
        self.assertEqual(again["links"]["claude"], "kept")

    def test_installing_a_binding_guards_generated_paths_in_git(self) -> None:
        gitignore = self.project / ".gitignore"
        gitignore.write_text("node_modules/\n")
        self.install()
        lines = gitignore.read_text().splitlines()
        self.assertIn(".contextkit/generated/", lines)
        self.assertIn(".contextkit.md", lines)


class CodexBindingMigrationTests(CodexBindingCase):
    """An older binding is repaired in place without discarding project settings."""

    def write_legacy_binding(self, fallback: str) -> None:
        config = self.project / ".codex" / "config.toml"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(
            f"project_doc_fallback_filenames = {fallback}\n"
            "project_doc_max_bytes = 131072\n"
            "\n"
            "[features]\n"
            "experimental = true\n"
        )
        hooks = self.project / ".codex" / "hooks.json"
        hooks.write_text(json.dumps({
            "hooks": {
                "SessionStart": [{
                    "matcher": "startup|resume|clear|compact",
                    "hooks": [{
                        "type": "command",
                        "command": (
                            "/bin/bash -lc 'root=$(git rev-parse --show-toplevel 2>/dev/null || pwd); "
                            "/bin/bash \"$root/.codex/hooks/build-context.sh\"'"
                        ),
                        "timeout": 30,
                        "statusMessage": "Regenerating ContextKit context",
                        "additionalContextLimit": 0,
                    }],
                }],
            },
        }, indent=2) + "\n")

    def test_stale_binding_is_reported_before_repair(self) -> None:
        self.write_legacy_binding('[".codex/generated/context.md", "NOTES.md"]')
        problems = "\n".join(self.codex_problems())
        self.assertIn("duplicates it on resume", problems)
        self.assertIn("does not list .contextkit.md", problems)

        plan = self.run_cli("migrate", "--plan")
        self.assertEqual(plan.returncode, 0, plan.stderr)
        self.assertIn("Codex project-doc settings", plan.stdout)

    def test_repair_replaces_the_path_entry_and_keeps_every_other_setting(self) -> None:
        self.write_legacy_binding('[".codex/generated/context.md", "NOTES.md"]')
        result = self.install()
        self.assertTrue(result["config_changed"])
        self.assertTrue(result["hook_changed"])
        self.assertFalse(result["hook_added"])

        config = tomllib.loads((self.project / ".codex" / "config.toml").read_text())
        self.assertEqual(config["project_doc_fallback_filenames"], ["NOTES.md", ".contextkit.md"])
        self.assertEqual(config["project_doc_max_bytes"], 524288)
        self.assertEqual(config["features"], {"experimental": True})
        self.assertNotIn("additionalContextLimit", self.installed_hook())
        self.assertEqual(self.codex_problems(), [])

    def test_repair_is_convergent(self) -> None:
        self.write_legacy_binding('[".codex/generated/context.md"]')
        self.install()
        config_path = self.project / ".codex" / "config.toml"
        before = (config_path.read_text(), (self.project / ".codex" / "hooks.json").read_text())
        result = self.install()
        self.assertFalse(result["config_changed"])
        self.assertFalse(result["hook_changed"])
        self.assertFalse(result["hook_added"])
        after = (config_path.read_text(), (self.project / ".codex" / "hooks.json").read_text())
        self.assertEqual(before, after)

    def test_a_larger_byte_budget_is_kept(self) -> None:
        config = self.project / ".codex" / "config.toml"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text('project_doc_fallback_filenames = [".contextkit.md"]\nproject_doc_max_bytes = 2000000\n')
        result = self.install()
        self.assertFalse(result["config_changed"])

    def test_brackets_inside_entries_never_delete_neighbouring_settings(self) -> None:
        config = self.project / ".codex" / "config.toml"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(
            'project_doc_fallback_filenames = ["x[y.md", ".codex/generated/context.md"]\n'
            "project_doc_max_bytes = 131072\n"
            "\n"
            "[features]\n"
            "experimental = true\n"
        )
        self.install()
        self.assertEqual(
            config.read_text(),
            'project_doc_fallback_filenames = ["x[y.md", ".contextkit.md"]\n'
            "project_doc_max_bytes = 524288\n"
            "\n"
            "[features]\n"
            "experimental = true\n",
        )

    def test_multiline_arrays_and_trailing_comments_survive_repair(self) -> None:
        config = self.project / ".codex" / "config.toml"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(
            "project_doc_fallback_filenames = [\n"
            '  "a].md",\n'
            '  ".codex/generated/context.md",\n'
            "]  # project documents\n"
            "project_doc_max_bytes = 131072  # budget\n"
        )
        self.install()
        self.assertEqual(
            config.read_text(),
            'project_doc_fallback_filenames = ["a].md", ".contextkit.md"]  # project documents\n'
            "project_doc_max_bytes = 524288  # budget\n",
        )

    def test_a_nested_array_before_the_entry_does_not_hide_it(self) -> None:
        config = self.project / ".codex" / "config.toml"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(
            "other = [\n  [1, 2],\n]\n"
            'project_doc_fallback_filenames = [".codex/generated/context.md"]\n'
        )
        self.install()
        parsed = tomllib.loads(config.read_text())
        self.assertEqual(parsed["other"], [[1, 2]])
        self.assertEqual(parsed["project_doc_fallback_filenames"], [".contextkit.md"])

    def test_a_quoted_key_is_located_and_repaired(self) -> None:
        config = self.project / ".codex" / "config.toml"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text('"project_doc_fallback_filenames" = [".codex/generated/context.md", "NOTES.md"]\n')
        self.install()
        self.assertEqual(
            config.read_text(),
            'project_doc_max_bytes = 524288\n"project_doc_fallback_filenames" = ["NOTES.md", ".contextkit.md"]\n',
        )

    def test_an_unparseable_codex_config_blocks_without_losing_the_plan(self) -> None:
        config = self.project / ".codex" / "config.toml"
        config.parent.mkdir(parents=True, exist_ok=True)
        original = "project_doc_fallback_filenames = [\n"
        config.write_text(original)
        self.assertTrue(any("invalid config TOML" in p for p in json.loads(self.run_cli("doctor", "--json").stdout)["problems"]))
        plan = self.run_cli("migrate", "--plan")
        self.assertEqual(plan.returncode, 0, plan.stderr)
        self.assertIn("Codex project-doc settings", plan.stdout)
        self.assertEqual(config.read_text(), original)

    def test_nested_codex_settings_are_left_to_their_owner(self) -> None:
        config = self.project / ".codex" / "config.toml"
        config.parent.mkdir(parents=True, exist_ok=True)
        original = '[profiles.review]\nproject_doc_fallback_filenames = [".codex/generated/context.md"]\n'
        config.write_text(original)
        self.install()
        text = config.read_text()
        self.assertTrue(text.endswith(original))
        parsed = tomllib.loads(text)
        self.assertEqual(parsed["profiles"]["review"]["project_doc_fallback_filenames"], [".codex/generated/context.md"])
        self.assertEqual(parsed["project_doc_fallback_filenames"], [".contextkit.md"])


LEGACY_PYTHONS = [
    path for path in ("/usr/bin/python3", "/Library/Developer/CommandLineTools/usr/bin/python3")
    if Path(path).exists()
]


class InterpreterBootstrapTests(unittest.TestCase):
    """The manager runs under a supported interpreter whatever `python3` resolves to."""

    def run_manager(
        self,
        python: str,
        *args: str,
        env: dict[str, str] | None = None,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        merged = dict(os.environ)
        merged.pop("CONTEXTKIT_PYTHON", None)
        merged.pop("CONTEXTKIT_PYTHON_BOOTSTRAP", None)
        if env:
            merged.update(env)
        return subprocess.run(
            [python, str(CONTEXTKIT), *args],
            cwd=None if cwd is None else str(cwd),
            env=merged,
            text=True,
            capture_output=True,
            check=False,
            # A regression of the re-execution bound must fail, not hang.
            timeout=60,
        )

    def legacy_python(self) -> str:
        for candidate in LEGACY_PYTHONS:
            probe = subprocess.run(
                [candidate, "-c", "import sys; print(sys.version_info[0], sys.version_info[1])"],
                text=True, capture_output=True, check=False,
            )
            if probe.returncode == 0:
                major, minor = (int(part) for part in probe.stdout.split())
                if (major, minor) < (3, 11):
                    return candidate
        self.skipTest("no Python older than 3.11 available to exercise the bootstrap")

    def initialized_project(self, legacy: str, temp: str) -> Path:
        project = Path(temp) / "project"
        project.mkdir()
        initialized = self.run_manager(legacy, "init", "--with-layers", "--json", cwd=project)
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        return project

    def test_an_explicit_supported_interpreter_is_used(self) -> None:
        legacy = self.legacy_python()
        with tempfile.TemporaryDirectory() as temp:
            project = self.initialized_project(legacy, temp)
            built = self.run_manager(
                legacy, "build", "--json",
                cwd=project, env={"CONTEXTKIT_PYTHON": sys.executable},
            )
            self.assertEqual(built.returncode, 0, built.stderr)
            self.assertTrue((project / ".contextkit" / "generated" / "context.md").exists())

    def test_an_inherited_marker_does_not_suppress_a_child_manager(self) -> None:
        legacy = self.legacy_python()
        with tempfile.TemporaryDirectory() as temp:
            project = self.initialized_project(legacy, temp)
            inherited = self.run_manager(
                legacy, "build", "--json",
                cwd=project, env={"CONTEXTKIT_PYTHON_BOOTSTRAP": "1"},
            )
            self.assertEqual(inherited.returncode, 0, inherited.stderr)
            self.assertTrue((project / ".contextkit" / "generated" / "context.md").exists())

    def test_the_bootstrap_marker_is_not_handed_to_child_processes(self) -> None:
        legacy = self.legacy_python()
        with tempfile.TemporaryDirectory() as temp:
            project = self.initialized_project(legacy, temp)
            record = Path(temp) / "child-env.txt"
            stub = Path(temp) / "capabilities"
            stub.write_text(
                "#!/bin/bash\n"
                f'printf "%s\\n" "${{CONTEXTKIT_PYTHON_BOOTSTRAP-unset}}" >> {record}\n'
                "exit 0\n"
            )
            stub.chmod(0o755)
            built = self.run_manager(
                legacy, "build", "--json",
                cwd=project, env={"CAPABILITIES_MANAGER": str(stub)},
            )
            self.assertEqual(built.returncode, 0, built.stderr)
            self.assertTrue(record.exists(), "the capabilities manager was never invoked")
            self.assertEqual(set(record.read_text().split()), {"unset"})

    def test_a_project_command_that_reads_toml_survives_an_older_interpreter(self) -> None:
        legacy = self.legacy_python()
        with tempfile.TemporaryDirectory() as temp:
            project = self.initialized_project(legacy, temp)
            built = self.run_manager(legacy, "build", "--json", cwd=project)
            self.assertEqual(built.returncode, 0, built.stderr)
            self.assertTrue((project / ".contextkit" / "generated" / "context.md").exists())

    def test_an_unsupported_explicit_interpreter_fails_once_with_the_anchor(self) -> None:
        legacy = self.legacy_python()
        result = self.run_manager(legacy, "help", env={"CONTEXTKIT_PYTHON": legacy})
        self.assertEqual(result.returncode, 6)
        self.assertIn("CONTEXTKIT_PYTHON", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_without_a_supported_interpreter_only_the_command_that_needs_one_fails(self) -> None:
        legacy = self.legacy_python()
        constrained = {"PATH": "/usr/bin:/bin"}
        served = self.run_manager(legacy, "help", env=constrained)
        self.assertEqual(served.returncode, 0, served.stderr)
        self.assertIn("contextkit —", served.stdout)

        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"
            project.mkdir()
            (project / ".contextkit").mkdir()
            (project / ".contextkit" / "config.toml").write_text('version = 1\ntype = "agent-project"\n')
            blocked = subprocess.run(
                [legacy, str(CONTEXTKIT), "build"],
                cwd=project,
                env={**{k: v for k, v in os.environ.items() if k != "CONTEXTKIT_PYTHON"}, **constrained},
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(blocked.returncode, 6)
            self.assertIn("Python 3.11+ is required", blocked.stderr)
            self.assertIn("CONTEXTKIT_PYTHON", blocked.stderr)


class TomlScanTests(unittest.TestCase):
    """The config scanner refuses a document it cannot resolve."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_manager()

    def test_ambiguous_documents_are_not_scanned(self) -> None:
        for text in (
            'project_doc_fallback_filenames = ["unterminated\n',
            "project_doc_fallback_filenames = [\n",
            'project_doc_fallback_filenames "NOTES.md"\n',
        ):
            with self.subTest(text=text):
                _assignments, scanned = self.module._toml_top_level_assignments(text)
                self.assertFalse(scanned)

    def test_a_table_header_ends_the_top_level_region(self) -> None:
        text = 'a = 1\n\n[features]\nproject_doc_fallback_filenames = ["x.md"]\n'
        assignments, scanned = self.module._toml_top_level_assignments(text)
        self.assertTrue(scanned)
        self.assertEqual(set(assignments), {"a"})

    def test_an_unresolvable_entry_blocks_the_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / "config.toml"
            config.write_text('project_doc_fallback_filenames = [".codex/generated/context.md"]\n')
            original = self.module._toml_top_level_assignments
            self.module._toml_top_level_assignments = lambda text: ({}, False)
            try:
                plan = self.module._planned_codex_config(config)
            finally:
                self.module._toml_top_level_assignments = original
            self.assertFalse(plan["changed"])
            self.assertIn("cannot update the Codex project-doc settings", plan["blocked"])
            self.assertEqual(plan["text"], config.read_text())


class CodexTrustTests(unittest.TestCase):
    """ContextKit reproduces the trust identity Codex records for a hook."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_manager()

    def test_the_hook_hash_matches_a_record_codex_wrote(self) -> None:
        # Recorded by codex-cli 0.156.1 when a user approved this exact hook.
        hook = {
            "additionalContextLimit": 0,
            "command": "/bin/bash -lc 'root=$(git rev-parse --show-toplevel 2>/dev/null || pwd); /bin/bash \"$root/.codex/hooks/build-context.sh\"'",
            "statusMessage": "Regenerating ContextKit context",
            "timeout": 30,
            "type": "command",
        }
        self.assertEqual(
            self.module._codex_hook_hash("startup|resume|clear|compact", hook),
            "sha256:2e6461841a0cf43b572c4ff02d4f51e6770d77bd045eadc85422f7b578e00c73",
        )

    def test_a_table_value_is_set_without_touching_anything_else(self) -> None:
        text = '[projects."/p"]\ntrust_level = "untrusted"  # decided\nother = 1\n\n[projects."/q"]\ntrust_level = "trusted"\n'
        updated = self.module._toml_set_table_value(text, ["projects", "/p"], "trust_level", "trusted")
        self.assertEqual(updated, text.replace('"untrusted"  # decided', '"trusted"'))

    def test_an_ambiguous_document_is_left_alone(self) -> None:
        text = 'projects = { "/p" = { trust_level = "untrusted" } }\n'
        self.assertIsNone(self.module._toml_set_table_value(text, ["projects", "/p"], "trust_level", "trusted"))


if __name__ == "__main__":
    unittest.main()
