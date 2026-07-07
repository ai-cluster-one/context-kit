# Routines Guide

Routines are repeatable procedures under `routines/`. A routine should tell the
agent when to run the procedure and the ordered work to perform.

Each routine Markdown file should start with:

```yaml
---
name: routine-name
description: Specific one-line trigger and outcome.
---
```

Authoring rules:

- Put procedural sequencing in routines.
- Keep durable doctrine in `context/`, not duplicated in routines.
- Keep tool contracts and identifier maps in the owning capability layer, not routines.
- Make the `description` a routing surface: when should this routine be loaded?
- Prefer one routine per repeatable job; split only when the trigger/outcome differs.

After editing routines, run `contextkit build --target all` so the generated
routine index is refreshed.
