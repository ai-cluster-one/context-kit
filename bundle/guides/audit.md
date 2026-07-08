# Audit Guide

Auditor entrypoint for a ContextKit project body.

Audit procedure: choose the rule source, walk the project body, classify
findings, report repairs. Layer rules live in layer guides.

## Commands

```sh
contextkit audit
contextkit audit-file context/path/to/file.md
contextkit audit --write
```

`contextkit audit` is advisory by default. `contextkit audit --write` persists a
dated report under `.contextkit/audits/`.

## Audit Source Routing

Before judging a file, load the rule source that owns that file type:

| Surface | Rule source |
| --- | --- |
| `context/**/*.md` | `contextkit guide authoring` |
| `assets/**/*.md` | `contextkit guide assets` |
| `routines/**/*.md` | `contextkit guide routines` |
| `capabilities/` project envelopes | `contextkit guide capabilities`, then the capability manager or capability guide when the issue is capability-owned |
| `.contextkit/`, config, required files, visible body shape | `contextkit guide bootstrap` and `contextkit guide validation` |
| generated host context and hook adapters | `contextkit guide hooks` |
| legacy dot folders or host-specific instruction migration | `contextkit guide migration` |
| destructive or state-erasing operations found in procedures | `contextkit guide destructive` |

If a finding depends on a rule from another guide, cite that guide as the rule
source. Do not restate the rule as if the audit guide owns it.

## Audit Walk

Audit target: trusted project body, single source of truth, reliable generated
runtime routing.

Order:

1. Identify the surface being reviewed.
2. Load the owning guide for that surface.
3. Compare the file or folder to that guide.
4. Record findings with the violated rule source.
5. Propose repairs that change the owning source, not generated output.
6. Rebuild and audit again after repairs.

## Finding Classes

Use these severities:

1. **Error** - structure, metadata, or binding prevents compilation or reliable
   routing.
2. **Warning** - the body likely contains drift, duplicate truth, wrong altitude,
   unsafe placement, or a rule-source violation.
3. **Info** - taxonomy or quality hint for human review before changing.

Coherent body over quiet report. Accepted warnings need a recorded reason where
the exception lives.

## Manual Audit Pass

For a full project audit:

1. Run `contextkit doctor`.
2. Run `contextkit build --target all`.
3. Run `contextkit audit --write`.
4. Read the report in `.contextkit/audits/`.
5. For each finding, identify the affected surface.
6. Load the owning guide from the routing table.
7. Repair the owning source file or folder.
8. Rebuild and audit again.

For one file, use:

```sh
contextkit audit-file <path>
```

Then load the owning guide for that path before editing.

## Report Shape

Manual finding fields:

- severity;
- affected path;
- rule source guide;
- observed problem;
- owning source to edit;
- recommended repair;
- repair mode: mechanical or user review.

When a finding crosses layers, name both sides. Example: a routine duplicated a
domain model owned by a context file. The routine guide owns the procedural rule;
the authoring guide owns the context placement rule.

## Repair Discipline

Repair source truth, not symptoms:

- edit `context/`, `assets/`, `routines/`, `capabilities/`, or `.contextkit/`
  according to the owning guide;
- do not hand-edit `.codex/generated/context.md` or
  `.claude/rules/CONTEXT.md`;
- do not move content into `assets/` merely to silence a live-context warning;
- do not copy capability doctrine into ContextKit to make a capability finding
  easier to explain.

After repairs:

```sh
contextkit build --target all
contextkit audit
```

Before committing, also check `git status --short` and confirm generated files
are not staged unless the project intentionally tracks them.
