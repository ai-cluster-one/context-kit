# Audit Guide

Use this guide when reviewing a ContextKit project body or applying audit
findings.

Rule owners: Rule Source Routing, One Fact One Home, Generated Output,
Project Stewardship, Audit Reports Standard, and the guide that owns the
affected layer.

Use `contextkit help` for exact command syntax.

## Source Routing

Before judging a file, load the rule source that owns that surface:

| Surface | Rule source |
| --- | --- |
| `context/**/*.md` | `contextkit guide authoring` |
| `assets/**/*.md` | `contextkit guide assets` |
| `routines/**/*.md` | `contextkit guide routines` |
| `capabilities/` envelopes | `contextkit guide capabilities`, then the capability-owned surface |
| `.contextkit/`, binding, visible body shape | `contextkit guide bootstrap` and `contextkit guide validation` |
| generated host context and hook adapters | `contextkit guide hooks` |
| legacy dot folders or host-specific instruction migration | `contextkit guide migration` |
| destructive or state-erasing operations | `contextkit guide destructive` |

If a finding crosses layers, name each owner.

## Audit Walk

1. Identify the surface.
2. Load the owning guide or tool surface.
3. Compare the artifact to that source.
4. Record findings with severity and rule source.
5. Repair the owning source, not generated output.
6. Rebuild and audit again.

## Finding Shape

A manual finding records:

- severity;
- affected path;
- rule source;
- observed problem;
- owning source to edit;
- recommended repair;
- repair mode.

Use severities from the Audit Reports Standard: error, warning, and info.

## Repair Discipline

Repair source truth, not symptoms.

- Edit the layer that owns the fact.
- Do not hand-edit generated host context.
- Do not move material into `assets/` merely to silence a live-context warning.
- Do not copy capability doctrine into ContextKit.

After repairs:

```sh
contextkit build --target all
contextkit audit
```
