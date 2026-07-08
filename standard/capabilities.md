# Capabilities Standard

Rule source for the boundary between ContextKit and external capability tools.

## ContextKit Owns

ContextKit owns the project envelope layer at `capabilities/`, the project gate
in `capabilities/settings.json`, enabled capability awareness in generated
runtime context, installed capability stubs when available, and warnings that
affect context generation.

## ContextKit Does Not Own

ContextKit does not own capability implementation, release mechanics, credential
cascades, connection registries, command contracts, schemas, output envelopes,
or capability-specific authoring guides.

## Operating Rule

Generated context tells the agent that a capability exists. The capability CLI
owns full use, readiness, connections, and contracts. Exit 4 is policy, not a
crash; the agent asks the user instead of lifting a gate.

## Quality Bar

The boundary is healthy when project-specific capability references stay in the
project envelope, capability-general doctrine stays with the capability, and
readiness is checked at use time.
