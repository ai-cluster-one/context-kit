from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

import codex_home  # noqa: F401  (isolates the Codex user config)
from test_identity import png_bytes


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTEXTKIT = REPO_ROOT / "bin" / "contextkit"
PERSONAL_AGENT = REPO_ROOT / "templates" / "agents" / "personal-agent"

# A capabilities manager stand-in that offers `capabilities agent`: it mints the
# project id into project.json on `init`, keeps the agent registry rows in a JSON
# file, and answers store_not_configured when STUB_NO_STORE is set.
STUB_MANAGER = r'''#!/usr/bin/env python3
import hashlib, json, os, secrets, sys, tomllib
from pathlib import Path

state = Path(os.environ["STUB_STATE"])
args = sys.argv[1:]
with (state / "calls.jsonl").open("a") as handle:
    handle.write(json.dumps(args) + "\n")
root = Path.cwd()
envelope = Path(os.environ.get("CAPABILITIES_PROJECT_ENVELOPE") or root / "capabilities")
identity_file = envelope / "project.json"
rows_file = state / "rows.json"
rows = json.loads(rows_file.read_text()) if rows_file.exists() else {}
no_store = bool(os.environ.get("STUB_NO_STORE"))


def die(code, slug, message):
    sys.stderr.write(json.dumps({"error": {"code": slug, "message": message}}) + "\n")
    sys.exit(code)


def project_id():
    try:
        return json.loads(identity_file.read_text()).get("id")
    except (OSError, ValueError):
        return None


def kernel_id():
    agent_id = project_id()
    if not agent_id:
        die(6, "no_project_identity", f"{identity_file} carries no project id")
    if no_store:
        die(6, "store_not_configured", "no database setting resolves for this project")
    return agent_id


def show(agent_id):
    row = rows.get(agent_id)
    agent = None if row is None else {key: value for key, value in row.items() if key != "icon"}
    return {"ok": True, "project": str(root), "agent_id": agent_id, "registered": row is not None,
            "agent": agent, "store": {"level": "machine", "schema": "agentkit"}}


if args == ["help"]:
    print("capabilities stand-in\n  agent show [--icon-out PATH]\n  agent set [--name TEXT]")
elif args == ["init"]:
    envelope.mkdir(parents=True, exist_ok=True)
    if not project_id():
        try:
            held = tomllib.loads((root / ".contextkit" / "config.toml").read_text()).get("identity", {}).get("id")
        except OSError:
            held = None
        identity_file.write_text(json.dumps({"schema": 1, "slug": root.name, "id": held or "prj_" + secrets.token_hex(6)}))
    print(json.dumps({"ok": True, "project": str(root)}))
elif args[:2] == ["agent", "show"]:
    agent_id = kernel_id()
    if "--icon-out" in args:
        icon = (rows.get(agent_id) or {}).get("icon")
        if not icon:
            die(6, "no_icon", "no icon")
        Path(args[args.index("--icon-out") + 1]).write_bytes(bytes.fromhex(icon))
    print(json.dumps(show(agent_id)))
elif args[:2] == ["agent", "set"]:
    agent_id = kernel_id()
    row = rows.setdefault(agent_id, dict.fromkeys(
        ("name", "description", "icon", "icon_sha", "onboarding_status", "onboarding_routine")))
    rest = [arg for arg in args[2:] if arg != "--json"]
    while rest:
        flag = rest.pop(0)
        if flag == "--no-icon":
            row["icon"] = row["icon_sha"] = None
            continue
        value = rest.pop(0)
        if flag == "--icon":
            data = Path(value).read_bytes()
            row["icon"], row["icon_sha"] = data.hex(), hashlib.sha256(data).hexdigest()
        else:
            column = flag[2:].replace("-", "_")
            row[column] = None if value.strip() in ("", "none") else value
    rows_file.write_text(json.dumps(rows))
    print(json.dumps(show(agent_id)))
elif args[:2] == ["store", "show"]:
    print(json.dumps({"configured": not no_store}))
elif args == ["context", "--fragment"]:
    print("# Capabilities\n\nStand-in block.")
elif args[:1] == ["enable"]:
    print(json.dumps({"enabled": args[1], "scope": "project"}))
elif args[:1] == ["list"]:
    names = ["mailbox", "whatsapp", "telegram", "calendar", "tasks", "automations"]
    print(json.dumps({"installed": [{"name": name, "effective": "enabled", "source": "project",
                                     "machine": "allowed"} for name in names]}))
else:
    die(64, "input", "unexpected call")
'''


class CapabilitiesAgentTests(unittest.TestCase):
    """ContextKit with a capabilities manager that owns the project id, the agent registry and onboarding."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.state = self.root / "stub-state"
        self.state.mkdir()
        self.manager = self.root / "capabilities"
        self.manager.write_text(STUB_MANAGER)
        self.manager.chmod(0o755)
        self.project = self.root / "my-agent"
        self.project.mkdir()

    def run_cli(self, *args: str, env: dict[str, str] | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        merged = dict(os.environ)
        merged.update({"CAPABILITIES_MANAGER": str(self.manager), "STUB_STATE": str(self.state)})
        merged.update(env or {})
        return subprocess.run([str(CONTEXTKIT), *args], cwd=str(cwd or self.project), env=merged,
                              text=True, capture_output=True, check=False)

    def run_json(self, *args: str, env: dict[str, str] | None = None) -> dict:
        result = self.run_cli(*args, "--json", env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def calls(self) -> list[list[str]]:
        path = self.state / "calls.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def rows(self) -> dict:
        path = self.state / "rows.json"
        return json.loads(path.read_text()) if path.exists() else {}

    def config(self) -> dict:
        return tomllib.loads((self.project / ".contextkit" / "config.toml").read_text())

    def project_json_id(self) -> str | None:
        path = self.project / "capabilities" / "project.json"
        return json.loads(path.read_text()).get("id") if path.is_file() else None

    def generated(self) -> str:
        return (self.project / ".contextkit" / "generated" / "context.md").read_text()

    def icon_file(self, body: bytes) -> Path:
        path = self.root / "icon-source.png"
        path.write_bytes(body)
        return path

    def test_init_takes_the_id_capabilities_init_mints_and_keeps_it_out_of_the_config(self) -> None:
        self.run_json("init", "--with-layers")
        project_id = self.project_json_id()
        self.assertRegex(project_id or "", r"^prj_[0-9a-f]{12}$")
        self.assertIn(["init"], self.calls())
        self.assertNotIn("id", self.config().get("identity", {}), "project.json is the id's one file home")
        self.assertEqual(self.run_json("identity", "show")["id"], project_id)
        adopted = self.run_json("identity", "adopt")
        self.assertEqual((adopted["id"], adopted["changed"]), (project_id, []))
        self.assertEqual(self.calls().count(["init"]), 1, "an id already in project.json is not minted again")

    def test_an_id_only_the_config_holds_stays_the_projects_id(self) -> None:
        released = self.run_cli("init", "--with-layers", "--json", env={"CAPABILITIES_MANAGER": str(self.root / "absent")})
        self.assertEqual(released.returncode, 0, released.stderr)
        held = self.config()["identity"]["id"]
        adopted = self.run_json("identity", "adopt")
        self.assertEqual((adopted["id"], adopted["id_source"], adopted["changed"]), (held, "config", []))
        self.assertEqual(self.project_json_id(), held, "capabilities init carries the config's id into project.json")
        self.assertEqual(self.config()["identity"]["id"], held)
        self.assertEqual(self.run_json("identity", "show")["id"], held)

    def test_identity_is_written_to_and_read_from_the_registry_row(self) -> None:
        initialized = self.run_json("init", "--with-layers")
        self.assertEqual(initialized["store"]["state"], "created", "init registers the agent")
        self.assertIn(self.project_json_id(), self.rows())
        body = png_bytes(0x33)
        report = self.run_json("identity", "set", "--name", "Ada", "--description", "Keeps the books.",
                               "--icon", str(self.icon_file(body)))
        self.assertEqual(report["changed"], ["name", "description", "icon"])
        self.assertEqual(report["store"]["state"], "updated")
        row = self.rows()[self.project_json_id()]
        self.assertEqual((row["name"], row["description"]), ("Ada", "Keeps the books."))
        self.assertEqual(row["icon_sha"], hashlib.sha256(body).hexdigest())
        self.assertEqual({key: value for key, value in self.config().get("identity", {}).items()}, {},
                         "the config holds no identity value the row owns")

        cached = self.project / ".contextkit" / f"icon-{hashlib.sha256(body).hexdigest()[:12]}.png"
        cached.unlink()
        shown = self.run_json("identity", "show")
        self.assertEqual((shown["name"], shown["name_source"], shown["description"]), ("Ada", "config", "Keeps the books."))
        self.assertEqual(Path(shown["icon"]), cached)
        self.assertEqual(cached.read_bytes(), body, "the row's icon is fetched into the binding folder")

        again = self.run_json("identity", "set", "--name", "Ada")
        self.assertEqual((again["changed"], again["unchanged"], again["store"]["state"]), ([], ["name"], "unchanged"))

        cleared = self.run_json("identity", "clear", "--name", "--icon")
        self.assertEqual(cleared["changed"], ["name", "icon"])
        row = self.rows()[self.project_json_id()]
        self.assertEqual((row["name"], row["icon_sha"], row["description"]), (None, None, "Keeps the books."))
        shown = self.run_json("identity", "show")
        self.assertEqual((shown["name"], shown["name_source"], shown["icon"]), ("my-agent", "folder", None))

    def test_build_moves_identity_and_onboarding_from_the_config_into_the_row(self) -> None:
        absent = {"CAPABILITIES_MANAGER": str(self.root / "absent")}
        self.assertEqual(self.run_cli("init", "--with-layers", env=absent).returncode, 0)
        body = png_bytes(0x44)
        self.assertEqual(self.run_cli("identity", "set", "--name", "Ada", "--description", "Keeps the books.",
                                      "--icon", str(self.icon_file(body)), env=absent).returncode, 0)
        (self.project / "routines" / "onboarding.md").write_text(
            "---\nname: onboarding\ndescription: Run first.\n---\n\n# Onboarding\n")
        config = self.project / ".contextkit" / "config.toml"
        config.write_text(config.read_text() + '\n[onboarding]\nstatus = "pending"\nroutine = "onboarding"\n')
        held = self.config()["identity"]["id"]
        self.assertIn("# Onboarding", self.run_cli("build", env=absent).stdout + self.generated())

        adopted = self.run_json("identity", "adopt")
        self.assertEqual(adopted["store"]["state"], "created")
        self.assertEqual(adopted["store"]["source"], "capabilities agent")
        row = self.rows()[held]
        self.assertEqual((row["name"], row["description"], row["icon_sha"]),
                         ("Ada", "Keeps the books.", hashlib.sha256(body).hexdigest()))
        self.assertEqual((row["onboarding_status"], row["onboarding_routine"]), ("pending", "onboarding"))
        self.assertEqual(self.config()["identity"], {"id": held}, "the id stays; the moved values leave the config")
        self.assertNotIn("onboarding", {key for key, value in self.config().items() if value})
        self.assertEqual(self.run_json("build")["store"]["state"], "unchanged")
        self.assertIn("# Onboarding", self.generated(), "the row's pending onboarding keeps the block")
        self.assertEqual(self.run_json("identity", "show")["name"], "Ada")

        status = self.run_json("onboarding", "status")
        self.assertEqual((status["status"], status["routine"]), ("pending", "onboarding"))
        completed = self.run_json("onboarding", "complete")
        self.assertTrue(completed["changed"])
        self.assertEqual(self.rows()[held]["onboarding_status"], "complete")
        self.assertNotIn("# Onboarding", self.generated())
        self.assertEqual(self.run_json("onboarding", "status")["status"], "complete")

    def test_without_a_database_identity_and_onboarding_stay_in_the_config(self) -> None:
        no_store = {"STUB_NO_STORE": "1"}
        self.run_json("init", "--with-layers", env=no_store)
        self.assertTrue(self.project_json_id(), "capabilities init mints the id without a database")
        report = self.run_json("identity", "set", "--name", "Ada", env=no_store)
        self.assertEqual(report["store"]["state"], "not_configured")
        self.assertEqual(self.config()["identity"]["name"], "Ada")
        self.assertEqual(self.rows(), {})
        self.assertEqual(self.run_json("identity", "show", env=no_store)["id"], self.project_json_id())

    def test_init_template_refuses_before_writing_when_no_database_resolves(self) -> None:
        result = self.run_cli("init", "--template", "personal-agent", "--json", env={"STUB_NO_STORE": "1"})
        self.assertEqual(result.returncode, 6, result.stderr)
        self.assertIn("capabilities store set", result.stderr)
        self.assertIn("AgentKit's database settings", result.stderr)
        self.assertEqual(list(self.project.iterdir()), [])
        self.assertFalse([call for call in self.calls() if call[:1] in (["enable"], ["init"])])

    def test_init_template_writes_identity_and_onboarding_to_the_row(self) -> None:
        report = self.run_json("init", "--template", "personal-agent", "--name", "Margaret")
        self.assertTrue(report["ok"])
        row = self.rows()[self.project_json_id()]
        manifest = tomllib.loads((PERSONAL_AGENT / "template.toml").read_text())
        self.assertEqual((row["name"], row["description"]), ("Margaret", manifest["description"]))
        self.assertEqual(row["icon_sha"], hashlib.sha256((PERSONAL_AGENT / "icon.png").read_bytes()).hexdigest())
        self.assertEqual((row["onboarding_status"], row["onboarding_routine"]), ("pending", "onboarding"))
        self.assertEqual(self.config().get("identity", {}), {})
        self.assertNotIn("onboarding", self.config())
        self.assertEqual(report["identity"]["name"], "Margaret")
        self.assertEqual(report["onboarding"]["status"], "pending")
        self.assertIn("# Onboarding", self.generated())

    def test_migrate_suggests_capabilities_init_until_project_json_exists(self) -> None:
        absent = {"CAPABILITIES_MANAGER": str(self.root / "absent")}
        self.assertEqual(self.run_cli("init", "--with-layers", env=absent).returncode, 0)

        def delegated() -> list[dict]:
            plan = json.loads(self.run_cli("migrate", "--plan", "--json", env=absent).stdout)
            return [step for steps in plan["sections"].values() for step in steps if step["action"] == "delegate"]

        self.assertEqual([(step["title"], step.get("command")) for step in delegated()],
                         [("capabilities/project.json", "capabilities init")])
        (self.project / "capabilities" / "project.json").write_text('{"id": "prj_0123456789ab"}\n')
        self.assertEqual(delegated(), [])


if __name__ == "__main__":
    unittest.main()
