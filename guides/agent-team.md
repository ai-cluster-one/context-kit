# Agent Team Guide

Use this guide after the user selects Agent Team mode for non-trivial work.

Agent Team mode separates task orchestration, execution, and independent acceptance. You remain the task setter and orchestrator. One subagent executes the work. A different read-only subagent reviews the actual result. Do not silently implement the task in the main session.

## Inputs

Before delegation, record:

- the original goal;
- the accepted scope;
- acceptance criteria;
- applicable project context and rule sources;
- required deterministic validation;
- human gates and prohibited consequences.

Resolve material ambiguity with the user before execution. Mode selection does not authorize a consequence that still requires human approval.

## Roles

- You own the task statement, scope, agent coordination, human gates, finding acceptance, and final report.
- The executor subagent changes only the accepted scope, runs required validation, and reports the resulting state and evidence.
- The reviewer subagent remains read-only and judges the actual result against the original goal, accepted scope, acceptance criteria, and applicable rule sources.

Keep the executor and reviewer separate. Do not give the reviewer the executor's rationale, defense, or self-assessment.

## Procedure

1. Give the executor subagent the recorded inputs and the source surfaces it may change.
2. Require the executor to implement the task, run deterministic validation, and return changed paths, validation evidence, and blockers.
3. Give a different reviewer subagent the recorded inputs, current source state or diff, and validation evidence.
4. Require one verdict: `PASS` or actionable findings supported by evidence and mapped to an acceptance criterion or applicable rule source.
5. Reject unsupported or out-of-scope findings. Return accepted findings to the same executor subagent for repair.
6. After repair and deterministic validation, return the actual result to the same reviewer subagent for another verdict.
7. End on `PASS`. After the third reviewer verdict without `PASS`, stop and return unresolved findings to the user.

One review cycle is one executor implementation or repair, its deterministic validation, and one reviewer verdict. The limit is three reviewer verdicts.

Resume the same executor subagent and reviewer subagent across cycles when the host supports continuation. Replace a subagent only when continuation is unavailable, and preserve that role's original inputs and boundary.

## Verdicts

`PASS` means the reviewer finds no actionable problem against the original goal, accepted scope, acceptance criteria, and applicable rule sources. It does not certify unrelated surfaces or waive deterministic validation.

Each finding states the affected surface, observed problem, evidence, violated criterion or rule source, and required repair. A finding does not expand the accepted scope or set product direction.

## Availability

Use Agent Team mode only when the host can provide distinct executor and reviewer subagents. If both roles are not available, tell the user that Agent Team mode is unavailable and offer Direct mode. Do not describe self-review or a single-agent workflow as Agent Team mode.

If a required subagent becomes unavailable and no replacement can preserve the role boundary, stop and return the incomplete state to the user.

## Completion

Report successful completion only after `PASS`. Include changed surfaces, validation evidence, the number of reviewer verdicts, and any consequence still waiting at a human gate. Without `PASS`, report the task as incomplete with its unresolved findings.
