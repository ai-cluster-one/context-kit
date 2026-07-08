# Semantic Anchors

Power: portable reference.

Context names meanings. Configuration supplies environment-specific values.

Decision Question: is this reference a semantic relationship, or a concrete
value that belongs in configuration?

## Law

Durable context refers to projects, services, repositories, secrets, URLs, and
machine-specific locations by semantic anchor rather than copying concrete
values into prose.

A semantic anchor may be an environment variable, configuration key, capability
connection, tool-managed setting, or structured owner. Context may name the
anchor and explain what it means. The concrete value lives with its owner.

## Failure Signs

- several files repeat the same absolute path;
- changing a checkout location requires doctrine edits;
- context copies a secret, credential, or machine-local value.
