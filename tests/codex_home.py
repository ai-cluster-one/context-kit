"""Point every test at a private Codex home.

`install-hooks` and `bootstrap` record Codex folder and hook trust in the Codex
user config; tests must never write to the developer's real one.
"""
from __future__ import annotations

import atexit
import os
import shutil
import tempfile

CODEX_HOME = tempfile.mkdtemp(prefix="contextkit-test-codex-home-")
os.environ["CODEX_HOME"] = CODEX_HOME
atexit.register(shutil.rmtree, CODEX_HOME, True)
