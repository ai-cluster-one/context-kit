from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import tomllib
import unittest
import uuid
from pathlib import Path

import codex_home  # noqa: F401  (isolates the Codex user config and the store)
from test_identity import png_bytes


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTEXTKIT = REPO_ROOT / "bin" / "contextkit"

# Stand-ins for capabilities-contract and psycopg: importing either records the
# attempt and fails, as on a machine where neither is installed.
BLOCKED_MODULE = """\
import os
with open(os.environ["CONTEXTKIT_TEST_IMPORT_LOG"], "a") as log:
    log.write(__name__ + "\\n")
raise ImportError(f"{__name__} is not installed")
"""


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class RegistryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / "my-agent"
        self.project.mkdir()
        self.extra_env: dict[str, str] = {}

    def run_cli(self, *args: str, manager: Path = CONTEXTKIT, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(manager), *args],
            cwd=str(self.project),
            env={**os.environ, **self.extra_env, **(env or {})},
            text=True,
            capture_output=True,
            timeout=60,
            check=False,
        )

    def run_json(self, *args: str, **kwargs) -> dict:
        result = self.run_cli(*args, "--json", **kwargs)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def config(self) -> dict:
        return tomllib.loads((self.project / ".contextkit" / "config.toml").read_text())


class NoStoreTests(RegistryTestCase):
    def test_writes_skip_the_registry_and_report_it(self) -> None:
        initialized = self.run_json("init", "--with-layers")
        self.assertEqual(initialized["store"]["state"], "not_configured")
        self.assertIn("skipped", initialized["store"]["detail"])
        built = self.run_json("build")
        self.assertEqual(built["store"], initialized["store"])
        self.assertEqual(self.run_json("identity", "set", "--name", "Ada")["store"]["state"], "not_configured")
        self.assertEqual(self.run_json("identity", "clear", "--name")["store"]["state"], "not_configured")
        self.assertEqual(self.run_json("identity", "adopt")["store"]["state"], "not_configured")
        self.assertNotIn("store", self.run_json("identity", "show"))
        text = self.run_cli("identity", "set", "--description", "Helps.")
        self.assertEqual(text.returncode, 0, text.stderr)
        self.assertIn("Agents registry: not_configured - no store is configured; the agents registry write is skipped", text.stdout)

    def test_doctor_reports_no_store_as_information(self) -> None:
        self.run_json("init", "--with-layers")
        report = self.run_json("doctor")
        self.assertEqual(report["store"], {"configured": False, "state": "not_configured", "detail": "no store is configured"})
        self.assertTrue(report["ok"], report["problems"])
        text = self.run_cli("doctor")
        self.assertEqual(text.returncode, 0, text.stderr)
        self.assertIn("Store:\n- Agents registry: not_configured - no store is configured. This is information, not a problem.", text.stdout)

    def test_a_store_setting_in_the_project_env_file_counts_as_configured(self) -> None:
        self.run_json("init", "--with-layers")
        env_local = self.project / ".env.local"
        env_local.write_text(env_local.read_text() + "\n# AGENTKIT_DB_URL=postgresql://commented/out\nAGENTKIT_DB_URL=\n")
        self.assertEqual(self.run_json("build")["store"]["state"], "not_configured")
        env_local.write_text(env_local.read_text() + "export AGENTKIT_DB_URL='postgresql://127.0.0.1:1/none?sslmode=disable'\n")
        self.assertTrue(self.run_json("build")["store"]["configured"])

    def test_the_machine_store_setting_counts_as_configured(self) -> None:
        self.run_json("init", "--with-layers")
        config_home = self.root / "config"
        (config_home / "agentkit").mkdir(parents=True)
        (config_home / "agentkit" / "store.json").write_text("{}")
        self.assertTrue(self.run_json("build", env={"XDG_CONFIG_HOME": str(config_home)})["store"]["configured"])


class WithoutStoreLibrariesTests(RegistryTestCase):
    """ContextKit installs and runs unchanged where capabilities-contract and psycopg are absent."""

    def setUp(self) -> None:
        super().setUp()
        blocked = self.root / "blocked"
        for name in ("capabilities_contract", "psycopg"):
            (blocked / name).mkdir(parents=True)
            (blocked / name / "__init__.py").write_text(BLOCKED_MODULE)
        self.import_log = self.root / "imports.log"
        self.extra_env = {"PYTHONPATH": str(blocked), "CONTEXTKIT_TEST_IMPORT_LOG": str(self.import_log)}

    def install(self) -> Path:
        """Install this checkout as a release through the manager's own update, and return the installed manager."""
        remote, ref = self.root / "remote", "test-ref"
        files: dict[str, str] = {}
        for rel in json.loads((REPO_ROOT / "release.json").read_text())["files"]:
            destination = remote / ref / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / rel, destination)
            files[rel] = hashlib.sha256(destination.read_bytes()).hexdigest()
        manifest = {**json.loads((REPO_ROOT / "release.json").read_text()), "files": files}
        (remote / ref / "release.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        self.extra_env.update({
            "HOME": str(self.root / "home"),
            "CONTEXTKIT_HOME": str(self.root / "installed"),
            "CONTEXTKIT_BIN": str(self.root / "bin"),
            "CONTEXTKIT_RAW_BASE": remote.as_uri(),
            "CONTEXTKIT_REF": ref,
        })
        installed = self.run_json("update", "--apply", "--yes")
        self.assertEqual(installed["status"], "updated")
        return self.root / "bin" / "contextkit"

    def test_install_build_identity_and_doctor_never_load_them_without_a_store(self) -> None:
        manager = self.install()
        self.assertEqual(self.run_json("init", "--with-layers", manager=manager)["store"]["state"], "not_configured")
        self.assertEqual(self.run_json("build", manager=manager)["store"]["state"], "not_configured")
        self.assertEqual(self.run_json("identity", "set", "--name", "Ada", manager=manager)["store"]["state"], "not_configured")
        self.assertEqual(self.run_json("identity", "clear", "--name", manager=manager)["store"]["state"], "not_configured")
        self.assertEqual(self.run_json("identity", "adopt", manager=manager)["store"]["state"], "not_configured")
        doctor = self.run_json("doctor", manager=manager)
        self.assertTrue(doctor["ok"], doctor["problems"])
        self.assertEqual(doctor["store"]["state"], "not_configured")
        self.assertFalse(self.import_log.exists(), "no store library is imported without a store")

    def test_a_configured_store_without_the_library_is_reported_and_changes_no_result(self) -> None:
        self.run_json("init", "--with-layers")
        store = {"AGENTKIT_DB_URL": "postgresql://127.0.0.1:1/none?sslmode=disable"}
        built = self.run_json("build", env=store)
        self.assertEqual(built["store"]["state"], "unavailable")
        self.assertIn("capabilities-contract is not installed", built["store"]["detail"])
        doctor = self.run_json("doctor", env=store)
        self.assertTrue(doctor["ok"], doctor["problems"])
        self.assertEqual(doctor["store"]["state"], "unavailable")
        self.assertEqual(self.import_log.read_text().split(), ["capabilities_contract", "capabilities_contract"])


def _store_libraries_ready() -> bool:
    if not (shutil.which("initdb") and shutil.which("pg_ctl")):
        return False
    if importlib.util.find_spec("psycopg") is None or importlib.util.find_spec("capabilities_contract") is None:
        return False
    from capabilities_contract import db

    return hasattr(db, "resolve_setting")


@unittest.skipUnless(_store_libraries_ready(), "needs initdb, pg_ctl, psycopg and capabilities-contract 0.4+")
class StoreTests(RegistryTestCase):
    """The agents registry against a throwaway local PostgreSQL."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.cluster = Path(tempfile.mkdtemp(prefix="contextkit-test-store-"))
        cls.port = free_port()
        data = cls.cluster / "data"
        subprocess.run(["initdb", "-D", str(data), "-U", "admin", "--auth=trust", "--no-locale", "-E", "UTF8"],
                       check=True, capture_output=True, env={**os.environ, "LC_ALL": "C"})
        subprocess.run(
            ["pg_ctl", "-D", str(data), "-w", "-l", str(cls.cluster / "log"),
             "-o", f"-p {cls.port} -c unix_socket_directories= -c listen_addresses=127.0.0.1", "start"],
            check=True, capture_output=True, env={**os.environ, "LC_ALL": "C"},
        )
        cls.url = f"postgresql://admin@127.0.0.1:{cls.port}/postgres?sslmode=disable"

    @classmethod
    def tearDownClass(cls) -> None:
        subprocess.run(["pg_ctl", "-D", str(cls.cluster / "data"), "-m", "immediate", "stop"], capture_output=True)
        shutil.rmtree(cls.cluster, ignore_errors=True)

    def setUp(self) -> None:
        super().setUp()
        self.schema = f"t{uuid.uuid4().hex[:12]}"
        self.extra_env = {"AGENTKIT_DB_URL": self.url, "AGENTKIT_DB_SCHEMA": self.schema}

    def query(self, sql: str, *params) -> list[tuple]:
        import psycopg

        with psycopg.connect(self.url, autocommit=True) as conn:
            conn.execute(f"SET search_path TO {self.schema}")
            cursor = conn.execute(sql, params)
            return cursor.fetchall() if cursor.description else []

    def rows(self) -> list[tuple]:
        return self.query("SELECT id, name, description, icon_sha, icon, created_at, updated_at FROM contextkit_agents")

    def test_the_table_holds_the_agreed_columns(self) -> None:
        self.run_json("init", "--with-layers")
        columns = self.query(
            "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = 'contextkit_agents' ORDER BY ordinal_position",
            self.schema,
        )
        self.assertEqual(columns, [
            ("id", "text", "NO"),
            ("name", "text", "YES"),
            ("description", "text", "YES"),
            ("icon_sha", "text", "YES"),
            ("icon", "bytea", "YES"),
            ("created_at", "timestamp with time zone", "NO"),
            ("updated_at", "timestamp with time zone", "NO"),
        ])

    def test_identity_writes_upsert_the_row_and_name_holds_only_a_set_name(self) -> None:
        initialized = self.run_json("init", "--with-layers")
        self.assertEqual(initialized["store"]["state"], "created")
        project_id = self.config()["identity"]["id"]
        self.assertEqual([row[:5] for row in self.rows()], [(project_id, None, None, None, None)])

        icon = self.root / "icon.png"
        icon.write_bytes(png_bytes())
        written = self.run_json("identity", "set", "--name", "Ada", "--description", "Helps.", "--icon", str(icon))
        self.assertEqual(written["store"]["state"], "updated")
        self.assertEqual(
            [row[:5] for row in self.rows()],
            [(project_id, "Ada", "Helps.", hashlib.sha256(png_bytes()).hexdigest(), png_bytes())],
        )
        self.assertEqual(self.run_json("identity", "clear", "--name", "--icon")["store"]["state"], "updated")
        self.assertEqual([row[:5] for row in self.rows()], [(project_id, None, "Helps.", None, None)])

    def test_build_reconciles_and_reruns_converge(self) -> None:
        self.run_json("init", "--with-layers")
        self.run_json("identity", "set", "--name", "Ada")
        [before] = self.rows()
        self.assertEqual(self.run_json("build")["store"]["state"], "unchanged")
        self.assertEqual(self.run_json("build")["store"]["state"], "unchanged")
        self.assertEqual(self.rows(), [before])

        config = self.project / ".contextkit" / "config.toml"
        config.write_text(config.read_text().replace('name = "Ada"', 'name = "Grace"'))
        time.sleep(0.01)
        self.assertEqual(self.run_json("build")["store"]["state"], "updated")
        [after] = self.rows()
        self.assertEqual(after[1], "Grace")
        self.assertEqual(after[5], before[5], "created_at is kept")
        self.assertGreater(after[6], before[6], "updated_at moves when content changes")

    def test_the_file_wins_for_id_and_content(self) -> None:
        self.run_json("init", "--with-layers")
        project_id = self.config()["identity"]["id"]
        self.query("UPDATE contextkit_agents SET name = 'Changed in the store'")
        self.assertEqual(self.run_json("build")["store"]["state"], "updated")
        self.assertEqual([(row[0], row[1]) for row in self.rows()], [(project_id, None)])

        self.query("DELETE FROM contextkit_agents")
        self.assertEqual(self.run_json("build")["store"]["state"], "created")
        self.assertEqual([row[0] for row in self.rows()], [project_id])

    def test_no_path_or_secret_enters_the_store(self) -> None:
        self.extra_env["AGENTKIT_DB_URL"] = self.url.replace("admin@", "admin:not-a-real-secret@")
        self.run_json("init", "--with-layers")
        self.run_json("identity", "set", "--name", "Ada")
        tables = self.query("SELECT table_name FROM information_schema.tables WHERE table_schema = %s ORDER BY 1", self.schema)
        self.assertEqual(tables, [("contextkit_agents",), ("schema_ledger",), ("schema_version",)])
        stored = repr(self.rows())
        for value in (str(self.project), str(self.root), "not-a-real-secret", "my-agent"):
            self.assertNotIn(value, stored)

    def test_doctor_reports_store_state_as_information(self) -> None:
        self.extra_env = {}
        self.run_json("init", "--with-layers")
        self.extra_env = {"AGENTKIT_DB_URL": self.url, "AGENTKIT_DB_SCHEMA": self.schema}
        pending = self.run_json("doctor")
        self.assertTrue(pending["ok"], pending["problems"])
        self.assertEqual(pending["store"]["state"], "table_pending")
        self.assertEqual(self.query("SELECT count(*) FROM information_schema.tables WHERE table_schema = %s", self.schema), [(0,)])

        self.run_json("build")
        present = self.run_json("doctor")
        self.assertEqual(present["store"]["state"], "row_present")
        self.assertTrue(present["ok"], present["problems"])
        self.query("DELETE FROM contextkit_agents")
        self.assertEqual(self.run_json("doctor")["store"]["state"], "row_absent")

    def test_an_unreachable_store_changes_no_result(self) -> None:
        self.run_json("init", "--with-layers")
        self.extra_env["AGENTKIT_DB_URL"] = f"postgresql://admin@127.0.0.1:{free_port()}/postgres?sslmode=disable"
        built = self.run_cli("build", "--json")
        self.assertEqual(built.returncode, 0, built.stderr)
        self.assertEqual(json.loads(built.stdout)["store"]["error"], "store_unreachable")
        doctor = self.run_cli("doctor", "--json")
        self.assertEqual(doctor.returncode, 0, doctor.stderr)
        report = json.loads(doctor.stdout)
        self.assertTrue(report["ok"], report["problems"])
        self.assertEqual(report["store"]["state"], "error")


if __name__ == "__main__":
    unittest.main()
