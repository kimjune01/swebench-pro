---
name: ask
description: Read-only diagnosis phase for SWE-bench instances. Walks the codebase, reproduces the failure, and produces a fix-plan handoff for /craft. Single diagnostician; correction comes from the audit->ask outer loop, not a parallel blind. No edits, no external access.
argument-hint: <instance-id>
allowed-tools: Read, Grep, Glob, Bash
---

# Ask: Codebase Diagnosis for Bench

Read the container, reproduce the failure, localize the root cause, hand off. No edits -- this is read-only. Every observation is grounded in code you can quote.

**The adversary is the gate, not a second model.** Rather than running a parallel blind diagnosis, the pipeline corrects a wrong diagnosis by *iterating*: craft tests your fix against the deterministic gate, and if it's wrong, audit feeds the failure back to you as a new observation. The gate is a fresh-eyes party that doesn't share your blind spots, and the outer loop is how its failures reach you. So diagnose decisively and cheaply; don't try to be exhaustively right on the first pass -- be testable, and let the loop catch you.

## Environment

Code lives in an offline Docker container, reached only through the helper the adapter names (e.g. `box-sh '<cmd>'`). The helper already `cd`s to the repo root -- **do not prepend `cd`**; run commands from root. There is no internet, no `gh`, no `codex`, no external fetching.

Run the failing tests with the gate helper the adapter names (e.g. `gate`). The FAIL_TO_PASS list and problem statement are in the adapter prompt.

## Output

Print your handoff to **stdout** as a markdown block starting with `# Diagnosis:`. The driver captures stdout, persists it, and feeds it to /craft. Also append your working notes to the document the adapter names (it accumulates across the outer loop -- never truncate it).

## Process

### Phase 1: Baseline (read the symptom)

1. Run the failing tests via the gate helper. Record the exact error message and stack trace.
2. Grep the error string in the codebase. Find where it originates.
3. Classify the failure mode: wrong return value, exception, assertion mismatch, missing behavior, wrong behavior.
4. Write your initial read: "The tests fail because ___." One sentence.

### Phase 2: Localize (shrink the suspect set)

Reduce before explaining.

1. Trace the call path from the failing test to the failure site. Follow imports, calls, data flow. Don't read the whole repo -- follow the thread.
2. Grep the key identifiers (functions, classes, error strings) to find every relevant location.
3. Read blame history for the suspect region: `git log --oneline -10 -- <file>`. A deliberate design choice has different weight than a default nobody revisited.
4. Identify the minimum set of files and line ranges that could produce the failure -- the **suspect set**. Everything outside it is irrelevant until proven otherwise.

### Phase 3: Root cause

1. State the root-cause explanation: what is wrong and why.
2. Quote the code that supports it (file:line).
3. State what would need to change to fix it.

Distinguish competing explanations with cheap read-only perturbations: temporary print statements via the box helper, reading intermediate data, careful trace-through. Prune explanations the code directly contradicts.

**If two explanations survive and you can't cheaply decide between them, don't force a pick** -- hand both to craft as competing edit sites (see below). Craft will test them against the gate, cheapest first. The gate decides what your reading couldn't.

### Phase 4: Edit sites

For the surviving explanation (or the few that survive), enumerate every location that must change:

1. `grep -rn "<pattern>" .` -- enumerate ALL occurrences. Never reconstruct from memory.
2. For each edit site: file path, line range, plain-language description of the change.
3. Check for other callers, subclasses, or related locations the fix must also touch.

### Phase 5: Emit

Print to stdout:

```markdown
# Diagnosis: <instance-id>

## Failure summary
<one paragraph: what the tests check, how they fail, error message>

## Suspect set
- `path/file.py` lines 10-40: <why suspect>

## Root cause
<2-3 sentences: what is wrong, why, the code path>
Supporting evidence:
- `file:line` -- <quote>

## Edit sites
- `path/file.py` lines 10-20: <what to change -- specific enough that craft acts without re-reading>

## Competing explanations (only if you couldn't decide -- craft tests these against the gate, cheapest first)
- Option 1: <edit> -- confirmed if the gate shows <X>
- Option 2: <edit> -- confirmed if the gate shows <Y>

## Ruled out
- <considered, dropped because ___>

## Open questions
- <anything unresolved>
```

Do not include code patches. Edit sites are a specification, not a diff.

## Re-entry (outer loop -- this is how correction happens)

When the adapter includes a **PRIOR FIX FAILED** report, the prior diagnosis was wrong or incomplete. This is the loop doing its job: the gate killed the fix, and that failure is now your richest evidence. Treat it as a new observation:

- The failing-test evidence in the report points at the code path the prior fix missed. Start Phase 2 from there.
- **Do not re-propose the failed root cause.** It's in your notes as a dead end. Mine it for what it ruled out, then go elsewhere -- the previous suspect set was wrong, so widen or shift it.
- If a fresh diagnosis genuinely lands on the *same* root cause as the failed attempt, say so explicitly (`FIXED POINT: re-diagnosis converged on the prior root cause`). The driver halts the loop on that signal rather than spinning -- a third identical diagnosis won't help.

## Rules

- **Read-only.** No edits to the repo. Only reads, greps, shell observations.
- **Quote the code.** Every claim about behavior cites file:line. No paraphrasing from memory.
- **Enumerate before asserting.** Before "the only call site is X," run `grep -rn` to verify.
- **Be testable, not exhaustive.** A decisive, cheaply-tested explanation the gate can check beats a hedged one that tries to cover everything. The loop corrects wrong guesses; it can't correct vague ones.
- **Append your notes, never truncate.** The notes document is the crash-recovery checkpoint across the whole outer loop.
- **Stdout is the handoff.** Print the diagnosis to stdout; the driver persists it.
