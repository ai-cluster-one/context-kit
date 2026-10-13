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

# Stand-ins for psycopg, ContextKit's only store dependency, and for
# capabilities-contract, which ContextKit never depends on: importing either
# records the attempt and fails, as on a machine where neither is installed.
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
        self.assertEqual(report["store"], {"configured": False, "state": "not_configured", "detail": "no store is configured", "level": "none"})
        self.assertTrue(report["ok"], report["problems"])
        text = self.run_cli("doctor")
        self.assertEqual(text.returncode, 0, text.stderr)
        self.assertIn("Store:\n- Agents registry: not_configured - no store is configured. This is information, not a problem.\n"
                      "- Store setting: none answers\n", text.stdout)

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


class SourceTests(unittest.TestCase):
    def test_no_shipped_file_imports_or_requires_capabilities_contract(self) -> None:
        for rel in [*json.loads((REPO_ROOT / "release.json").read_text())["files"], "install.sh"]:
            path = REPO_ROOT / rel
            if path.suffix == ".png":
                continue
            text = path.read_text()
            self.assertNotIn("capabilities_contract", text, rel)
            if rel.startswith(("bin/", "bundle/", "templates/")) or rel == "install.sh":
                self.assertNotIn("capabilities-contract", text, rel)


class BlockedLibrariesTestCase(RegistryTestCase):
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
        self.installed = self.run_json("update", "--apply", "--yes")
        self.assertEqual(self.installed["status"], "updated")
        return self.root / "bin" / "contextkit"


class WithoutStoreLibrariesTests(BlockedLibrariesTestCase):
    """ContextKit installs and runs unchanged where psycopg is absent, and never loads capabilities-contract."""

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
        self.assertEqual(built["store"]["error"], "driver_missing")
        self.assertIn("psycopg is not installed", built["store"]["detail"])
        doctor = self.run_json("doctor", env=store)
        self.assertTrue(doctor["ok"], doctor["problems"])
        self.assertEqual(doctor["store"]["state"], "unavailable")
        self.assertEqual(self.import_log.read_text().split(), ["psycopg", "psycopg"])


class StoreDriverTests(BlockedLibrariesTestCase):
    """The installed manager carries its own psycopg, installed by the manager's own update."""

    STORE = {"AGENTKIT_DB_URL": "postgresql://127.0.0.1:1/none?sslmode=disable"}

    def setUp(self) -> None:
        super().setUp()
        self.uv_log = self.root / "uv.log"
        self.extra_env["CONTEXTKIT_TEST_UV_LOG"] = str(self.uv_log)

    def driver(self) -> Path:
        return self.root / "installed" / ".driver"

    def uv_calls(self) -> list[str]:
        return self.uv_log.read_text().splitlines() if self.uv_log.exists() else []

    def test_update_installs_the_driver_and_the_installed_manager_loads_it(self) -> None:
        manager = self.install()
        driver = self.installed["store_driver"]
        self.assertEqual((driver["state"], driver["interpreter"]), ("present", sys.executable))
        self.assertEqual(Path(driver["path"]).parent, self.driver())
        [call] = self.uv_calls()
        self.assertIn(f"--python {sys.executable} ", call)
        self.assertTrue(call.endswith(" psycopg[binary]>=3.2,<4"), call)
        self.assertEqual(self.run_json("update", "--check")["store_driver"]["state"], "present")
        self.run_json("init", "--with-layers", manager=manager)
        store = self.run_json("build", manager=manager, env=self.STORE)["store"]
        self.assertEqual((store["state"], store["error"]), ("error", "store_unreachable"))
        self.assertIn("installed stand-in driver", store["detail"])
        self.assertFalse(self.import_log.exists(), "the interpreter's own psycopg is never reached")
        self.assertEqual(self.run_json("update", "--apply", "--yes")["store_driver"]["state"], "present")
        self.assertEqual(len(self.uv_calls()), 1, "a present driver is kept")

    def test_a_release_without_the_driver_installs_it_once_a_store_needs_it(self) -> None:
        manager = self.install()
        shutil.rmtree(self.driver())
        self.run_json("init", "--with-layers", manager=manager)
        self.assertEqual(self.run_json("build", manager=manager)["store"]["state"], "not_configured")
        self.assertFalse(self.driver().exists(), "nothing is installed without a store")
        store = self.run_json("build", manager=manager, env=self.STORE)["store"]
        self.assertEqual(store["error"], "store_unreachable")
        self.assertIn("installed stand-in driver", store["detail"])
        self.run_json("build", manager=manager, env=self.STORE)
        self.assertEqual(len(self.uv_calls()), 2, "one install by the update, one by the first store use")

    def test_a_failed_install_is_reported_once_and_update_apply_installs_it_again(self) -> None:
        self.extra_env["CONTEXTKIT_TEST_UV_FAIL"] = "no network"
        manager = self.install()
        driver = self.installed["store_driver"]
        self.assertEqual(driver["state"], "failed")
        self.assertIn("uv: error: no network", driver["detail"])
        self.run_json("init", "--with-layers", manager=manager)
        for _ in range(2):
            store = self.run_json("build", manager=manager, env=self.STORE)["store"]
            self.assertEqual((store["state"], store["error"]), ("unavailable", "driver_missing"))
            self.assertIn("uv: error: no network", store["detail"])
            self.assertIn("`contextkit update --apply` installs it again", store["detail"])
        self.assertEqual(len(self.uv_calls()), 1, "a recorded failure is not retried by every command")
        del self.extra_env["CONTEXTKIT_TEST_UV_FAIL"]
        self.assertEqual(self.run_json("update", "--check")["store_driver"]["state"], "failed")
        repaired = self.run_json("update", "--apply", "--yes")
        self.assertEqual((repaired["status"], repaired["store_driver"]["state"]), ("up_to_date", "present"))
        self.assertEqual(sorted(path.name for path in self.driver().iterdir()), [Path(repaired["store_driver"]["path"]).name])
        self.assertEqual(self.run_json("build", manager=manager, env=self.STORE)["store"]["error"], "store_unreachable")

    def test_a_checkout_never_installs_or_loads_a_driver(self) -> None:
        self.install()
        self.run_json("init", "--with-layers")
        store = self.run_json("build", env=self.STORE)["store"]
        self.assertEqual(store["error"], "driver_missing")
        self.assertEqual(len(self.uv_calls()), 1)


class StoreSettingTests(BlockedLibrariesTestCase):
    """ContextKit resolves the family store setting itself, level by level, before it loads psycopg."""

    REMOTE = "postgresql://admin@db.example.com:5432/agents"

    def setUp(self) -> None:
        super().setUp()
        self.run_json("init", "--with-layers")
        self.config_home = self.root / "config"
        self.extra_env["XDG_CONFIG_HOME"] = str(self.config_home)

    def machine_file(self, **fields) -> Path:
        path = self.config_home / "agentkit" / "store.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        setting = {"schema": "agentkit.store.v1", "host": "db.example.com", "port": 5432,
                   "database": "agents", "user": "admin", "sslmode": "require", **fields}
        path.write_text(json.dumps({key: value for key, value in setting.items() if value is not None}))
        return path

    def store(self, env: dict[str, str] | None = None) -> dict:
        return self.run_json("doctor", env=env)["store"]

    def test_the_project_env_files_answer_first_and_env_local_wins_key_by_key(self) -> None:
        self.machine_file()
        (self.project / ".env").write_text(f"AGENTKIT_DB_URL={self.REMOTE}?sslmode=prefer\nAGENTKIT_DB_SCHEMA=Not-A-Schema\n")
        store = self.store(env={"AGENTKIT_DB_URL": self.REMOTE})
        self.assertEqual((store["level"], store["source"]), ("project", str(self.project / ".env")))
        self.assertEqual(store["error"], "bad_schema_name")
        (self.project / ".env.local").write_text("AGENTKIT_DB_SCHEMA=agents_test\n")
        store = self.store()
        self.assertEqual(store["level"], "project")
        self.assertEqual(store["source"], f"{self.project / '.env.local'}, {self.project / '.env'}")
        self.assertEqual(store["error"], "sslmode_too_weak", "the URL still comes from .env")
        (self.project / ".env.local").write_text(f"AGENTKIT_DB_SCHEMA=agents_test\nAGENTKIT_DB_URL={self.REMOTE}\n")
        self.assertEqual(self.store()["error"], "driver_missing")

    def test_the_answering_level_is_used_whole(self) -> None:
        (self.project / ".env.local").write_text("AGENTKIT_DB_SCHEMA=agents_test\n")
        store = self.store(env={"AGENTKIT_DB_URL": self.REMOTE})
        self.assertEqual((store["level"], store["error"]), ("project", "bad_store_setting"))
        self.assertIn("AGENTKIT_DB_URL", store["detail"])

    def test_the_process_environment_answers_before_the_machine_file(self) -> None:
        self.machine_file()
        store = self.store(env={"AGENTKIT_DB_HOST": "db.example.com", "AGENTKIT_DB_NAME": "agents", "AGENTKIT_DB_USER": "admin"})
        self.assertEqual((store["level"], store["source"], store["error"]), ("environment", "process environment", "driver_missing"))
        store = self.store(env={"AGENTKIT_DB_HOST": "db.example.com", "AGENTKIT_DB_NAME": "agents", "AGENTKIT_DB_USER": "admin",
                                "AGENTKIT_DB_SSLMODE": "disable"})
        self.assertEqual(store["error"], "sslmode_too_weak")

    def test_the_machine_file_answers_last(self) -> None:
        path = self.machine_file(password="not-a-real-secret", db_schema="agents_test")
        store = self.store()
        self.assertEqual((store["level"], store["source"], store["error"]), ("machine", str(path), "driver_missing"))
        self.assertNotIn("not-a-real-secret", json.dumps(store))
        text = self.run_cli("doctor")
        self.assertIn(f"- Store setting: machine ({path})\n", text.stdout)

    def test_the_machine_file_defaults_to_the_home_config_folder(self) -> None:
        del self.extra_env["XDG_CONFIG_HOME"]
        home = self.root / "home"
        path = home / ".config" / "agentkit" / "store.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"schema": "agentkit.store.v1", "host": "127.0.0.1", "port": 5432,
                                    "database": "agents", "user": "admin", "sslmode": "disable"}))
        env = {key: value for key, value in os.environ.items() if key != "XDG_CONFIG_HOME"}
        result = subprocess.run([sys.executable, str(CONTEXTKIT), "doctor", "--json"], cwd=str(self.project),
                                env={**env, **self.extra_env, "HOME": str(home)}, text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        store = json.loads(result.stdout)["store"]
        self.assertEqual((store["level"], store["source"], store["error"]), ("machine", str(path), "driver_missing"))

    def test_the_machine_file_refuses_what_its_version_does_not_hold(self) -> None:
        self.machine_file(schema="agentkit.store.v2")
        self.assertEqual(self.store()["error"], "store_setting_too_new")
        self.machine_file(extra="value")
        self.assertEqual(self.store()["error"], "bad_store_setting")
        self.machine_file(sslmode="prefer")
        self.assertEqual(self.store()["error"], "sslmode_too_weak")
        self.machine_file(host="127.0.0.1", sslmode="disable")
        self.assertEqual(self.store()["error"], "driver_missing")
        self.assertEqual(self.import_log.read_text().split(), ["psycopg"])


def _store_libraries_ready() -> bool:
    return bool(shutil.which("initdb") and shutil.which("pg_ctl")) and importlib.util.find_spec("psycopg") is not None


@unittest.skipUnless(_store_libraries_ready(), "needs initdb, pg_ctl and psycopg")
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
        self.assertEqual(tables, [("contextkit_agents",), ("contextkit_migrations",)])
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

    def test_a_0_3_9_table_is_adopted_with_its_rows_and_reruns_converge(self) -> None:
        self.extra_env = {}
        self.run_json("init", "--with-layers")
        self.extra_env = {"AGENTKIT_DB_URL": self.url, "AGENTKIT_DB_SCHEMA": self.schema}
        project_id = self.config()["identity"]["id"]
        # The shape 0.3.9 left: its table and rows, booked in the shared ledger it migrated through.
        self.query(f"CREATE SCHEMA {self.schema}")
        self.query(
            "CREATE TABLE contextkit_agents (id text PRIMARY KEY, name text, description text, icon_sha text, icon bytea, "
            "created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now())"
        )
        self.query("CREATE TABLE schema_ledger (owner text, step text, checksum text, PRIMARY KEY (owner, step))")
        self.query("INSERT INTO schema_ledger VALUES ('contextkit', '0001-agents', 'old')")
        self.query("INSERT INTO contextkit_agents (id, description, created_at) VALUES (%s, 'Kept.', '2026-10-01'), "
                   "('prj_000000000000', 'Another agent.', '2026-10-01')", project_id)
        self.assertEqual(self.run_json("doctor")["store"]["state"], "table_pending")

        self.assertEqual(self.run_json("build")["store"]["state"], "updated")
        rows = {row[0]: row for row in self.rows()}
        self.assertEqual(rows["prj_000000000000"][2], "Another agent.")
        self.assertEqual(str(rows[project_id][5].date()), "2026-10-01", "the adopted row keeps created_at")
        ledger = self.query("SELECT step, applied_at FROM contextkit_migrations")
        self.assertEqual([step for step, _ in ledger], ["0001-agents"])
        self.assertEqual(self.query("SELECT owner, step, checksum FROM schema_ledger"), [("contextkit", "0001-agents", "old")])

        self.assertEqual(self.run_json("build")["store"]["state"], "unchanged")
        self.assertEqual(self.query("SELECT step, applied_at FROM contextkit_migrations"), ledger)
        self.assertEqual(self.run_json("doctor")["store"]["state"], "row_present")

    def test_the_machine_file_reaches_the_store_bound_to_its_schema(self) -> None:
        self.extra_env = {"XDG_CONFIG_HOME": str(self.root / "config")}
        path = self.root / "config" / "agentkit" / "store.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"schema": "agentkit.store.v1", "host": "127.0.0.1", "port": self.port,
                                    "database": "postgres", "user": "admin", "sslmode": "disable", "db_schema": self.schema}))
        initialized = self.run_json("init", "--with-layers")
        self.assertEqual((initialized["store"]["state"], initialized["store"]["level"]), ("created", "machine"))
        self.assertEqual([row[0] for row in self.rows()], [self.config()["identity"]["id"]])
        doctor = self.run_json("doctor")["store"]
        self.assertEqual((doctor["state"], doctor["level"], doctor["source"]), ("row_present", "machine", str(path)))

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
