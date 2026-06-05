---
name: ask-feynman
description: Read-only diagnosis phase for SWE-bench instances -- the STATIC ablation arm for recon (prereg-pro-v1-feynman). Identical to recon in goal, typing, process, and handoff; it removes ONLY scoped diagnostic perturbation -- it may not run experiments during diagnosis. It may REASON about what an experiment would show, but it cannot execute one. "Write down the problem, think real hard, write down the solution." No edits, no external access.
argument-hint: <instance-id>
allowed-tools: Read, Grep, Glob, Bash
---

# Ask-Feynman: Static Codebase Diagnosis for Bench

Read the container, localize the root cause, hand off -- **from reading and reasoning alone**. No edits, and no *experiments*: this arm diagnoses statically. Every observation is grounded in code you can quote.

This is the **static ablation arm** for `recon` (see `docs/PREREGISTRATION-feynman-ablation.md`). It is the *same diagnosis job*, the *same typed inquiry*, with one capability removed: **scoped diagnostic perturbation**. You may not run the failing tests, drop a print, run a narrowed experiment, or bypass-to-isolate during diagnosis. You diagnose by *thinking*, not by *poking*.

**Experimentation policy (this is the only thing that differs from `recon`).** You may **imagine** experiments and reason counterfactually about them -- "if I bypassed X, the symptom would clear, so X is the cause" -- to **generate and rank hypotheses**. But an imagined result is a **prediction, not evidence**: you may not record it as an observation, and it may not "confirm" a hypothesis. State the experiment you would run and your predicted result, mark it **unverified**, and let the downstream gate be what actually confirms. You may **not execute** anything during diagnosis.

**The adversary is the gate, not a second model.** The pipeline corrects a wrong diagnosis by *iterating*: craft tests your hypothesis against the deterministic gate, and if it's wrong, audit feeds the kill back to you as a new observation. So diagnose decisively from the evidence you can read; if your static reasoning bottoms out, hand off your best-reasoned hypothesis and let the loop catch you.

## Environment

Code lives in an offline Docker container, reached only through the helper the adapter names (e.g. `box-sh '<cmd>'`). **The helper is READ-ONLY for this arm: file reads, greps, and `git log` only. It will not execute code, tests, or scripts.** The helper already `cd`s to the repo root -- **do not prepend `cd`**. There is no internet, no `gh`, no `codex`.

You do **not** have the gate helper. The failing-test source, the error message, and the FAIL_TO_PASS list are in the adapter prompt; reason from those.

## Output

Print your handoff to **stdout** as a markdown block starting with `# Recon:`. The driver captures stdout, persists it, and feeds it to /craft. Also append your hypothesis nodes to the graph document the adapter names (it accumulates across the outer loop -- never truncate it).

## Process

### Phase 1: Baseline (read the symptom)

1. Read the failing-test source AND the captured failure output (exact error + stack trace from running the failing test on the base) -- both are in the adapter prompt. This is the **same symptom `recon` observes by reproducing**; you are not deprived of it, only of running *further* experiments. (You may not re-run anything; reason from the provided failure.)
2. Grep the error string in the codebase. Find where it originates.
3. Classify the failure mode: wrong return value, exception, assertion mismatch, missing behavior, wrong behavior.
4. Write H0: "The tests fail because ___." One sentence. Mark it as an abduction.

### Phase 2: Localize (shrink the suspect set)

Delta-debug instinct: reduce before explaining.

1. Trace the call path from the failing test to the failure site. Follow imports, calls, data flow. Don't read the whole repo -- follow the thread.
2. Grep the key identifiers (functions, classes, error strings) to find every relevant location.
3. Read blame history for the suspect region: `git log --oneline -10 -- <file>`. A deliberate design choice has different weight than a default nobody revisited.
4. Identify the minimum set of files and line ranges that could produce the failure -- the **suspect set**. Everything outside it is irrelevant until proven otherwise.

### Phase 3: Hypothesis (root cause)

1. State the root-cause hypothesis: what is wrong and why.
2. Quote the code that supports it (file:line).
3. State what would need to change to fix it.
4. Classify confidence by reasoning mode: **deduction** (read the code, traced consequences -> 95-99%), **induction** (checked a prediction against the *provided* failure output or existing code -> 90-95%), **abduction** (proposed from pattern -> 60-85%). An experiment you only *imagined* does NOT earn induction -- it is at most a deduction, and stays unverified.

Distinguish competing explanations by **reasoning through** what a cheap experiment *would* show -- "a print here would read N, which would confirm A over B" -- and carefully tracing the code. State the experiment and your predicted result as an **unverified prediction** (it ranks hypotheses; it does not confirm one), and prune hypotheses the code directly contradicts.

**If two explanations survive and you cannot decide them by reasoning, don't force a pick** -- hand both to craft as competing edit sites. Craft will test them against the gate, cheapest first. The gate decides what your reading couldn't.

### Phase 4: Edit sites

For the surviving hypothesis (or the few that survive), enumerate every location that must change:

1. `grep -rn "<pattern>" .` -- enumerate ALL occurrences. Never reconstruct from memory.
2. For each edit site: file path, line range, plain-language description of the change.
3. Check for other callers, subclasses, or related locations the fix must also touch.

### Phase 5: Emit

Print to stdout:

```markdown
# Recon: <instance-id>

## Failure summary
<one paragraph: what the tests check, how they fail, error message>

## Suspect set
- `path/file.py` lines 10-40: <why suspect>

## Root cause
<2-3 sentences: what is wrong, why, the code path>
Confidence: <deduction/induction/abduction> -- <percentage>
Supporting evidence:
- `file:line` -- <quote>

## Edit sites
- `path/file.py` lines 10-20: <what to change -- specific enough that craft acts without re-reading>

## Competing hypotheses (only if you couldn't decide -- craft tests these against the gate, cheapest first)
- Option 1: <edit> -- confirmed if the gate shows <X>
- Option 2: <edit> -- confirmed if the gate shows <Y>

## Rejected hypotheses
- H1: <considered, killed by reasoning because ___>

## Open questions
- <anything unresolved>
```

Do not include code patches. Edit sites are a specification, not a diff.

## Re-entry (outer loop -- this is how correction happens)

When the adapter includes an **AUDIT KILL REPORT** (the prior patch failed audit), the prior diagnosis was wrong or incomplete. This is the loop doing its job: the gate killed the hypothesis, and the kill is now your richest evidence. Treat it as a new observation H0 -- kill conditions generate the next hypothesis:

- The failing-test evidence in the kill report points at the code path the prior fix missed. Start Phase 2 from there.
- **Do not re-propose the killed root cause.** It's in the graph document as a dead node. Mine it for what it ruled out, then go elsewhere -- the previous suspect set was wrong, so widen or shift it.
- If a fresh diagnosis genuinely lands on the *same* root cause as the prior dead node, say so explicitly (`FIXED POINT: re-diagnosis converged on the prior root cause`). The driver halts the loop on that signal rather than spinning.

## Rules

- **Read-only, and no experiments.** No edits to the repo. No executing code, tests, prints, or scripts during diagnosis. Only reads, greps, `git log`, and reasoning. You may *imagine* experiments; you may not *run* them.
- **Quote the code.** Every claim about behavior cites file:line. No paraphrasing from memory.
- **Enumerate before asserting.** Before "the only call site is X," run `grep -rn` to verify.
- **Confidence tracks mode.** Don't claim 95% on an abduction. The mode sets the ceiling. An imagined experiment never raises confidence above what the static trace alone supports.
- **Be falsifiable, not exhaustive.** A decisive, well-reasoned hypothesis the gate can kill beats a hedged one that tries to cover everything. The loop corrects wrong guesses; it can't correct vague ones.
- **Append the graph, never truncate.** The hypothesis graph document is the crash-recovery checkpoint across the whole outer loop.
- **Stdout is the handoff.** Print the diagnosis to stdout; the driver persists it.
