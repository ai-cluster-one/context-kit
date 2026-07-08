# Operational Provenance

Power: traceable delivery.

Operational artifacts tell the reader where they came from, who owns them, and
how to rebuild or verify them.

Decision Question: can a reader tell the origin, owner, and repair path for this
operational artifact?

## Law

Delivered operational surfaces carry enough provenance to make repair obvious:
generator identity, owning source or config, rebuild or verification command,
rule source, install or delivery source, and next safe action when useful.

The artifact should not become a manual. It should expose the path back to the
owner.

## Failure Signs

- generated output does not say it was generated;
- a report omits the rule source used to produce it;
- an agent can inspect an artifact but cannot tell how to rebuild it.
