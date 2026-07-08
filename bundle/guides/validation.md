# Validation Guide

Use this guide after initialization, migration, hook changes, or meaningful
edits to `context/`, `assets/`, `routines/`, or `capabilities/`.

Rule owners: Validation Standard, Audit Reports Standard, Generated Output
Standard, Context Files Standard, and Rule Source Routing.

## Sequence

Run:

```sh
contextkit doctor
contextkit build --target all
contextkit audit
```

`doctor` checks shape, binding, local/generated guards, visible layers,
capability gate, legacy dot layers, and configured targets.

`build` proves source body can compile into host runtime context. Generated
files are build artifacts; do not fix them by hand.

`audit` checks coherence and quality. Each finding names a rule source. Load the
named guide or owner before repairing.

## Human Review

Machine checks are the floor. Review asks:

- Which rule source owns the layer?
- Was that source loaded before judging the file?
- Did any finding cross layers?
- Did the repair change the owning source?
- Did generated files stay unstaged unless intentionally tracked?

## Before Commit

```sh
contextkit doctor
contextkit build --target all
contextkit audit
git status --short
```

If validation fails, fix the source layer that owns the problem. Do not silence
the report by hiding material in a lower-visibility place.
