# Bootstrap Guide

Use this guide when initializing or adopting a ContextKit project body.

This guide is the operational rule source for bootstrap and adoption. It applies Visible Body, Project Stewardship, Bounded Compatibility, Convergent Operations, Generated Output, and Human Gates.

Use `contextkit help` for exact command syntax.

## Goal

Bootstrap establishes:

- ContextKit binding under `.contextkit/`;
- ignored local env and generated-state guards;
- visible body layers: `context/`, `assets/`, `routines/`, `capabilities/`;
- configured host bindings;
- generated runtime context;
- first doctor/build/audit pass.

Existing project material has standing. Inspect before changing it. Visible body files are created only when absent. Existing body files remain in place.

## Body Root

Layer names are canonical; their location is configured. By default the layers sit at the project root. A project that wants one visible home for the agent body sets `body.root` in `.contextkit/config.toml`, or passes `--body-root <dir>` on the first `bootstrap`, `init`, or `adopt`:

```sh
contextkit bootstrap --body-root agent
```

The body root must be a visible relative folder inside the project. It moves `context/`, `assets/`, `routines/`, `capabilities/`, and the default memory root beneath it, so a collapsed body leaves nothing behind at the project root.

`body.root` locates the body; `sources.<layer>` names a layer inside it. With `root = "agent"` and `sources.routines = "playbooks"`, routines resolve to `agent/playbooks/`. The same rule covers `context`, `assets`, `routines`, `memory`, and `capabilities`. A source path must name a directory strictly inside the project.

The capability envelope has one owner for its place and another for its contents: ContextKit dictates where it sits, and the capabilities manager, sole writer of everything inside it, asks `contextkit path capabilities` on every invocation rather than assuming a location. Configure the envelope through `body.root` like any other layer. The legacy `sources.capabilities = ".capabilities"` bridge names a fixed project-root location and is never rooted.

ContextKit does not relocate an existing body. To adopt a body root later, set `body.root`, move the layers with `git mv`, and rerun `contextkit doctor`.

Use `contextkit path <layer>` to resolve one layer, or `contextkit path` for the whole layout. Tools that need a body layer should ask that command instead of assuming a location.

## Agent Identity

A project carries the identity a host application shows for it: a display name, a one-line description, and an icon. The `[identity]` table in `.contextkit/config.toml` owns the values. The icon is a square PNG, 64 to 1024 pixels per side and at most 1 MiB, stored inside `.contextkit/` under a name ContextKit derives from the image content, so its path changes whenever the image does.

All three are optional. The name falls back to the project folder name, so an unnamed project still presents a usable identity.

The identity also holds the project id, `identity.id`: the one id other tools, such as the capabilities manager and task stores, take for this project. `init`, `adopt`, and `bootstrap` assign it once, and `contextkit identity adopt` assigns it to a project that has none. Assignment adopts the id from the capabilities envelope ContextKit resolves for the project when that envelope already carries one, so records filed under it stay attached; it only reads the envelope. Otherwise ContextKit generates `prj_` plus 12 hex. No command changes or clears an assigned id.

`contextkit identity` is the only writer. It validates the values, copies a chosen image into the binding folder, records the reference, and only then removes the icon files it owns that the config no longer names, so a failed write leaves the previous icon in place. A host application reads the resolved identity and writes through that command rather than editing ContextKit's files.

Doctor reports a project without an id and a configured icon whose file is missing. An absent name, description, or icon is healthy and is not a finding.

## Agent Templates

An agent template is a ready agent ContextKit ships: an identity, a starter body, the capabilities the agent needs, and an onboarding that gets it up to speed. The starter context set behind `--with-template` stays the empty agent; agent templates live beside it.

Each template is a folder `templates/agents/<id>/` holding a `template.toml` manifest and the template's body files:

```toml
id = "personal-agent"            # equals the folder name
name = "Personal Agent"          # the template's display name in a gallery
description = "One line."        # the gallery line and the new agent's identity description
icon = "icon.png"                # square PNG inside the folder; becomes the agent's icon
capabilities = ["mailbox", "tasks"]   # enabled for the new project through the capabilities manager
agent_names = ["Arthur", "Felix"]     # the new agent's name is picked at random from this list

[onboarding]
routine = "onboarding"           # the routine that carries the onboarding; omit the table for none
```

Body files sit under the canonical layer names `context/`, `routines/`, and `assets/`, and land wherever the new project's config places those layers, `body.root` included. A template's routines are its `routines/*.md` files, read from their front matter.

`contextkit templates --json` lists the templates with their manifest values and routines. `contextkit init --template <id>`, run in an empty folder, creates the agent in one step: a Git repository as bootstrap creates one in an empty folder, with the body left ready to commit, the binding and the layers, the template's files, the identity, the capabilities enabled for the project, the Codex and Claude bindings, and the generated context. It refuses a folder that holds anything but a `.git` repository or a `.DS_Store` marker, and an unknown id, and changes nothing then. Running it is the human's act of creating the agent, so enabling the manifest's capabilities crosses no further gate; the command reports each capability with its result, counts one as enabled only when the capabilities manager reports it effective for the project, and exits non-zero naming any that failed while the body and the repository stay in place for the repair.

## Onboarding

An agent created from a template with an onboarding carries `[onboarding]` in `.contextkit/config.toml`: `status`, `pending` or `complete`, and the `routine` that carries it. While it is pending, generated context opens the project's part with an Onboarding block that names the routine and tells the agent to finish it before other work, so every session starts with it.

Only the state is stored. What remains is checked live by the routine itself, through the capabilities and the project files, so stored progress cannot disagree with reality. The routine ends with `contextkit onboarding complete`, which sets the status, rebuilds, and removes the block; running it again changes nothing. `contextkit onboarding status` reports the state.

Doctor reports a pending onboarding as information and still passes. A pending onboarding whose routine is no longer declared is a problem, because the block would point nowhere.

## Main Flow

From the project root:

```sh
contextkit bootstrap
```

Bootstrap creates missing binding and empty body layers, installs configured host bindings, builds generated context, runs doctor, and runs audit.

An absent `memory/` directory is healthy. Bootstrap, initialization, and templates do not create it; the first memory capture or import creates it when needed.

If a directory has files but no Git repository, bootstrap asks for a pre-bootstrap Git safeguard before ContextKit changes project files. `--yes` approves that safeguard and managed hook replacement.

A Codex binding records folder and hook trust in the Codex user config so headless Codex sessions load the context; `--no-trust` leaves that config alone. Use `contextkit guide hooks` for what is recorded.

Starter context templates are opt-in:

```sh
contextkit bootstrap --with-template
```

## Component Flows

Use component commands when you need a smaller change:

```sh
contextkit init
contextkit init --with-layers
contextkit init --with-template
contextkit adopt
contextkit adopt --with-layers
contextkit adopt --with-template
contextkit init --template <id>
contextkit install-hooks --target codex --target claude
contextkit build
contextkit doctor
contextkit audit
```

The CLI owns exact option behavior. This guide owns when and why to use the flows.

## Existing Projects

Existing visible body files remain in place. Missing binding files, guards, host bindings, generated context, and empty layers may be added.

Legacy dot folders are migration inputs:

```text
.context/       -> context/
.assets/        -> assets/
.routines/      -> routines/
.capabilities/  -> capabilities/
```

Inspect migration before moving files:

```sh
contextkit migrate --plan
```

Merge collisions manually. Preserve historical material in `assets/`; promote only durable live facts into `context/`.

## Host Delivery

Agents learn project context through one generated runtime context file that Codex and Claude each load through their own host link. Generated files are build artifacts: edit source files, then rebuild.

## Quality Bar

A project is bootstrapped when doctor is ok, generated context builds, audit has no unreviewed findings, local env and generated files are ignored or intentionally tracked, visible body folders are present, and legacy dot body folders are not canonical.
