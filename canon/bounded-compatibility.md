# Bounded Compatibility

Power: controlled transition.

Compatibility keeps old shapes usable long enough to migrate them. It does not
make old shapes canonical again.

Decision Question: is this compatibility path an explicit bridge, or a second
canonical system?

## Law

ContextKit may support legacy shapes only as explicit, bounded bridges.

A compatibility path names the old shape, names the canonical destination,
routes through migration, rejects ambiguous parallel ownership, and keeps
transitional language pointing at the destination.

Compatibility that never ends becomes drift with a friendly name.

## Failure Signs

- old and new paths both accept writes with no owner distinction;
- a generated surface normalizes a legacy shape without migration routing;
- compatibility exceptions are invisible to validation.
