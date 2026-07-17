from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTEXTKIT = REPO_ROOT / "bin" / "contextkit"
CAPABILITIES_PROVIDER = REPO_ROOT / "tests" / "fixtures" / "capabilities"


FAKE_CODEX = r'''#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

args = sys.argv[1:]
cwd = Path.cwd().resolve()
target = Path(args[args.index("--add-dir") + 1]).resolve()
host = cwd / "AGENTS.md"
prompt = sys.stdin.read()
guide = subprocess.run(
    ["contextkit", "guide", "authoring"], cwd=cwd, env=os.environ,
    text=True, capture_output=True, check=False,
)
capture = {
    "engine": Path(sys.argv[0]).name,
    "cwd": str(cwd),
    "target": str(target),
    "args": args,
    "prompt": prompt,
    "host_file": host.name,
    "context": host.read_text(),
    "target_anchor": os.environ.get("CONTEXTKIT_TARGET_PROJECT"),
    "claude_project_dir": os.environ.get("CLAUDE_PROJECT_DIR"),
    "guide_executable": shutil.which("contextkit"),
    "guide_returncode": guide.returncode,
    "guide_stdout": guide.stdout,
}
Path(os.environ["FAKE_CAPTURE"]).write_text(json.dumps(capture))
mutate_path = os.environ.get("FAKE_MUTATE_PATH")
if mutate_path:
    (target / mutate_path).write_text(os.environ.get("FAKE_MUTATE_CONTENT", "changed by fake engine\n"))
elif os.environ.get("FAKE_MUTATE") == "1":
    (target / "workbench-write.txt").write_text("changed by fake engine\n")
if os.environ.get("FAKE_INDEX_ONLY"):
    hashed = subprocess.run(
        ["git", "hash-object", "-w", "--stdin"], cwd=target,
        input=os.environ["FAKE_INDEX_ONLY"], text=True, capture_output=True, check=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "update-index", "--cacheinfo", f"100644,{hashed},tracked.txt"],
        cwd=target, check=True,
    )
if os.environ.get("FAKE_HEAD_MOVE") == "1":
    subprocess.run(
        ["git", "-c", "user.name=ContextKit Test", "-c", "user.email=contextkit@example.invalid",
         "commit", "--allow-empty", "-m", "fake head move"],
        cwd=target, text=True, capture_output=True, check=True,
    )
if os.environ.get("FAKE_SLEEP"):
    time.sleep(float(os.environ["FAKE_SLEEP"]))
if os.environ.get("FAKE_EXIT"):
    print("fake engine failure", file=sys.stderr)
    raise SystemExit(int(os.environ["FAKE_EXIT"]))
output = Path(args[args.index("-o") + 1])
output.write_text("fake codex answer\n")
print(json.dumps({"type": "thread.started", "thread_id": "fake-codex-session"}))
print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 11, "output_tokens": 7, "cached_input_tokens": 3}}))
'''


class WorkbenchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        codex = self.bin_dir / "codex"
        codex.write_text(FAKE_CODEX)
        codex.chmod(0o755)
        self.capture = self.root / "capture.json"
        self.project = self.root / "target"
        self.project.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.project, check=True)
        initialized = self.run_cli("init", "--with-layers", "--json")
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        identity = self.project / "context" / "identity"
        identity.mkdir()
        (identity / "PERSONA.md").write_text(textwrap.dedent("""\
            ---
            title: Target Persona
            description: Load when the target worker needs its target-only accountant identity and operating role.
            load: inline
            order: 100
            ---

            TARGET PERSONA SECRET: You are the target accountant.
            """))
        (self.project / "routines" / "target-only.md").write_text(textwrap.dedent("""\
            ---
            name: target-only
            description: TARGET ROUTINE SECRET.
            ---

            # Target Routine
            """))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_cli(self, *args: str, env_extra: dict[str, str] | None = None,
                input_text: str | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env["PATH"] = str(self.bin_dir) + os.pathsep + env.get("PATH", "")
        env["FAKE_CAPTURE"] = str(self.capture)
        env["CAPABILITIES_MANAGER"] = str(CAPABILITIES_PROVIDER)
        if env_extra:
            env.update(env_extra)
        return subprocess.run(
            [str(CONTEXTKIT), *args],
            cwd=cwd or self.project,
            env=env,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
        )

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args], cwd=self.project, text=True,
            capture_output=True, check=True,
        )

    def commit_all(self, message: str = "test baseline") -> None:
        self.git("add", "-A")
        self.git(
            "-c", "user.name=ContextKit Test", "-c", "user.email=contextkit@example.invalid",
            "commit", "--allow-empty", "-m", message,
        )

    def result(self, proc: subprocess.CompletedProcess[str]) -> dict:
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            self.fail(f"invalid JSON result: {exc}\nstdout={proc.stdout}\nstderr={proc.stderr}")

    def capture_data(self) -> dict:
        return json.loads(self.capture.read_text())

    def remove_kept_workbench(self, workbench: Path) -> None:
        for directory, subdirs, _files in os.walk(workbench, topdown=False, followlinks=False):
            for name in subdirs:
                child = Path(directory) / name
                if not child.is_symlink():
                    child.chmod(0o700)
            Path(directory).chmod(0o700)
        shutil.rmtree(workbench)

    def assert_read_mutation(self, env_extra: dict[str, str], expected_path: str) -> dict:
        proc = self.run_cli("workbench", "Read only.", "--json", env_extra=env_extra)
        self.assertNotEqual(proc.returncode, 0, proc.stderr)
        result = self.result(proc)
        self.assertFalse(result["ok"])
        self.assertIn("read-only workbench mutated the target", result["error"])
        self.assertIn(expected_path, [item["path"] for item in result["git"]["files_changed"]])
        return result

    def test_codex_read_uses_isolated_context_current_guides_and_hard_fence(self) -> None:
        proc = self.run_cli(
            "workbench", "--stdin", "--json", "--keep",
            input_text="Review Direct Address in the target.",
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = self.result(proc)
        capture = self.capture_data()
        workbench = Path(result["workbench_path"])
        try:
            self.assertTrue(result["ok"])
            self.assertEqual(result["engine"], "codex")
            self.assertEqual(result["mode"], "read")
            self.assertEqual(result["answer"], "fake codex answer")
            self.assertEqual(result["session_id"], "fake-codex-session")
            self.assertTrue(workbench.is_dir())
            self.assertFalse(workbench == self.project or workbench in self.project.parents or self.project in workbench.parents)
            self.assertEqual(capture["cwd"], str(workbench))
            self.assertIsNone(capture["claude_project_dir"])
            self.assertEqual(capture["target_anchor"], str(self.project))
            self.assertEqual(capture["host_file"], "AGENTS.md")
            self.assertIn("-C", capture["args"])
            self.assertEqual(capture["args"][capture["args"].index("-C") + 1], str(workbench))
            self.assertEqual(capture["args"][capture["args"].index("--add-dir") + 1], str(self.project))
            self.assertIn("--ephemeral", capture["args"])
            self.assertIn("--ignore-user-config", capture["args"])
            self.assertIn("--ignore-rules", capture["args"])
            self.assertEqual(capture["args"][capture["args"].index("--sandbox") + 1], "read-only")
            self.assertIn('approval_policy="never"', capture["args"])
            self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", capture["args"])
            self.assertIn("# Guide Menu", capture["context"])
            self.assertIn("# Workbench Guide", capture["context"])
            self.assertIn("You are operating inside a ContextKit-managed project.", capture["context"])
            self.assertNotIn("TARGET PERSONA SECRET", capture["context"])
            self.assertNotIn("TARGET ROUTINE SECRET", capture["context"])
            self.assertNotIn("fixture manager-owned block", capture["context"])
            self.assertIn("Review Direct Address in the target.", capture["prompt"])
            self.assertIn("## Authorized Scope", capture["prompt"])
            self.assertIn("## Acceptance Criteria", capture["prompt"])
            self.assertIn("## Required Validation", capture["prompt"])
            self.assertEqual(capture["guide_returncode"], 0)
            self.assertEqual(Path(capture["guide_executable"]), workbench / "contextkit")
            self.assertIn("# ContextKit Authoring Guide", capture["guide_stdout"])
            self.assertTrue((workbench / ".contextkit-workbench.json").is_file())
            self.assertTrue((workbench / "distribution.json").is_file())
            self.assertEqual((workbench / "guides").stat().st_mode & 0o777, 0o555)
            self.assertEqual((workbench / "guides" / "authoring.md").stat().st_mode & 0o777, 0o444)
            self.assertEqual(result["git"]["files_changed"], [])
            self.assertIn("ignored files excluded", result["git"]["coverage"])
        finally:
            self.remove_kept_workbench(workbench)

    def test_tmpdir_inside_target_falls_back_to_external_root(self) -> None:
        unsafe_tmp = self.project / "unsafe-tmp"
        unsafe_tmp.mkdir()
        proc = self.run_cli(
            "workbench", "Inspect safely.", "--json", "--keep",
            env_extra={"TMPDIR": str(unsafe_tmp)},
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = self.result(proc)
        workbench = Path(result["workbench_path"])
        try:
            repo_root = Path(result["git"]["root"])
            self.assertFalse(workbench == self.project or workbench in self.project.parents or self.project in workbench.parents)
            self.assertFalse(workbench == repo_root or workbench in repo_root.parents or repo_root in workbench.parents)
            self.assertFalse(workbench.is_relative_to(unsafe_tmp))
            self.assertTrue((workbench / ".contextkit-workbench.json").is_file())
        finally:
            self.remove_kept_workbench(workbench)

    def test_codex_write_uses_workspace_fence_and_runs_validation(self) -> None:
        proc = self.run_cli(
            "workbench", "Make one local source change.", "--write", "--json",
            env_extra={"FAKE_MUTATE": "1"},
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = self.result(proc)
        capture = self.capture_data()
        self.assertTrue(result["ok"])
        self.assertEqual(capture["args"][capture["args"].index("--sandbox") + 1], "workspace-write")
        self.assertIn("sandbox_workspace_write.network_access=false", capture["args"])
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", capture["args"])
        self.assertEqual([item["name"] for item in result["validation"]], ["doctor", "build", "audit"])
        self.assertTrue(all(item["ok"] for item in result["validation"]))
        self.assertIn("workbench-write.txt", [item["path"] for item in result["git"]["files_changed"]])
        self.assertIsNone(result["workbench_path"])
        self.assertFalse(Path(capture["cwd"]).exists())

    def test_pre_dirty_tracked_content_mutation_is_detected(self) -> None:
        tracked = self.project / "tracked.txt"
        tracked.write_text("committed\n")
        self.commit_all()
        tracked.write_text("pre-existing dirty\n")

        result = self.assert_read_mutation(
            {"FAKE_MUTATE_PATH": "tracked.txt", "FAKE_MUTATE_CONTENT": "changed again\n"},
            "tracked.txt",
        )
        self.assertTrue(result["git"]["dirty_before"])

    def test_pre_existing_untracked_content_mutation_is_detected(self) -> None:
        self.commit_all()
        (self.project / "untracked.txt").write_text("pre-existing untracked\n")

        result = self.assert_read_mutation(
            {"FAKE_MUTATE_PATH": "untracked.txt", "FAKE_MUTATE_CONTENT": "changed untracked\n"},
            "untracked.txt",
        )
        self.assertTrue(result["git"]["dirty_before"])

    def test_index_only_mutation_with_same_porcelain_is_detected(self) -> None:
        tracked = self.project / "tracked.txt"
        tracked.write_text("committed\n")
        self.commit_all()
        tracked.write_text("staged version\n")
        self.git("add", "tracked.txt")
        tracked.write_text("working version\n")
        status_before = self.git("status", "--porcelain=v1").stdout
        self.assertIn("MM tracked.txt", status_before)

        result = self.assert_read_mutation({"FAKE_INDEX_ONLY": "different staged blob\n"}, "<INDEX>")
        status_after = self.git("status", "--porcelain=v1").stdout
        self.assertIn("MM tracked.txt", status_after)
        self.assertNotEqual(result["git"]["index_before"], result["git"]["index_after"])

    def test_head_move_is_detected(self) -> None:
        self.commit_all()
        result = self.assert_read_mutation({"FAKE_HEAD_MOVE": "1"}, "<HEAD>")
        self.assertNotEqual(result["git"]["head_before"], result["git"]["head_after"])

    def test_engine_error_and_timeout_are_normalized_and_cleaned_up(self) -> None:
        failed = self.run_cli(
            "workbench", "Fail safely.", "--json", env_extra={"FAKE_EXIT": "7"},
        )
        self.assertNotEqual(failed.returncode, 0)
        failed_result = self.result(failed)
        failed_capture = self.capture_data()
        self.assertFalse(failed_result["ok"])
        self.assertIn("Codex exited 7", failed_result["error"])
        self.assertFalse(Path(failed_capture["cwd"]).exists())

        timed_out = self.run_cli(
            "workbench", "Time out safely.", "--timeout", "1", "--json",
            env_extra={"FAKE_SLEEP": "3"},
        )
        self.assertNotEqual(timed_out.returncode, 0)
        timeout_result = self.result(timed_out)
        timeout_capture = self.capture_data()
        self.assertFalse(timeout_result["ok"])
        self.assertIn("timed out after 1s", timeout_result["error"])
        self.assertFalse(Path(timeout_capture["cwd"]).exists())

    def test_json_task_preflight_errors_are_normalized(self) -> None:
        cases = [
            (("workbench", "--json"), None, "requires a non-empty task"),
            (("workbench", "", "--json"), None, "requires a non-empty task"),
            (("workbench", "positional", "--stdin", "--json"), "stdin task", "either a positional task or --stdin"),
        ]
        for args, input_text, expected in cases:
            with self.subTest(args=args):
                proc = self.run_cli(*args, input_text=input_text)
                self.assertEqual(proc.returncode, 6)
                result = self.result(proc)
                self.assertFalse(result["ok"])
                self.assertEqual(result["engine"], "codex")
                self.assertIn(expected, result["error"])

    def test_target_git_and_engine_readiness_errors_are_clear(self) -> None:
        unmanaged = self.root / "unmanaged"
        unmanaged.mkdir()
        no_target = self.run_cli("workbench", "Inspect.", "--json", cwd=unmanaged)
        self.assertEqual(no_target.returncode, 6)
        self.assertIn("ContextKit-managed target project", self.result(no_target)["error"])

        non_git = self.root / "non-git"
        non_git.mkdir()
        initialized = self.run_cli("init", "--with-layers", "--json", cwd=non_git)
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        no_git = self.run_cli("workbench", "Inspect.", "--json", cwd=non_git)
        self.assertEqual(no_git.returncode, 6)
        self.assertIn("inside a Git repository", self.result(no_git)["error"])

        env = dict(os.environ)
        env["PATH"] = "/usr/bin:/bin"
        env["CAPABILITIES_MANAGER"] = str(CAPABILITIES_PROVIDER)
        no_engine = subprocess.run(
            [str(CONTEXTKIT), "workbench", "Inspect.", "--json"],
            cwd=self.project,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(no_engine.returncode, 6)
        self.assertIn("is not on PATH", self.result(no_engine)["error"])

    def test_workbench_guide_help_and_release_surface_are_discoverable(self) -> None:
        guide = self.run_cli("guide", "workbench")
        self.assertEqual(guide.returncode, 0, guide.stderr)
        self.assertIn("# Workbench Guide", guide.stdout)
        self.assertIn("Treat the target's context", guide.stdout)
        self.assertIn("v1 workbench adapter uses Codex", guide.stdout)

        help_result = self.run_cli("help")
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("contextkit workbench", help_result.stdout)
        self.assertNotIn("--engine codex|claude", help_result.stdout)

        command_help = self.run_cli("workbench", "--help")
        self.assertEqual(command_help.returncode, 0, command_help.stderr)
        self.assertNotIn("--engine", command_help.stdout)

        release = json.loads((REPO_ROOT / "release.json").read_text())
        self.assertIn("guides/workbench.md", release["files"])


if __name__ == "__main__":
    unittest.main()
