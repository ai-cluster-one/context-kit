# Audit Guide

Use this guide when reviewing a ContextKit project body or applying audit findings.

This guide is the operational rule source for deterministic audits. It applies Rule Source Routing, One Fact One Home, Generated Output, and Project Stewardship, then routes each finding to the guide that owns the affected layer.

Use `contextkit help` for exact command syntax.

## Boundary

`contextkit audit` reports deterministic findings that the manager can prove from project structure and authored metadata. It does not decide whether durable facts are duplicated, semantically misplaced, stale in meaning, or owned by the wrong artifact type.

Use `contextkit guide groom` for agent-driven semantic review. Keep memory grooming under `contextkit guide memory`.

## Source Routing

Before judging a file, load the rule source that owns that surface:

| Surface                                                   | Rule source                                                          |
| --------------------------------------------------------- | -------------------------------------------------------------------- |
| `context/**/*.md`                                         | `contextkit guide authoring`                                         |
| configured global context (`**/*.md`)                     | `contextkit guide global-context`, then `contextkit guide authoring` |
| active project memory root (`**/*.md`)                    | `contextkit guide memory`                                            |
| `assets/**/*.md`                                          | `contextkit guide assets`                                            |
| `routines/**/*.md`                                        | `contextkit guide routines`                                          |
| `capabilities/` envelopes                                 | `contextkit guide capabilities`, then the capability-owned surface   |
| `.contextkit/`, binding, visible body shape               | `contextkit guide bootstrap` and `contextkit guide validation`       |
| generated host context and hook adapters                  | `contextkit guide hooks`                                             |
| legacy dot folders or host-specific instruction migration | `contextkit guide migration`                                         |
| destructive or state-erasing operations                   | `contextkit guide destructive`                                       |

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

Use the severity vocabulary exposed by `contextkit audit`: error, warning, and info.

## Repair Discipline

Repair source truth, not symptoms.

- Edit the layer that owns the fact.
- Do not hand-edit generated host context.
- Do not move material into `assets/` merely to silence a live-context warning.
- Do not copy capability doctrine into ContextKit.

After repairs, load `contextkit guide validation` and follow its current sequence.
