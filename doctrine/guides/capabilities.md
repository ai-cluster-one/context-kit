# Capabilities Guide

Capabilities remain separate tools. ContextKit includes their project index from
`capabilities/settings.json`, installed capability snapshots, and each enabled
capability's visible project envelope under `capabilities/<name>/`.
Capability-owned references and operational state stay inside `capabilities/`.

ContextKit does not define how to create, validate, audit, or release a
capability. Use the capabilities manager/repo for capability doctrine. ContextKit
only surfaces the enabled capability set into generated project context.
