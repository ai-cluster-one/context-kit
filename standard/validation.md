# Validation Standard

Rule source for proving a ContextKit project body can be trusted after changes.

## Sequence

Validation has three layers:

1. `doctor` validates shape, binding, guards, visible layers, capability gate,
   and target paths.
2. `build` proves the source body can compile into host runtime context.
3. `audit` checks coherence, metadata, routing, duplication, and source-owner
   discipline.

The machine checks are the floor. Human review checks rule-source routing,
cross-layer ownership, generated-output discipline, and whether warnings are
accepted deliberately.

## Quality Bar

A validation pass is good when every failure points to the owning source or tool
surface, and the repair path changes source truth rather than symptoms.
