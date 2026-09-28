# Agent Team Guide

Use this guide after the user selects Agent Team mode for non-trivial work, or when the user wants to change whether the mode is offered.

Agent Team mode separates orchestration, execution, and acceptance so a result is judged against a fixed standard by an agent that did not produce it. You remain the orchestrator. One subagent executes the work. A different read-only subagent reviews the actual result. Do not implement the task in the main session.

## Inputs

Before delegation, record:

- the goal and the accepted scope;
- the done condition: the observable result that makes the item finished;
- the acceptance checks;
- the attempt budget: the number of reviewer verdicts the item may use, three unless the project assigns a smaller budget;
- the standing deterministic validation that must pass before review;
- human gates and prohibited consequences.

Resolve material ambiguity with the user before execution. Mode selection does not authorize a consequence that still requires human approval.

## Acceptance Checks

The acceptance checks are a closed list fixed before execution. The executor and the reviewer receive the same list.

- Break the done condition into checks that can each be confirmed, and add each applicable standing project standard as a concrete check.
- Add one baseline check: nothing that held in a named prior state, such as a commit, version, or published revision, stops holding.
- Add one scope check: the result changes only the accepted scope and leaves material the executor did not create untouched.
- State for each check how it is confirmed: the environment, the instrument, and the real input path, not only what must hold.

Every check maps to a clause of the done condition or to a standing project standard. Correct or remove a check only by showing that it maps to neither, record the change, and never leave a clause without a check.

## Roles

- You own the goal, the checks, the budget, finding decisions, human gates, and the final report.
- The executor changes only the accepted scope, runs standing validation, confirms each check itself, and returns changed surfaces with evidence per check. It reports a blocker as soon as it meets one, with its cause and at least one different path, instead of iterating silently.
- The reviewer stays read-only and confirms each check against the actual result. It does not receive the executor's rationale, defense, or self-assessment. Never ask the reviewer to look for anything beyond the checks.

## Evidence

Evidence for a check names what was confirmed and where: a file and line, a test, a command result, or an observation in the running environment. Evidence reports every run, including failures. A check that passes only on some runs fails, and incomplete evidence fails the check.

## Procedure

1. Give the executor the recorded inputs and the surfaces it may change.
2. The executor implements, runs standing validation, and returns evidence per check and any observations. Do not send a result that fails standing validation to review.
3. Give the reviewer the recorded inputs, the actual result or diff, and the validation evidence.
4. The reviewer returns each numbered check with `PASS` or `FAIL` and one line of evidence, then the verdict, then its observations.
5. On `REJECT`, return only the failed checks to the same executor. After repair and standing validation, return the result to the same reviewer.
6. On `ACCEPT`, the review ends without another cycle.
7. When integration follows review, confirm the done condition in the delivered state before reporting done. A failure there counts as a `REJECT` against the same budget. Publishing, release, and other external consequences stay behind their human gates.

Resume the same executor and reviewer across cycles when the host supports continuation. Replace a subagent only when continuation is unavailable, and preserve that role's inputs and boundary.

## Verdicts And Findings

`ACCEPT` means every check passed. `REJECT` names the failed checks. The verdict rests on the checks alone.

A blocking finding is a failed check. Everything else the executor or reviewer meets is an observation: an issue next to the change, an imperfection the change did not introduce, or an improvement idea. Test any finding with one question: would the done condition hold without this change? If yes, it is an observation, however closely related.

An observation never affects the verdict and never returns to the executor within the same item. Route each observation to the project's own intake when it has one, and list every observation in the final report.

## Stalls

When the executor stops converging before the budget is spent, stop it and ask for a diagnosis: the mechanism that blocks it, the evidence, what was tried and what each attempt changed, and at least one different path to the same result. Classify the cause:

- **Path**: the chosen approach cannot reach the done condition. Choose another path within the remaining budget; bring it to the user when it changes an accepted decision.
- **Check**: a check catches something outside the done condition. Correct it under the mapping rule.
- **Instrument**: the available environment or instrument cannot observe the failure. Change the instrument or bring the user in; do not spend more attempts on it.
- **Goal**: the goal or done condition is ill-posed, or a later decision invalidated it. Return it to the user.

When the budget is spent without `ACCEPT`, stop and return the failed checks, the diagnosis, and a recommended remedy to the user.

Never narrow the accepted goal to make an item pass. The path to it can change.

## Availability

Use Agent Team mode only when the host can provide distinct executor and reviewer subagents. If both roles are not available, tell the user that Agent Team mode is unavailable and offer Direct mode. Do not describe self-review or a single-agent workflow as Agent Team mode.

If a required subagent becomes unavailable and no replacement can preserve the role boundary, stop and return the incomplete state to the user.

## Mode Offer

`[collaboration] mode` in `.contextkit/config.toml` decides whether generated context offers the choice. `ask`, the default, offers Direct or Agent Team mode before non-trivial work. `direct` leaves the offer out of generated context; the user can still request Agent Team mode explicitly. When the user no longer wants the offer, set `mode = "direct"` and run `contextkit build`.

## Completion

Report done only after `ACCEPT` and, when integration follows review, confirmation in the delivered state. Include changed surfaces, evidence, the number of verdicts used, observations, and any consequence waiting at a human gate. Otherwise report the item as incomplete with its failed checks and diagnosis.
