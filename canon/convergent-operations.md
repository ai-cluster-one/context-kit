# Convergent Operations

Power: rerun safety.

ContextKit operations converge toward a stable project shape when run more than
once with the same inputs, authority, and state.

Decision Question: will rerunning this operation converge, or create duplicate
state?

## Law

A product operation has a stable destination. It distinguishes created, changed,
skipped, and review-needed outcomes; replaces projections deterministically; and
leaves ownership clearer than before.

Rerun safety does not mean every operation is harmless. It means repeated work
does not accumulate duplicate owners, bindings, or fragments.

## Failure Signs

- rerunning an operation appends another generated block;
- a repeated operation cannot tell what it owns;
- a repair creates a new source of truth instead of reaching the same shape.
