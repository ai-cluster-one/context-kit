from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTEXTKIT = REPO_ROOT / "bin" / "contextkit"
CAPABILITIES_PROVIDER = REPO_ROOT / "tests" / "fixtures" / "capabilities"


class BodyRootTests(unittest.TestCase):
    def run_cli(self, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env["CAPABILITIES_MANAGER"] = str(CAPABILITIES_PROVIDER)
        env.pop("CONTEXTKIT_MEMORY_DIR", None)
        return subprocess.run(
            [str(CONTEXTKIT), *args],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def project(self, temp: str) -> Path:
        project = Path(temp).resolve() / "project"
        project.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=project, check=True)
        return project

    def write_config(self, project: Path, body: str) -> None:
        (project / ".contextkit").mkdir(exist_ok=True)
        (project / ".contextkit" / "config.toml").write_text(body)

    def doctor_json(self, project: Path) -> dict:
        result = self.run_cli("doctor", "--json", cwd=project)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_default_body_root_keeps_layers_at_the_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.project(temp)
            initialized = self.run_cli("init", "--with-layers", "--json", cwd=project)
            self.assertEqual(initialized.returncode, 0, initialized.stderr)

            self.assertTrue((project / "context").is_dir())
            self.assertTrue((project / "assets" / "sessions").is_dir())
            self.assertTrue((project / "routines").is_dir())
            report = self.doctor_json(project)
            self.assertEqual(report["body_root"], ".")

    def test_body_root_collapses_the_visible_body_into_one_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.project(temp)
            initialized = self.run_cli(
                "init", "--with-template", "--body-root", "agent", "--json", cwd=project
            )
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            self.assertEqual(json.loads(initialized.stdout)["body_root"], "agent")

            for rel in ("context", "assets/sessions", "assets/plans", "assets/research", "routines"):
                with self.subTest(layer=rel):
                    self.assertTrue((project / "agent" / rel).is_dir())
                    self.assertFalse((project / rel).exists())

            starters = list((project / "agent" / "context").rglob("*.md"))
            self.assertTrue(starters, "starter templates should land under the body root")

    def test_capabilities_envelope_stays_at_the_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.project(temp)
            self.run_cli("init", "--with-layers", "--body-root", "agent", "--json", cwd=project)

            self.assertTrue((project / "capabilities" / "settings.json").is_file())
            self.assertFalse((project / "agent" / "capabilities").exists())
            report = self.doctor_json(project)
            resolved = Path(report["layers"]["capabilities"]["path"]).resolve()
            self.assertEqual(resolved, (project / "capabilities").resolve())

    def test_memory_resolves_under_the_body_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.project(temp)
            self.run_cli("init", "--with-layers", "--body-root", "agent", "--json", cwd=project)

            added = self.run_cli("memory", "add", "--title", "Note", "Body root note.", "--json", cwd=project)
            self.assertEqual(added.returncode, 0, added.stderr)
            self.assertTrue(json.loads(added.stdout)["path"].startswith("agent/memory/"))
            self.assertTrue((project / "agent" / "memory").is_dir())
            self.assertFalse((project / "memory").exists())

            status = self.run_cli("memory", "status", cwd=project)
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertIn("Source: `agent/memory`", status.stdout)

    def test_memory_is_nameable_like_any_other_layer(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.project(temp)
            self.run_cli("init", "--with-layers", "--body-root", "agent", "--json", cwd=project)
            self.write_config(
                project,
                'version = 1\ntype = "agent-project"\n\n[body]\nroot = "agent"\n\n[sources]\nmemory = "notes"\n',
            )

            resolved = self.run_cli("path", "memory", cwd=project)
            self.assertEqual(resolved.returncode, 0, resolved.stderr)
            self.assertEqual(Path(resolved.stdout.strip()), project / "agent" / "notes")

            added = self.run_cli("memory", "add", "--title", "Note", "Named memory layer.", "--json", cwd=project)
            self.assertEqual(added.returncode, 0, added.stderr)
            self.assertTrue(json.loads(added.stdout)["path"].startswith("agent/notes/"))
            self.assertFalse((project / "agent" / "memory").exists())

    def test_memory_dir_env_still_overrides_the_configured_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.project(temp)
            self.run_cli("init", "--with-layers", "--body-root", "agent", "--json", cwd=project)
            external = Path(temp).resolve() / "external-memory"
            external.mkdir()

            env = dict(os.environ)
            env["CAPABILITIES_MANAGER"] = str(CAPABILITIES_PROVIDER)
            env["CONTEXTKIT_MEMORY_DIR"] = str(external)
            status = subprocess.run(
                [str(CONTEXTKIT), "memory", "status"],
                cwd=project, env=env, text=True, capture_output=True, check=False,
            )
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertIn("$CONTEXTKIT_MEMORY_DIR", status.stdout)
            self.assertIn("environment-configured", status.stdout)

    def test_absent_memory_layer_is_not_a_doctor_problem(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.project(temp)
            self.run_cli("init", "--with-layers", "--body-root", "agent", "--json", cwd=project)

            self.assertFalse((project / "agent" / "memory").exists())
            report = self.doctor_json(project)
            self.assertIn("memory", report["layers"])
            self.assertFalse(report["layers"]["memory"]["present"])
            self.assertEqual([p for p in report["problems"] if "memory" in p], [])
            self.assertTrue(report["ok"], report["problems"])

    def test_generated_context_references_the_configured_body_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.project(temp)
            self.run_cli("init", "--with-template", "--body-root", "agent", "--json", cwd=project)
            built = self.run_cli("build", "--target", "claude", cwd=project)
            self.assertEqual(built.returncode, 0, built.stderr)

            generated = (project / ".claude" / "rules" / "CONTEXT.md").read_text()
            self.assertIn("agent/context/", generated)
            self.assertIn("visible body under `agent/`", generated)

    def test_source_names_the_layer_inside_the_body_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.project(temp)
            self.write_config(
                project,
                'version = 1\ntype = "agent-project"\n\n[body]\nroot = "agent"\n\n[sources]\nroutines = "playbooks"\n',
            )
            report = self.doctor_json(project)
            layers = {name: Path(item["path"]).relative_to(project).as_posix()
                      for name, item in report["layers"].items()}
            self.assertEqual(layers["context"], "agent/context")
            self.assertEqual(layers["assets"], "agent/assets")
            self.assertEqual(layers["routines"], "agent/playbooks")
            self.assertEqual(layers["capabilities"], "capabilities")

    def test_legacy_dot_capabilities_source_survives_a_body_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.project(temp)
            self.write_config(
                project,
                'version = 1\ntype = "agent-project"\n\n[body]\nroot = "agent"\n\n[sources]\ncapabilities = ".capabilities"\n',
            )
            report = self.doctor_json(project)
            layers = {name: Path(item["path"]).relative_to(project).as_posix()
                      for name, item in report["layers"].items()}
            self.assertEqual(layers["capabilities"], ".capabilities")

    def test_hidden_and_escaping_source_paths_are_rejected(self) -> None:
        cases = {
            "context": ".hidden",
            "assets": "../outside",
            "routines": "/abs/path",
            "capabilities": ".",
        }
        for layer, value in cases.items():
            with self.subTest(layer=layer), tempfile.TemporaryDirectory() as temp:
                project = self.project(temp)
                self.write_config(
                    project,
                    f'version = 1\ntype = "agent-project"\n\n[body]\nroot = "agent"\n\n[sources]\n{layer} = "{value}"\n',
                )
                result = self.run_cli("doctor", cwd=project)
                self.assertEqual(result.returncode, 6, result.stdout)
                self.assertIn(f"invalid source path for {layer}", result.stderr)

    def test_invalid_body_roots_are_rejected(self) -> None:
        cases = {
            ".agent": "visible",
            "../outside": "relative path inside the project",
            "/abs/path": "relative path inside the project",
            "": "non-empty path string",
        }
        for value, expected in cases.items():
            with self.subTest(body_root=value), tempfile.TemporaryDirectory() as temp:
                project = self.project(temp)
                self.write_config(
                    project,
                    f'version = 1\ntype = "agent-project"\n\n[body]\nroot = "{value}"\n',
                )
                result = self.run_cli("doctor", cwd=project)
                self.assertEqual(result.returncode, 6, result.stdout)
                self.assertIn(expected, result.stderr)

    def test_migration_plan_targets_the_configured_body_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.project(temp)
            (project / ".context").mkdir()
            (project / ".context" / "A.md").write_text("legacy\n")
            self.write_config(project, 'version = 1\ntype = "agent-project"\n\n[body]\nroot = "agent"\n')

            plan = self.run_cli("migrate", "--plan", cwd=project)
            self.assertEqual(plan.returncode, 0, plan.stderr)
            self.assertIn("Rename `.context/` to `agent/context/`", plan.stdout)
            self.assertIn("git mv .context agent/context", plan.stdout)

    def test_body_root_conflict_with_existing_config_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = self.project(temp)
            self.write_config(project, 'version = 1\ntype = "agent-project"\n\n[body]\nroot = "agent"\n')

            result = self.run_cli("init", "--body-root", "workbench", "--json", cwd=project)
            self.assertEqual(result.returncode, 6, result.stdout)
            self.assertIn("conflicts with the existing body root", result.stderr)


if __name__ == "__main__":
    unittest.main()
