# Validation Guide

Use this guide after initialization, migration, hook changes, or meaningful edits to `context/`, `assets/`, `routines/`, or `capabilities/`.

This guide is the operational rule source for validation. It applies Generated Output and Rule Source Routing, then routes each problem to the guide or tool that owns the affected surface.

## Sequence

Run:

```sh
contextkit doctor
contextkit build --target all
contextkit audit
```

`doctor` checks shape, binding, local/generated guards, visible layers, capability gate, legacy dot layers, configured targets, and an optional global context source.

`build` proves project and configured global context can compile into host runtime context. Generated files are build artifacts; do not fix them by hand.

`audit` checks coherence and quality across project and configured global context. Each finding names a rule source. Load the named guide or owner before repairing.

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

If validation fails, fix the source layer that owns the problem. Do not silence the report by hiding material in a lower-visibility place.
