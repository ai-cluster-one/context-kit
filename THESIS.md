# ContextKit Thesis

ContextKit starts from a simple claim:

Agent context is not documentation. It is an operating environment.

An agent does not merely read context before working. The agent wakes up inside it, uses it to decide what matters, discovers what to load next, and acts through the permissions, routines, tools, and boundaries that context makes available.

If that environment is loose prose, copied instructions, stale notes, and hand-edited host files, the agent inherits confusion. If the environment has a body, sources, laws, evidence, procedures, and validation, the agent can work with continuity.

ContextKit is a way to give a project that body.

## The Body

A ContextKit project separates the kinds of knowledge an agent needs:

- `context/` holds live doctrine: identity, mission, laws, constraints, architecture, and stable project models.
- `assets/` preserves evidence: sessions, plans, research, history, raw notes, and records of how the project learned something.
- `routines/` holds repeatable work: procedures with triggers, order, idempotency, stop conditions, and expected outcomes.
- `capabilities/` holds project envelopes for tools: the enabled set, project-specific identifiers, references, and connection declarations where the tool's own doctrine allows them.
- `.contextkit/` holds binding and manager artifacts: config, audit reports, and ContextKit-native technical state.
- Generated host context is delivery output. It is rebuilt from source and is not edited by hand.

This body is not a folder convention for its own sake. It is a way to prevent different kinds of truth from collapsing into one text blob.

## Source And Runtime

The source body and the runtime context are different things.

The source body is where durable truth is authored. The runtime context is a compiled view for a host such as Codex or Claude. Runtime context should contain only what the operating agent needs in that moment: orientation, laws, routing, and compact awareness of on-demand surfaces.

This separation matters because context has cost. Always-on text is paid for in every session. A good runtime block helps the agent live inside the project; it does not document the whole product, repeat every guide, or copy every tool contract.

The source body is the house. Runtime context is the set of rooms and signs the agent needs when it enters.

## The Context Lens

Every authored artifact has a reader, a moment, and a job.

Before writing, the author asks:

- Who will read this?
- At what moment will they read it?
- What action should it make possible?
- Is this a law, an instruction, a runtime directive, evidence, a procedure, human documentation, or an executable contract?

Different artifacts require different voices:

- Runtime context directs an operating agent.
- Guides teach an authoring agent.
- A thesis states the worldview.
- A README orients a human.
- Assets preserve evidence and history.
- Routines describe repeatable work.
- CLI help owns executable command truth.
- Generated files deliver compiled context to hosts.

When these voices blur, the agent loses angle of view. It may receive product documentation where it needed a directive, a historical asset where it needed live truth, or a guide where it needed a small operating law.

ContextKit treats that angle of view as a quality property.

## One Fact, One Home

Every durable fact has one home.

A fact may be a principle, path, command, identifier, workflow rule, limitation, product decision, or project model. If it appears as live truth in several places, drift has already started.

Other surfaces can route to the owner. They do not become parallel owners.

This is why generated files are not source truth, assets are not live doctrine, README prose is not the command contract, and a routine does not own the model it applies.

## Evidence Becomes Doctrine Deliberately

Evidence is valuable because it preserves how the project learned. It may be old, partial, exploratory, or contradicted by later work.

Live doctrine is different. It states what the agent should treat as true now.

An asset can contain a conclusion, but the conclusion becomes live only when it is promoted into the source file that owns it. The asset remains as evidence. The live layer carries the current fact.

This keeps memory honest without letting old notes masquerade as operating law.

## Tools Speak For Themselves

Command-answerable knowledge belongs in the command.

If a CLI can answer a question through `help`, `doctor`, `connections`, a guide verb, or another contract surface, ContextKit does not copy that answer into always-on prose. Runtime context points to the tool and tells the agent how to discover the contract at use time.

Readiness is also proven at use time. A stub or generated index tells the agent that a tool exists; the tool's own doctor surface tells the agent whether it is ready in the current environment.

## Human Gates

Agents can do a great deal of work without asking the human to operate every step. They can inspect, classify, draft, refactor, validate, summarize, and prepare decisions.

But some actions carry consequences: external writes, money, publication, credentials, irreversible deletion, product direction, reputation, and access changes.

ContextKit makes those gates explicit. The agent can do the work; the human approves the consequences.

## Product Structure

ContextKit itself separates the artifacts it ships:

- Thesis: the worldview.
- Runtime: the always-on operating block emitted into generated context.
- Guides: on-demand instructions delivered as a project-side reference manual.
- Templates: starter project-body files for onboarding and initialization.
- CLI: executable manager and command contracts.
- Installer: delivery for the manager, runtime, guides, and templates.
- README: human-facing orientation.

The public product repository owns these shipped sources.

Maintainer memory, authoring principles, and product-construction doctrine live outside the public product repository, in an admin project. A demo project can show what a completed ContextKit-managed project looks like. The shipped mechanism, the workbench, and the demo stay separate so their meanings do not leak into each other.

## The Goal

The goal is not to make projects verbose. The goal is to make them inhabitable.

A good ContextKit project gives an agent enough stable structure to continue work across sessions, hosts, and tools:

- identity without role confusion;
- laws without bloated instruction walls;
- evidence without stale doctrine;
- routines without hidden task state;
- tools without copied contracts;
- generated context without hand edits;
- validation without guessing;
- and a clear lens for every artifact the agent reads or writes.

ContextKit turns context from a pile of remembered text into a maintained operating environment for agents.
