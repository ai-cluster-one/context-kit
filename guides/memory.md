# Memory Guide

Use this guide when capturing, reviewing, importing, grooming, or promoting provisional project knowledge.

This guide is the operational rule source for project memory. It applies Visible Body, Altitude, One Fact One Home, Evidence Promotion, Tool Truth, and Host-Neutral Core, then routes durable material to its owning layer or tool.

## Role

Project memory is the project's hot staging layer. Keep project-relevant knowledge there when future sessions must account for it but its durable owner or final form is not ready yet.

Memory is provisional. It is not live doctrine, historical evidence, a task queue, a transcript archive, or provider-owned storage.

The memory directory is optional and created lazily by memory capture or import. It defaults to visible `memory/`. Set `CONTEXTKIT_MEMORY_DIR` to a dedicated persistent directory when deployment may replace the project filesystem. The deployment environment must mount that directory durably.

Use `contextkit memory status` to verify the active source before relying on external persistence. Do not point the anchor at a project root, shared doctrine tree, or directory whose unrelated Markdown should enter runtime context.

One memory root is active at a time. When the environment anchor is set, ContextKit does not merge project-local `memory/`; import or move useful local notes deliberately before switching the deployment to the external root.

Memory files are ordinary Markdown and do not use the `context/` front-matter contract. ContextKit appends new captured notes to a dated Markdown file under the active memory root.

Every Markdown file under the active memory root is included fully in generated runtime context. Keep memory compact and groom it regularly because every retained note consumes always-on context.

Live project doctrine and owning-tool truth take precedence over memory. Treat a conflict as a grooming problem and repair the owning sources instead of relying on memory as an override.

## Capture Judgment

Use `contextkit memory add` when the current session produces a decision, observation, correction, constraint, or unresolved conclusion that future sessions must consider before it has a durable owner.

Capture the smallest self-contained note that preserves the useful meaning. State enough context for a future agent to understand why the note matters.

Do not add:

- a fact already owned by live context, a routine, a capability, or another tool;
- secrets, credentials, or machine-local state;
- transient task progress, conversational trivia, or an open work queue;
- raw transcripts, large research records, or evidence that belongs in `assets/`;
- provider-specific memory instructions or settings.

The current session already knows what it captured. Continue the work without restarting solely to reload the new note.

## Memory Operations

Use the stable memory verbs as routes to the live command contract:

- `contextkit memory add` captures a provisional note;
- `contextkit memory context` returns the complete current memory block;
- `contextkit memory search` finds material in project memory;
- `contextkit memory status` reports the current memory layer;
- `contextkit memory import` brings existing project memory under ContextKit ownership.

Use `contextkit help` and command help for exact syntax, accepted inputs, output, and failure behavior.

## Grooming

Groom memory when notes have become clear enough to classify, when memory conflicts with live doctrine, or when the hot layer has grown beyond what every session should carry.

For each note:

1. Decide whether it is still provisional and useful.
2. Find the durable owner for any conclusion that is ready to govern future work.
3. Load the guide or tool surface that owns the destination.
4. Write the durable conclusion in the destination's required form.
5. Preserve historically useful evidence in `assets/` when the record matters beyond the conclusion.
6. Verify the destination, then remove or rewrite the superseded memory note so it does not remain a second live copy.
7. Leave the note in memory only when its useful meaning is still unresolved.

Route current doctrine through `contextkit guide authoring`, repeatable procedure through `contextkit guide routines`, historical evidence through `contextkit guide assets`, and tool-owned knowledge through `contextkit guide capabilities` or the owning tool.

Run the normal validation flow after promoting material or changing another project-body owner.

## Import

Use memory import when adopting useful project memory from an existing provider-specific or project-local Markdown store.

Inspect the import plan before applying it. Review the proposed sources, destinations, and collisions, then apply the accepted plan explicitly.

Import preserves usable Markdown as provisional memory; it does not require semantic reclassification before the material can be used. After import, review and groom the imported notes under the same rules as newly captured memory.

ContextKit project memory becomes the canonical project-side memory after adoption. Provider-specific discovery, host settings, and binding behavior remain owned by the CLI and `contextkit guide hooks`.

## Quality Bar

Project memory is healthy when every note is useful to future sessions, provisional rather than duplicated doctrine, safe to include fully in runtime context, and either moving toward an owner or intentionally awaiting clarification.
