from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTEXTKIT = REPO_ROOT / "bin" / "contextkit"


class AgentTeamTests(unittest.TestCase):
    def run_cli(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(CONTEXTKIT), *args],
            cwd=cwd or REPO_ROOT,
            env=dict(os.environ),
            text=True,
            capture_output=True,
            check=False,
        )

    def test_agent_team_guide_is_available_and_discoverable(self) -> None:
        guide = self.run_cli("guide", "agent-team")
        self.assertEqual(guide.returncode, 0, guide.stderr)
        self.assertIn("# Agent Team Guide", guide.stdout)
        self.assertIn("One review cycle is", guide.stdout)
        self.assertIn("three reviewer verdicts", guide.stdout)
        self.assertIn("Do not describe self-review", guide.stdout)

        help_result = self.run_cli("help")
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("agent-team", help_result.stdout)

        release = json.loads((REPO_ROOT / "release.json").read_text())
        self.assertIn("guides/agent-team.md", release["files"])

    def test_generated_context_offers_and_routes_agent_team_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"
            project.mkdir()

            initialized = self.run_cli("init", "--with-layers", "--json", cwd=project)
            self.assertEqual(initialized.returncode, 0, initialized.stderr)

            built = self.run_cli("build", "--target", "codex", cwd=project)
            self.assertEqual(built.returncode, 0, built.stderr)

            generated = (project / ".codex" / "generated" / "context.md").read_text()
            self.assertIn("offer the user Direct or Agent Team mode once", generated)
            self.assertIn("give execution to one subagent", generated)
            self.assertIn("`contextkit guide agent-team`", generated)
            self.assertIn("- `contextkit guide agent-team` - Agent Team Guide:", generated)
            self.assertEqual(generated.count("# Guide Menu"), 1)


if __name__ == "__main__":
    unittest.main()
