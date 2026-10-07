from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

import codex_home  # noqa: F401  (isolates the Codex user config)


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTEXTKIT = REPO_ROOT / "bin" / "contextkit"
PERSONAL_AGENT = REPO_ROOT / "templates" / "agents" / "personal-agent"
PERSONAL_CAPABILITIES = ["mailbox", "whatsapp", "telegram", "calendar", "tasks", "automations"]
PERSONAL_FILES = (
    "context/identity/AGENT.md", "context/identity/MISSION.md", "context/identity/OWNER.md",
    "context/identity/PEOPLE.md", "context/projects/PROJECTS.md", "context/guidelines/CONDUCT.md",
    "context/guidelines/COMMS.md", "context/guidelines/LIMITATIONS.md", "routines/onboarding.md",
    "routines/daily-brief.md",
)

# A capabilities manager stand-in: it records each call, enables what it is
# asked to unless the capability is named in STUB_FAIL, lists only what is
# "installed", and answers the context fragment the build asks for.
STUB_MANAGER = """#!/usr/bin/env python3
import json, os, sys
from pathlib import Path

state = Path(os.environ["STUB_STATE"])
calls = state / "calls.jsonl"
with calls.open("a") as handle:
    handle.write(json.dumps({"argv": sys.argv[1:], "envelope": os.environ.get("CAPABILITIES_PROJECT_ENVELOPE"),
                             "project_id": os.environ.get("CAPABILITIES_PROJECT_ID")}) + "\\n")
fail = set(filter(None, os.environ.get("STUB_FAIL", "").split(",")))
missing = set(filter(None, os.environ.get("STUB_MISSING", "").split(",")))
enabled_file = state / "enabled.json"
enabled = json.loads(enabled_file.read_text()) if enabled_file.exists() else []
args = sys.argv[1:]
if args[:1] == ["enable"]:
    name = args[1]
    if name in fail:
        print(json.dumps({"error": {"code": "stub", "message": f"stub refuses {name}"}}))
        sys.exit(5)
    enabled.append(name)
    enabled_file.write_text(json.dumps(enabled))
    print(json.dumps({"enabled": name, "scope": "project"}))
elif args[:1] == ["list"]:
    known = ["mailbox", "whatsapp", "telegram", "calendar", "tasks", "automations", "extra"]
    rows = [{"name": name, "effective": "enabled" if name in enabled else "disabled",
             "source": "project" if name in enabled else "default", "machine": "allowed"}
            for name in known if name not in missing]
    print(json.dumps({"installed": rows}))
elif args == ["context", "--fragment"]:
    print("# Capabilities\\n\\n" + "\\n".join(f"## {name}" for name in enabled))
else:
    print("unexpected call", file=sys.stderr)
    sys.exit(64)
"""


class AgentTemplateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.state = self.root / "stub-state"
        self.state.mkdir()
        self.manager = self.root / "capabilities"
        self.manager.write_text(STUB_MANAGER)
        self.manager.chmod(0o755)
        self.project = self.root / "new-agent"
        self.project.mkdir()

    def run_cli(self, *args: str, cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        merged = dict(os.environ)
        merged.update({"CAPABILITIES_MANAGER": str(self.manager), "STUB_STATE": str(self.state)})
        merged.update(env or {})
        return subprocess.run(
            [str(CONTEXTKIT), *args],
            cwd=str(cwd or self.project),
            env=merged,
            text=True,
            capture_output=True,
            check=False,
        )

    def manager_calls(self) -> list[dict]:
        path = self.state / "calls.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def config(self) -> dict:
        return tomllib.loads((self.project / ".contextkit" / "config.toml").read_text())

    def generated(self) -> str:
        return (self.project / ".contextkit" / "generated" / "context.md").read_text()

    def assert_body_ready_to_commit(self) -> None:
        """The folder is a repository whose body is untracked and ready to commit, as bootstrap leaves it."""
        status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=self.project,
                                text=True, capture_output=True, check=True).stdout.splitlines()
        untracked = {line[3:] for line in status if line.startswith("?? ")}
        for rel in (".contextkit/config.toml", "context/identity/AGENT.md", "routines/onboarding.md", ".gitignore"):
            self.assertIn(rel, untracked)
        self.assertNotIn(".contextkit/generated/context.md", untracked, "generated context stays ignored")
        self.assertNotIn(".env.local", untracked, "local env stays ignored")

    def create_agent(self, *args: str, env: dict[str, str] | None = None) -> tuple[subprocess.CompletedProcess[str], dict]:
        result = self.run_cli("init", "--template", "personal-agent", *args, "--json", env=env)
        return result, json.loads(result.stdout)

    def test_templates_json_lists_the_agent_templates(self) -> None:
        result = self.run_cli("templates", "--json", cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        listing = json.loads(result.stdout)
        self.assertTrue(listing["starter"], "the starter gallery stays listed")
        agents = {item["id"]: item for item in listing["agents"]}
        self.assertIn("personal-agent", agents)
        personal = agents["personal-agent"]
        self.assertEqual(personal["name"], "Personal Agent")
        self.assertTrue(personal["description"])
        self.assertEqual(Path(personal["icon"]), PERSONAL_AGENT / "icon.png")
        self.assertEqual(personal["capabilities"], PERSONAL_CAPABILITIES)
        self.assertEqual([item["name"] for item in personal["routines"]], ["daily-brief", "onboarding"])
        self.assertEqual(personal["onboarding"], {"routine": "onboarding"})
        self.assertTrue(personal["agent_names"])

    def test_plain_templates_shows_the_starter_gallery_and_names_agent_templates(self) -> None:
        result = self.run_cli("templates", cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("# ContextKit Templates", result.stdout)
        self.assertIn("`context/identity/AGENT.md`", result.stdout)
        self.assertIn("Agent templates:", result.stdout)
        self.assertIn("- `personal-agent` - Personal Agent", result.stdout)
        self.assertIn("contextkit init --template <id>", result.stdout)

    def test_init_template_creates_a_complete_agent_with_onboarding_pending(self) -> None:
        result, report = self.create_agent()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(report["ok"])
        self.assertEqual(report["template"], "personal-agent")

        for rel in PERSONAL_FILES + ("assets/sessions", "capabilities", ".contextkit/README.md"):
            self.assertTrue((self.project / rel).exists(), rel)
        self.assertFalse((self.project / "context" / "people").exists(), "People is one file")
        self.assertFalse((self.project / "template.toml").exists())

        config = self.config()
        manifest = tomllib.loads((PERSONAL_AGENT / "template.toml").read_text())
        self.assertIn(config["identity"]["name"], manifest["agent_names"])
        self.assertEqual(config["identity"]["description"], manifest["description"])
        self.assertRegex(config["identity"]["id"], r"^prj_[0-9a-f]{12}$")
        self.assertEqual(config["onboarding"], {"status": "pending", "routine": "onboarding"})
        icon = self.project / ".contextkit" / config["identity"]["icon"]
        self.assertEqual(icon.read_bytes(), (PERSONAL_AGENT / "icon.png").read_bytes())

        shown = json.loads(self.run_cli("identity", "show", "--json").stdout)
        self.assertEqual(shown["name"], config["identity"]["name"])
        self.assertEqual(shown["icon"], str(icon))

        self.assertEqual([item["name"] for item in report["capabilities"]], PERSONAL_CAPABILITIES)
        self.assertTrue(all(item["result"] == "enabled" for item in report["capabilities"]))
        enables = [call for call in self.manager_calls() if call["argv"][:1] == ["enable"]]
        self.assertEqual([call["argv"] for call in enables],
                         [["enable", name, "--project", "--json"] for name in PERSONAL_CAPABILITIES])
        self.assertTrue(all(call["envelope"] == str(self.project / "capabilities") for call in enables))
        self.assertTrue(all(call["project_id"] == config["identity"]["id"] for call in enables))

        self.assertTrue((self.project / ".claude" / "rules" / "CONTEXT.md").is_symlink())
        self.assertTrue((self.project / ".contextkit.md").is_symlink())
        self.assertTrue(report["git"]["initialized"])
        self.assert_body_ready_to_commit()
        generated = self.generated()
        self.assertIn("# Onboarding", generated)
        self.assertIn("[onboarding](routines/onboarding.md)", generated)
        self.assertIn("Finish it before other work", generated)
        self.assertLess(generated.index("# Onboarding"), generated.index("# Inline Context"))
        self.assertIn("## automations", generated, "the build runs after the capabilities are enabled")
        self.assertEqual((self.project / ".claude" / "rules" / "CONTEXT.md").read_text(), generated)

        audit = self.run_cli("audit", "--json")
        self.assertEqual(json.loads(audit.stdout)["findings"], [], "the template body passes the audit")

    def test_each_agent_gets_a_name_from_the_template_list(self) -> None:
        manifest = tomllib.loads((PERSONAL_AGENT / "template.toml").read_text())
        names = set()
        for index in range(6):
            project = self.root / f"agent-{index}"
            project.mkdir()
            result = self.run_cli("init", "--template", "personal-agent", "--no-trust", "--json", cwd=project)
            self.assertEqual(result.returncode, 0, result.stderr)
            names.add(json.loads(result.stdout)["identity"]["name"])
        self.assertTrue(names <= set(manifest["agent_names"]))

    def test_a_capability_that_fails_to_enable_is_named_and_fails_the_command(self) -> None:
        result, report = self.create_agent(env={"STUB_FAIL": "telegram", "STUB_MISSING": "calendar"})
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["ok"])
        by_name = {item["name"]: item for item in report["capabilities"]}
        self.assertEqual(by_name["telegram"]["result"], "failed")
        self.assertIn("stub refuses telegram", by_name["telegram"]["detail"])
        self.assertEqual(by_name["calendar"]["result"], "failed")
        self.assertIn("not installed", by_name["calendar"]["detail"])
        self.assertEqual(by_name["mailbox"]["result"], "enabled")
        self.assertIn("telegram", result.stderr)
        self.assertIn("calendar", result.stderr)
        # The body and the repository stay in place for the capabilities to be repaired.
        self.assertTrue((self.project / "routines" / "onboarding.md").is_file())
        self.assert_body_ready_to_commit()
        self.assertEqual(self.config()["onboarding"]["status"], "pending")
        self.assertIn("# Onboarding", self.generated())

    def test_without_a_manager_every_capability_fails(self) -> None:
        result, report = self.create_agent(env={"CAPABILITIES_MANAGER": str(self.root / "absent-manager")})
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(all(item["result"] == "failed" for item in report["capabilities"]))

    def test_text_output_lists_each_capability_with_its_result(self) -> None:
        result = self.run_cli("init", "--template", "personal-agent", env={"STUB_FAIL": "tasks"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("- mailbox: enabled", result.stdout)
        self.assertIn("- tasks: failed - stub refuses tasks", result.stdout)
        self.assertIn("Onboarding: pending (routine `onboarding`)", result.stdout)

    def test_init_template_refuses_a_folder_that_is_not_empty(self) -> None:
        (self.project / "notes.txt").write_text("mine\n")
        result = self.run_cli("init", "--template", "personal-agent", "--json")
        self.assertEqual(result.returncode, 6)
        self.assertIn("needs an empty folder", result.stderr)
        self.assertIn("notes.txt", result.stderr)
        self.assertEqual(sorted(path.name for path in self.project.iterdir()), ["notes.txt"])
        self.assertEqual(self.manager_calls(), [])

    def test_a_finder_marker_does_not_make_a_folder_non_empty(self) -> None:
        (self.project / ".DS_Store").write_bytes(b"\x00")
        result, _report = self.create_agent()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_an_existing_empty_repository_is_kept(self) -> None:
        subprocess.run(["git", "init", "-q"], cwd=self.project, check=True)
        result, report = self.create_agent()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(report["git"]["initialized"])
        self.assert_body_ready_to_commit()

    def test_refusals_leave_no_repository(self) -> None:
        self.run_cli("init", "--template", "no-such-agent")
        self.assertFalse((self.project / ".git").exists())
        (self.project / "notes.txt").write_text("mine\n")
        self.run_cli("init", "--template", "personal-agent")
        self.assertFalse((self.project / ".git").exists())

    def test_init_template_refuses_an_unknown_id_and_lists_the_available_ones(self) -> None:
        result = self.run_cli("init", "--template", "no-such-agent")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown agent template: no-such-agent", result.stderr)
        self.assertIn("personal-agent", result.stderr)
        self.assertEqual(list(self.project.iterdir()), [])

    def test_template_conflicts_with_the_starter_flags(self) -> None:
        result = self.run_cli("init", "--template", "personal-agent", "--with-template")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(list(self.project.iterdir()), [])
        result = self.run_cli("init", "--no-trust")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(list(self.project.iterdir()), [])

    def test_template_body_lands_under_the_body_root(self) -> None:
        result, report = self.create_agent("--body-root", "agent")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.project / "agent" / "context" / "identity" / "PEOPLE.md").is_file())
        self.assertTrue((self.project / "agent" / "routines" / "onboarding.md").is_file())
        self.assertFalse((self.project / "context").exists())
        self.assertIn("[onboarding](agent/routines/onboarding.md)", self.generated())
        self.assertEqual(report["onboarding"]["routine_path"], str(self.project / "agent" / "routines" / "onboarding.md"))

    def test_onboarding_status_and_complete(self) -> None:
        result, _report = self.create_agent()
        self.assertEqual(result.returncode, 0, result.stderr)

        status = json.loads(self.run_cli("onboarding", "status", "--json").stdout)
        self.assertEqual(status["status"], "pending")
        self.assertEqual(status["routine"], "onboarding")
        self.assertEqual(status["routine_path"], str(self.project / "routines" / "onboarding.md"))

        doctor = self.run_cli("doctor", "--json")
        self.assertEqual(doctor.returncode, 0, doctor.stderr)
        report = json.loads(doctor.stdout)
        self.assertTrue(report["ok"], report["problems"])
        self.assertEqual(report["onboarding"]["status"], "pending")
        doctor_text = self.run_cli("doctor").stdout
        self.assertIn("Status: ok", doctor_text)
        self.assertIn("This is information, not a problem.", doctor_text)

        completed = self.run_cli("onboarding", "complete", "--json")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["status"], "complete")
        self.assertTrue(report["changed"])
        self.assertEqual(self.config()["onboarding"], {"status": "complete", "routine": "onboarding"})
        self.assertNotIn("# Onboarding", self.generated())
        self.assertNotIn("# Onboarding", (self.project / ".claude" / "rules" / "CONTEXT.md").read_text())

        again = self.run_cli("onboarding", "complete", "--json")
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertFalse(json.loads(again.stdout)["changed"])
        self.assertEqual(json.loads(self.run_cli("onboarding", "status", "--json").stdout)["status"], "complete")
        self.assertIn("- Complete", self.run_cli("doctor").stdout)

    def test_onboarding_outside_a_template_agent(self) -> None:
        initialized = self.run_cli("init", "--with-layers", "--json")
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        status = json.loads(self.run_cli("onboarding", "status", "--json").stdout)
        self.assertEqual(status["status"], "none")
        completed = self.run_cli("onboarding", "complete")
        self.assertEqual(completed.returncode, 3)
        self.assertIn("no onboarding is tracked", completed.stderr)
        self.assertNotIn("onboarding", self.config())
        built = self.run_cli("build")
        self.assertEqual(built.returncode, 0, built.stderr)
        self.assertNotIn("# Onboarding", self.generated())

    def test_invalid_onboarding_state_is_refused(self) -> None:
        self.run_cli("init", "--with-layers", "--json")
        config = self.project / ".contextkit" / "config.toml"
        config.write_text(config.read_text() + '\n[onboarding]\nstatus = "halfway"\nroutine = "onboarding"\n')
        result = self.run_cli("onboarding", "status")
        self.assertEqual(result.returncode, 6)
        self.assertIn("invalid onboarding.status: halfway", result.stderr)

    def test_doctor_reports_a_pending_onboarding_whose_routine_is_gone(self) -> None:
        result, _report = self.create_agent()
        self.assertEqual(result.returncode, 0, result.stderr)
        (self.project / "routines" / "onboarding.md").unlink()
        report = json.loads(self.run_cli("doctor", "--json").stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(any("onboarding is pending but its routine" in problem for problem in report["problems"]))
        self.run_cli("build")
        self.assertIn("onboarding routine `onboarding` is not declared", self.generated())

    def test_a_template_must_carry_its_onboarding_routine(self) -> None:
        templates = self.root / "templates"
        shutil.copytree(REPO_ROOT / "templates", templates)
        broken = templates / "agents" / "personal-agent"
        (broken / "routines" / "onboarding.md").unlink()
        env = {"CONTEXTKIT_TEMPLATES_DIR": str(templates)}
        listed = self.run_cli("templates", "--json", cwd=self.root, env=env)
        self.assertEqual(listed.returncode, 6)
        self.assertIn("`[onboarding] routine` must name a routine the template carries", listed.stderr)
        created = self.run_cli("init", "--template", "personal-agent", env=env)
        self.assertEqual(created.returncode, 6)
        self.assertEqual(list(self.project.iterdir()), [])

    def test_a_template_file_outside_the_body_layers_is_refused(self) -> None:
        templates = self.root / "templates"
        shutil.copytree(REPO_ROOT / "templates", templates)
        (templates / "agents" / "personal-agent" / "NOTES.md").write_text("# Notes\n")
        result = self.run_cli("templates", "--json", cwd=self.root, env={"CONTEXTKIT_TEMPLATES_DIR": str(templates)})
        self.assertEqual(result.returncode, 6)
        self.assertIn("`NOTES.md` is outside the body layers", result.stderr)

    def test_help_and_readme_name_the_feature(self) -> None:
        help_text = self.run_cli("help", cwd=self.root).stdout
        self.assertIn("contextkit init --template <id>", help_text)
        self.assertIn("contextkit onboarding status", help_text)
        self.assertIn("contextkit onboarding complete", help_text)
        self.assertIn("contextkit templates [--json]", help_text)
        readme = (REPO_ROOT / "README.md").read_text()
        self.assertIn("contextkit init --template personal-agent", readme)
        guide = self.run_cli("guide", "bootstrap", cwd=self.root).stdout
        self.assertIn("## Agent Templates", guide)
        self.assertIn("template.toml", guide)


if __name__ == "__main__":
    unittest.main()
