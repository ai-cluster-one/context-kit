# Semantic Grooming Guide

Use this guide when reviewing a ContextKit-managed project for duplicated facts, misplaced meaning, ambiguous ownership, stale live doctrine, or material whose artifact type does not match its job.

This guide owns semantic grooming. It applies One Fact One Home, Altitude, Context Lens, Rule Source Routing, Generated Output, and Project Stewardship.

## Scope

State the accepted scope before review. Include the managed project body and configured context-bearing sources. Inspect generated output only as evidence of delivery.

Exclude active project memory. Use `contextkit guide memory` for memory grooming and promotion.

Do not inspect arbitrary repository documentation or code, provider-private memory, secrets, connection payloads, or capability state as part of semantic grooming.

Load the guide or tool surface that owns each artifact before judging it. If the complete accepted scope was not reviewed, do not report `PASS`.

## Roles

You remain the orchestrator and task setter. Use three distinct subagents and load `contextkit guide agent-team` for general role separation and verdict discipline.

- Give a researcher subagent read-only access to the accepted scope. Require a semantic inventory and repair hypotheses.
- Give an independent validator subagent the original sources, accepted scope, and owning rule sources. Require validation of every hypothesis.
- Give a separate executor subagent only the consensus repairs accepted by you.
- Return the actual diff to the validator after execution.

## Research

Require the researcher to identify the current owner before proposing a destination. Look for duplicated durable facts, semantic material in the wrong artifact type, stale present-tense claims, generated symptoms whose source owner is elsewhere, and unique meaning that a move or deletion could lose.

Keep each finding short. State the affected source, observed problem, governing rule source, current owner, intended owner, repair hypothesis, preservation requirement, and any confidence limit or blocker.

Do not create packets, schemas, ledgers, JSON protocols, or persistent groom state.

## Validation

Require the validator to check every claim against the original source and its owning rules. Reject a hypothesis when the evidence is incomplete, the proposed owner is wrong, unique meaning would be lost, or the change exceeds the accepted scope.

Accept only repairs on which the researcher and validator agree and whose preservation path is explicit. Treat disagreement or uncertainty as a blocker, not as permission to choose silently.

Defer changes to shared global owners, external capability owners, and the ContextKit product owner until the user explicitly authorizes that owner change.

## Repair

Give the executor the accepted findings, exact source boundaries, preservation requirements, and prohibited consequences. Repair authored source, not generated output. Do not let the executor broaden the scope or reinterpret rejected findings.

After execution, require the validator to inspect the actual diff. Report `PASS` only when the diff implements every accepted repair, preserves unique meaning, introduces no new competing owner, and leaves no accepted finding unresolved.

If source changed, load `contextkit guide validation` and follow its current sequence before completion.
