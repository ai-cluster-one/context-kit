from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTEXTKIT = REPO_ROOT / "bin" / "contextkit"


class GroomTests(unittest.TestCase):
    def run_cli(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(CONTEXTKIT), *args],
            cwd=cwd or REPO_ROOT,
            env=dict(os.environ),
            text=True,
            capture_output=True,
            check=False,
        )

    def snapshot(self, root: Path) -> dict[str, bytes]:
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file() and ".git" not in path.relative_to(root).parts
        }

    def test_plain_groom_and_guide_render_the_owning_guide_without_state(self) -> None:
        expected = (REPO_ROOT / "guides" / "groom.md").read_text()
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            before = self.snapshot(project)

            plain = self.run_cli("groom", cwd=project)
            self.assertEqual(plain.returncode, 0, plain.stderr)
            self.assertEqual(plain.stdout, expected)
            self.assertEqual(self.snapshot(project), before)
            self.assertFalse((project / ".contextkit" / "groom").exists())

        guide = self.run_cli("guide", "groom")
        self.assertEqual(guide.returncode, 0, guide.stderr)
        self.assertEqual(guide.stdout, expected)

        help_result = self.run_cli("help")
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("contextkit groom [--plan|--apply]", help_result.stdout)
        self.assertIn("|groom|", help_result.stdout)

    def test_guide_owns_the_semantic_workflow_and_routes_other_owners(self) -> None:
        guide = (REPO_ROOT / "guides" / "groom.md").read_text()
        for expected in (
            "researcher subagent",
            "independent validator subagent",
            "separate executor subagent",
            "Return the actual diff to the validator",
            "Exclude active project memory",
            "`contextkit guide memory`",
            "do not report `PASS`",
            "Do not create packets, schemas, ledgers, JSON protocols, or persistent groom state",
            "shared global owners, external capability owners, and the ContextKit product owner",
            "`contextkit guide validation`",
        ):
            self.assertIn(expected, guide)

        audit = (REPO_ROOT / "guides" / "audit.md").read_text()
        self.assertIn("operational rule source for deterministic audits", audit)
        self.assertIn("Use `contextkit guide groom` for agent-driven semantic review", audit)

        readme = (REPO_ROOT / "README.md").read_text()
        self.assertIn("Open the agent-driven semantic grooming workflow", readme)
        self.assertIn("contextkit groom", readme)

    def test_legacy_modes_remain_bounded_and_do_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            initialized = self.run_cli("init", "--with-layers", "--json", cwd=project)
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            subprocess.run(["git", "init", "--quiet"], cwd=project, check=True)
            before = self.snapshot(project)

            plan = self.run_cli("groom", "--plan", cwd=project)
            self.assertEqual(plan.returncode, 0, plan.stderr)
            self.assertIn("deterministic audit findings only", plan.stdout)
            self.assertEqual(self.snapshot(project), before)

            applied = self.run_cli("groom", "--apply", cwd=project)
            self.assertEqual(applied.returncode, 0, applied.stderr)
            self.assertIn("does not apply semantic repairs", applied.stdout)
            self.assertEqual(self.snapshot(project), before)


if __name__ == "__main__":
    unittest.main()
