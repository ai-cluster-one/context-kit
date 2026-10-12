"""Point every test at a private Codex home and at no shared store.

`install-hooks` and `bootstrap` record Codex folder and hook trust in the Codex
user config; tests must never write to the developer's real one. Every build and
identity write upserts the agents registry row when a store is configured, so
tests clear the `AGENTKIT_DB_*` keys and the machine store setting; a test that
needs a store names its own.
"""
from __future__ import annotations

import atexit
import os
import shutil
import tempfile

CODEX_HOME = tempfile.mkdtemp(prefix="contextkit-test-codex-home-")
os.environ["CODEX_HOME"] = CODEX_HOME
atexit.register(shutil.rmtree, CODEX_HOME, True)

CONFIG_HOME = tempfile.mkdtemp(prefix="contextkit-test-config-home-")
os.environ["XDG_CONFIG_HOME"] = CONFIG_HOME
atexit.register(shutil.rmtree, CONFIG_HOME, True)
for key in [key for key in os.environ if key.startswith("AGENTKIT_DB_")]:
    del os.environ[key]
