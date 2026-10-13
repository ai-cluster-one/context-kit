"""Point every test at a private Codex home and at no shared store.

`install-hooks` and `bootstrap` record Codex folder and hook trust in the Codex
user config; tests must never write to the developer's real one. Every build and
identity write upserts the agents registry row when a store is configured, so
tests clear the `AGENTKIT_DB_*` keys and the machine store setting; a test that
needs a store names its own. Every `update --apply` installs the store driver, so
tests reach a stand-in `uv` first on PATH and a pip that never leaves the machine.
"""
from __future__ import annotations

import atexit
import os
import shutil
import sys
import tempfile

CODEX_HOME = tempfile.mkdtemp(prefix="contextkit-test-codex-home-")
os.environ["CODEX_HOME"] = CODEX_HOME
atexit.register(shutil.rmtree, CODEX_HOME, True)

CONFIG_HOME = tempfile.mkdtemp(prefix="contextkit-test-config-home-")
os.environ["XDG_CONFIG_HOME"] = CONFIG_HOME
atexit.register(shutil.rmtree, CONFIG_HOME, True)
for key in [key for key in os.environ if key.startswith("AGENTKIT_DB_")]:
    del os.environ[key]

# A stand-in for uv: `pip install --target DIR` writes a psycopg stand-in there that
# loads and then fails to connect, so a store result shows which driver loaded; every
# other call goes to the real uv. `CONTEXTKIT_TEST_UV_LOG` records each install and
# `CONTEXTKIT_TEST_UV_FAIL` makes it fail.
REAL_UV = shutil.which("uv")
FAKE_UV = """\
import os, sys
from pathlib import Path
if sys.argv[1:3] != ["pip", "install"]:
    if not REAL_UV:
        sys.exit("uv is not installed")
    os.execv(REAL_UV, [REAL_UV, *sys.argv[1:]])
if os.environ.get("CONTEXTKIT_TEST_UV_LOG"):
    with open(os.environ["CONTEXTKIT_TEST_UV_LOG"], "a") as log:
        log.write(" ".join(sys.argv[1:]) + "\\n")
if os.environ.get("CONTEXTKIT_TEST_UV_FAIL"):
    sys.exit("error: " + os.environ["CONTEXTKIT_TEST_UV_FAIL"])
package = Path(sys.argv[sys.argv.index("--target") + 1]) / "psycopg"
package.mkdir(parents=True)
(package / "__init__.py").write_text(
    "class OperationalError(Exception):\\n    pass\\n"
    "def connect(*args, **kwargs):\\n    raise OperationalError('installed stand-in driver')\\n"
)
"""
FAKE_BIN = tempfile.mkdtemp(prefix="contextkit-test-bin-")
atexit.register(shutil.rmtree, FAKE_BIN, True)
with open(os.path.join(FAKE_BIN, "uv"), "w") as handle:
    handle.write(f"#!{sys.executable}\nREAL_UV = {REAL_UV!r}\n" + FAKE_UV)
os.chmod(os.path.join(FAKE_BIN, "uv"), 0o755)
os.environ["PATH"] = FAKE_BIN + os.pathsep + os.environ.get("PATH", "")
os.environ["PIP_NO_INDEX"] = "1"
