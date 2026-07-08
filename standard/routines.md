# Routines Standard

Rule source for repeatable procedures under a project's `routines/` layer.

## File Contract

Each routine is one Markdown file with front matter:

```yaml
---
name: routine-name
description: Specific one-line trigger and outcome.
---
```

The filename stem equals `name`. The description says when to run the routine
and what outcome it produces.

## Body Contract

A routine opens with trigger, scope boundary, and definition of done. It includes
inputs, ordered steps, idempotency guard, stop conditions, low-confidence path,
expected final state, and context or capability surfaces to load by role.

Routines apply models; they do not own models. They exclude durable domain
models, raw evidence, copied command contracts, secrets, and open task queues.

## Quality Bar

A routine is good when rerunning the same class of work is safer and clearer
than re-deriving the procedure, and when the agent can load owners for models
and tools instead of finding copies inside the routine.
