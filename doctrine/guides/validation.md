# Validation Guide

Run validation after init, migration, hook changes, or any meaningful body edit:

```sh
contextkit doctor
contextkit build --target all
contextkit audit
```

`doctor` checks project binding, required files, gitignore guards, visible body
layers, legacy dot folders, and host binding locations.

`doctor` confirms the project can expose `capabilities/` as a layer, but it does
not validate capability implementation, creation doctrine, or capability tests.
Use the capabilities manager and capabilities repo for that.

`build --target all` proves Codex and Claude generated contexts can be compiled
from source. Generated files are ignored build artifacts and should not be edited
by hand.

`audit` checks the live context layer for metadata quality, duplicate durable
facts, stale routing assumptions, wrong placement, and inline bloat.

Before committing, also confirm that `.env.local`, `.env`, `.codex/generated/`,
and `.claude/rules/CONTEXT.md` are not staged.
