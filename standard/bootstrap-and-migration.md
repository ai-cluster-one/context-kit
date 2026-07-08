# Bootstrap And Migration Standard

Rule source for initializing or adopting ContextKit project bodies and migrating
legacy shapes.

## Bootstrap Contract

Bootstrap establishes the binding, visible body layers, host bindings, generated
runtime context, and first validation pass.

Bootstrap preserves existing project body files, creates missing visible layers
only when absent, installs generated-output delivery paths, runs validation, and
requires review before replacing non-ContextKit files in managed hook paths.

Local env files are machine-local. Generated host output and capability state
guards are ignored unless a project deliberately tracks them.

## Migration Contract

Migration begins with classification. Legacy dot folders and host instruction
files are migration inputs. Their durable meaning is moved to the visible owner:
`context/`, `assets/`, `routines/`, `capabilities/`, or the owning tool surface.

Migration is complete when generated context has equal or better routing value
than the old host-specific files without duplicating their facts.

## Quality Bar

A bootstrapped or migrated project has a valid binding, visible body layers,
ignored local/generated state, no canonical dot-body layers, and clean or
reviewed validation.
