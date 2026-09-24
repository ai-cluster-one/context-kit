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


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTEXTKIT = REPO_ROOT / "bin" / "contextkit"
HOOK_COMMAND_NEEDLE = ".codex/hooks/build-context.sh"
MARKER = "MIDDLE-MARKER-4f2c"


class CodexBindingCase(unittest.TestCase):
    """Fixture for a project whose Codex binding ContextKit owns."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        subprocess.run(["git", "init", "-q", "."], cwd=self.project, check=True)
        initialized = self.run_cli("init", "--with-layers", "--json")
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        self.manager = self.project / ".contextkit" / "manager"
        self.manager.mkdir(parents=True, exist_ok=True)
        (self.manager / "contextkit").symlink_to(CONTEXTKIT)

    def run_cli(self, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(CONTEXTKIT), *args],
            cwd=self.project,
            env=dict(os.environ),
            input=stdin,
            text=True,
            capture_output=True,
            check=False,
        )

    def run_adapter(self, *args: str, path_prefix: Path | None = None) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        if path_prefix is not None:
            env["PATH"] = f"{path_prefix}{os.pathsep}{env['PATH']}"
        return subprocess.run(
            ["/bin/bash", str(self.project / ".codex" / "hooks" / "build-context.sh"), *args],
            cwd=self.project,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def install(self) -> dict:
        installed = self.run_cli("install-hooks", "--target", "codex", "--json")
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


class CodexDeliveryTests(CodexBindingCase):
    """Codex receives generated context through synchronous SessionStart stdout."""

    def test_session_start_hook_delivers_context_without_a_context_limit(self) -> None:
        self.install()
        hook = self.installed_hook()
        self.assertEqual(hook["additionalContextLimit"], 0)
        self.assertNotIn("async", hook)
        entry = json.loads((self.project / ".codex" / "hooks.json").read_text())["hooks"]["SessionStart"][0]
        self.assertEqual(entry["matcher"], "startup|resume|clear|compact")

    def test_install_writes_no_codex_project_doc_settings(self) -> None:
        self.install()
        self.assertFalse((self.project / ".codex" / "config.toml").exists())

    def test_adapter_emits_the_generated_target_verbatim(self) -> None:
        self.install()
        built = self.run_cli("build", "--target", "codex")
        self.assertEqual(built.returncode, 0, built.stderr)
        emitted = self.run_adapter()
        self.assertEqual(emitted.returncode, 0, emitted.stderr)
        generated = (self.project / ".codex" / "generated" / "context.md").read_text()
        self.assertEqual(emitted.stdout, generated)

    def test_large_context_is_emitted_whole(self) -> None:
        self.install()
        note = f"{'x' * 70000}\n{MARKER}\n{'y' * 70000}"
        added = self.run_cli("memory", "add", "--stdin", stdin=note)
        self.assertEqual(added.returncode, 0, added.stderr)

        emitted = self.run_adapter()
        self.assertEqual(emitted.returncode, 0, emitted.stderr)
        generated = (self.project / ".codex" / "generated" / "context.md").read_text()
        self.assertGreater(len(generated.encode()), 140000)
        self.assertEqual(emitted.stdout, generated)
        self.assertIn(MARKER, emitted.stdout)
        self.assertIn("y" * 70000, emitted.stdout)

    def test_claude_only_invocation_emits_no_codex_context(self) -> None:
        self.install()
        emitted = self.run_adapter("claude")
        self.assertEqual(emitted.returncode, 0, emitted.stderr)
        self.assertEqual(emitted.stdout, "")

    def test_a_foreign_codex_hooks_file_raises_no_contextkit_problem(self) -> None:
        hooks = self.project / ".codex" / "hooks.json"
        hooks.parent.mkdir(parents=True, exist_ok=True)
        hooks.write_text(json.dumps({"hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "echo hi"}]}]}}) + "\n")
        report = json.loads(self.run_cli("doctor", "--json").stdout)
        self.assertEqual([p for p in report["problems"] if "Codex" in p], [])

    def test_a_stale_adapter_is_reported_even_when_the_hook_looks_healthy(self) -> None:
        self.install()
        adapter = self.project / ".codex" / "hooks" / "build-context.sh"
        adapter.write_text("#!/usr/bin/env bash\n# Generated by `contextkit install-hooks --target codex`; do not edit by hand.\ncontextkit build --target codex >/dev/null\n")
        report = json.loads(self.run_cli("doctor", "--json").stdout)
        self.assertTrue(any("not the current ContextKit adapter" in p for p in report["problems"]))
        plan = self.run_cli("migrate", "--plan")
        self.assertIn("Codex build adapter", plan.stdout)

    def test_a_narrowed_matcher_is_reported_and_repaired(self) -> None:
        self.install()
        hooks_path = self.project / ".codex" / "hooks.json"
        hooks = json.loads(hooks_path.read_text())
        hooks["hooks"]["SessionStart"][0]["matcher"] = "startup"
        hooks_path.write_text(json.dumps(hooks, indent=2) + "\n")
        report = json.loads(self.run_cli("doctor", "--json").stdout)
        self.assertTrue(any("does not run at: resume, clear, compact" in p for p in report["problems"]))

        result = self.install()
        self.assertTrue(result["hook_changed"])
        self.assertEqual(json.loads(hooks_path.read_text())["hooks"]["SessionStart"][0]["matcher"], "startup|resume|clear|compact")
        repaired = json.loads(self.run_cli("doctor", "--json").stdout)
        self.assertEqual([p for p in repaired["problems"] if "Codex" in p], [])

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

        report = json.loads(self.run_cli("doctor", "--json").stdout)
        self.assertTrue(any("its own SessionStart entry" in p for p in report["problems"]))

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
        self.assertEqual(managed[0]["additionalContextLimit"], 0)
        self.assertEqual(hooks["hooks"]["SessionStart"][0]["matcher"], "startup|resume|clear|compact")

        report = json.loads(self.run_cli("doctor", "--json").stdout)
        self.assertEqual([p for p in report["problems"] if "Codex" in p], [])
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

        report = json.loads(self.run_cli("doctor", "--json").stdout)
        self.assertTrue(any("delivered more than once" in p for p in report["problems"]))

        result = self.install()
        self.assertTrue(result["hook_changed"])
        session = json.loads(hooks_path.read_text())["hooks"]["SessionStart"]
        managed = [hook for entry in session for hook in entry["hooks"] if "build-context.sh" in hook["command"]]
        self.assertEqual(len(managed), 1)
        self.assertEqual(len(session), 1)
        repaired = json.loads(self.run_cli("doctor", "--json").stdout)
        self.assertEqual([p for p in repaired["problems"] if "Codex" in p], [])

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
        self.assertEqual(entry["hooks"][0]["additionalContextLimit"], 0)

    def test_an_appended_adapter_edit_is_reported_by_doctor_and_migrate(self) -> None:
        self.install()
        adapter = self.project / ".codex" / "hooks" / "build-context.sh"
        adapter.write_text(adapter.read_text() + "\necho extra\n")
        report = json.loads(self.run_cli("doctor", "--json").stdout)
        self.assertTrue(any("not the current ContextKit adapter" in p for p in report["problems"]))
        plan = self.run_cli("migrate", "--plan")
        self.assertEqual(plan.returncode, 0, plan.stderr)
        self.assertNotIn("is the current ContextKit adapter", plan.stdout)
        self.assertIn("ContextKit adapter from an earlier release", plan.stdout)

    def test_an_unreadable_hooks_file_is_reported(self) -> None:
        self.install()
        (self.project / ".codex" / "hooks.json").write_text("not json\n")
        report = json.loads(self.run_cli("doctor", "--json").stdout)
        self.assertTrue(any("not a readable JSON object" in p for p in report["problems"]))

    def test_a_current_binding_reports_no_migration_work(self) -> None:
        self.install()
        built = self.run_cli("build", "--target", "codex")
        self.assertEqual(built.returncode, 0, built.stderr)
        report = json.loads(self.run_cli("doctor", "--json").stdout)
        self.assertEqual([p for p in report["problems"] if "Codex" in p], [])
        plan = self.run_cli("migrate", "--plan")
        self.assertEqual(plan.returncode, 0, plan.stderr)
        self.assertNotIn("is a project-local compiler", plan.stdout)

    def test_the_emitted_target_ends_with_exactly_one_newline(self) -> None:
        self.install()
        emitted = self.run_adapter()
        self.assertEqual(emitted.returncode, 0, emitted.stderr)
        self.assertTrue(emitted.stdout.endswith("\n"))
        self.assertFalse(emitted.stdout.endswith("\n\n"))

    def test_a_target_with_a_nul_byte_is_refused(self) -> None:
        self.install()
        built = self.run_cli("build", "--target", "codex")
        self.assertEqual(built.returncode, 0, built.stderr)
        target = self.project / ".codex" / "generated" / "context.md"
        target.write_bytes(b"# Codex Context\n\x00broken\n")
        read = self.run_cli("context", "--target", "codex")
        self.assertEqual(read.returncode, 6)
        self.assertIn("NUL byte", read.stderr)
        self.assertEqual(read.stdout, "")

    def test_reading_a_missing_target_fails_with_a_repair_route(self) -> None:
        self.install()
        built = self.run_cli("build", "--target", "codex")
        self.assertEqual(built.returncode, 0, built.stderr)
        (self.project / ".codex" / "generated" / "context.md").unlink()
        read = self.run_cli("context", "--target", "codex")
        self.assertEqual(read.returncode, 6)
        self.assertIn("contextkit build --target codex", read.stderr)
        self.assertEqual(read.stdout, "")

    def _stub_manager(self, body: str) -> Path:
        stub_dir = self.root / "stub-bin"
        stub_dir.mkdir(exist_ok=True)
        stub = stub_dir / "contextkit"
        stub.write_text(body)
        stub.chmod(0o755)
        (self.manager / "contextkit").unlink()
        return stub_dir

    def test_a_failed_build_never_reports_loaded_context(self) -> None:
        self.install()
        stub_dir = self._stub_manager(
            "#!/bin/bash\n"
            "if [ \"$1\" = build ]; then printf 'build broke\\n' >&2; exit 6; fi\n"
            "printf 'context that must never be emitted\\n'\n"
        )
        emitted = self.run_adapter(path_prefix=stub_dir)
        self.assertNotEqual(emitted.returncode, 0)
        self.assertEqual(emitted.stdout, "")
        self.assertIn("ContextKit build failed", emitted.stderr)

    def test_a_failed_read_never_emits_partial_context(self) -> None:
        self.install()
        stub_dir = self._stub_manager(
            "#!/bin/bash\n"
            "if [ \"$1\" = build ]; then exit 0; fi\n"
            "printf 'half a document' ; printf 'cannot read generated codex context\\n' >&2; exit 6\n"
        )
        emitted = self.run_adapter(path_prefix=stub_dir)
        self.assertNotEqual(emitted.returncode, 0)
        self.assertEqual(emitted.stdout, "")
        self.assertIn("could not read generated Codex context", emitted.stderr)


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
                    }],
                }],
            },
        }, indent=2) + "\n")

    def test_stale_binding_is_reported_before_repair(self) -> None:
        self.write_legacy_binding('[".codex/generated/context.md", "NOTES.md"]')
        report = json.loads(self.run_cli("doctor", "--json").stdout)
        problems = "\n".join(report["problems"])
        self.assertIn("additionalContextLimit 0", problems)
        self.assertIn("project_doc_fallback_filenames", problems)

        plan = self.run_cli("migrate", "--plan")
        self.assertEqual(plan.returncode, 0, plan.stderr)
        self.assertIn("Codex project-doc fallback", plan.stdout)

    def test_repair_removes_only_the_generated_fallback_entry(self) -> None:
        self.write_legacy_binding('[".codex/generated/context.md", "NOTES.md"]')
        result = self.install()
        self.assertTrue(result["config_changed"])
        self.assertTrue(result["hook_changed"])
        self.assertFalse(result["hook_added"])

        config = tomllib.loads((self.project / ".codex" / "config.toml").read_text())
        self.assertEqual(config["project_doc_fallback_filenames"], ["NOTES.md"])
        self.assertEqual(config["project_doc_max_bytes"], 131072)
        self.assertEqual(config["features"], {"experimental": True})
        self.assertEqual(self.installed_hook()["additionalContextLimit"], 0)

        report = json.loads(self.run_cli("doctor", "--json").stdout)
        self.assertNotIn("codex", " ".join(report["problems"]).casefold())

    def test_repair_drops_an_empty_fallback_array_and_is_convergent(self) -> None:
        self.write_legacy_binding('[".codex/generated/context.md"]')
        self.install()
        config_path = self.project / ".codex" / "config.toml"
        config = tomllib.loads(config_path.read_text())
        self.assertNotIn("project_doc_fallback_filenames", config)
        self.assertEqual(config["project_doc_max_bytes"], 131072)

        before = (config_path.read_text(), (self.project / ".codex" / "hooks.json").read_text())
        result = self.install()
        self.assertFalse(result["config_changed"])
        self.assertFalse(result["hook_changed"])
        self.assertFalse(result["hook_added"])
        after = (config_path.read_text(), (self.project / ".codex" / "hooks.json").read_text())
        self.assertEqual(before, after)

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
            'project_doc_fallback_filenames = ["x[y.md"]\n'
            "project_doc_max_bytes = 131072\n"
            "\n"
            "[features]\n"
            "experimental = true\n",
        )
        self.assertEqual(tomllib.loads(config.read_text())["features"], {"experimental": True})

    def test_multiline_arrays_and_trailing_comments_survive_repair(self) -> None:
        config = self.project / ".codex" / "config.toml"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(
            "project_doc_fallback_filenames = [\n"
            '  "a].md",\n'
            '  ".codex/generated/context.md",\n'
            "]  # project documents\n"
            "project_doc_max_bytes = 131072\n"
        )
        self.install()
        self.assertEqual(
            config.read_text(),
            'project_doc_fallback_filenames = ["a].md"]  # project documents\n'
            "project_doc_max_bytes = 131072\n",
        )
        self.assertEqual(tomllib.loads(config.read_text())["project_doc_fallback_filenames"], ["a].md"])

    def test_an_emptied_array_is_removed_and_keeps_its_comment(self) -> None:
        config = self.project / ".codex" / "config.toml"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(
            'project_doc_fallback_filenames = [".codex/generated/context.md"]  # keep this note\n'
            "project_doc_max_bytes = 131072\n"
        )
        self.install()
        self.assertEqual(
            config.read_text(),
            "# keep this note\n"
            "project_doc_max_bytes = 131072\n",
        )
        self.assertNotIn("project_doc_fallback_filenames", tomllib.loads(config.read_text()))

    def test_a_nested_array_before_the_entry_does_not_hide_it(self) -> None:
        config = self.project / ".codex" / "config.toml"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(
            "other = [\n  [1, 2],\n]\n"
            'project_doc_fallback_filenames = [".codex/generated/context.md"]\n'
        )
        self.install()
        self.assertEqual(config.read_text(), "other = [\n  [1, 2],\n]\n")
        self.assertEqual(tomllib.loads(config.read_text())["other"], [[1, 2]])

    def test_a_quoted_key_is_located_and_repaired(self) -> None:
        config = self.project / ".codex" / "config.toml"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text('"project_doc_fallback_filenames" = [".codex/generated/context.md", "NOTES.md"]\n')
        self.install()
        self.assertEqual(config.read_text(), '"project_doc_fallback_filenames" = ["NOTES.md"]\n')

    def test_an_unparseable_codex_config_blocks_without_losing_the_plan(self) -> None:
        config = self.project / ".codex" / "config.toml"
        config.parent.mkdir(parents=True, exist_ok=True)
        original = "project_doc_fallback_filenames = [\n"
        config.write_text(original)

        report = json.loads(self.run_cli("doctor", "--json").stdout)
        self.assertTrue(any("invalid config TOML" in p for p in report["problems"]))

        plan = self.run_cli("migrate", "--plan")
        self.assertEqual(plan.returncode, 0, plan.stderr)
        self.assertIn("Codex project-doc fallback", plan.stdout)
        self.assertEqual(config.read_text(), original)

    def test_nested_codex_settings_are_left_to_their_owner(self) -> None:
        config = self.project / ".codex" / "config.toml"
        config.parent.mkdir(parents=True, exist_ok=True)
        original = '[profiles.review]\nproject_doc_fallback_filenames = [".codex/generated/context.md"]\n'
        config.write_text(original)
        result = self.install()
        self.assertFalse(result["config_changed"])
        self.assertEqual(config.read_text(), original)

        built = self.run_cli("build", "--target", "codex")
        self.assertEqual(built.returncode, 0, built.stderr)



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
                legacy, "build", "--target", "codex", "--json",
                cwd=project, env={"CONTEXTKIT_PYTHON": sys.executable},
            )
            self.assertEqual(built.returncode, 0, built.stderr)
            self.assertTrue((project / ".codex" / "generated" / "context.md").exists())

    def test_an_inherited_marker_does_not_suppress_a_child_manager(self) -> None:
        legacy = self.legacy_python()
        with tempfile.TemporaryDirectory() as temp:
            project = self.initialized_project(legacy, temp)
            inherited = self.run_manager(
                legacy, "build", "--target", "codex", "--json",
                cwd=project, env={"CONTEXTKIT_PYTHON_BOOTSTRAP": "1"},
            )
            self.assertEqual(inherited.returncode, 0, inherited.stderr)
            self.assertTrue((project / ".codex" / "generated" / "context.md").exists())

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
                legacy, "build", "--target", "codex", "--json",
                cwd=project, env={"CAPABILITIES_MANAGER": str(stub)},
            )
            self.assertEqual(built.returncode, 0, built.stderr)
            self.assertTrue(record.exists(), "the capabilities manager was never invoked")
            self.assertEqual(set(record.read_text().split()), {"unset"})

    def test_a_project_command_that_reads_toml_survives_an_older_interpreter(self) -> None:
        legacy = self.legacy_python()
        with tempfile.TemporaryDirectory() as temp:
            project = self.initialized_project(legacy, temp)
            built = self.run_manager(legacy, "build", "--target", "codex", "--json", cwd=project)
            self.assertEqual(built.returncode, 0, built.stderr)
            self.assertTrue((project / ".codex" / "generated" / "context.md").exists())

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
                [legacy, str(CONTEXTKIT), "build", "--target", "codex"],
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
        name = "contextkit_codex_delivery_test_module"
        loader = importlib.machinery.SourceFileLoader(name, str(CONTEXTKIT))
        spec = importlib.util.spec_from_loader(name, loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        loader.exec_module(module)
        cls.module = module

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
                plan = self.module._planned_codex_config(config, ".codex/generated/context.md")
            finally:
                self.module._toml_top_level_assignments = original
            self.assertFalse(plan["changed"])
            self.assertIn("cannot locate that assignment safely", plan["blocked"])
            self.assertEqual(plan["text"], config.read_text())


if __name__ == "__main__":
    unittest.main()
