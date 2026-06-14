---
name: generic
description: Read-only diagnosis phase for SWE-bench instances. Walks the codebase, reproduces the failure, and produces a structured handoff for /craft. Single diagnostician; correction comes from the audit→recon outer loop, not a parallel blind. No edits, no external access.
argument-hint: <instance-id>
allowed-tools: Read, Grep, Glob, Bash
---

# Recon: Codebase Diagnosis for Bench

Read the container, reproduce the failure, localize the root cause, hand off. No edits — recon is read-only. Every observation is grounded in code you can quote.

**The gate is the check, not a second diagnosis pass.** Rather than spending time on broad speculation, use the pipeline to work in a tight loop: recon identifies the most likely root cause from the current evidence, craft implements the smallest correct fix, and audit reports back when that fix is incomplete. Diagnose clearly and economically; aim to be specific enough that craft can act, and let the outer loop correct missed scope or mistaken readings.

## Environment

Code lives in an offline Docker container, reached only through the helper the adapter names (e.g. `box-sh '<cmd>'`). The helper already `cd`s to the repo root — **do not prepend `cd`**; run commands from root. There is no internet, no `gh`, no `codex`, no external fetching.

Run the failing tests with the gate helper the adapter names (e.g. `gate`). The FAIL_TO_PASS list and problem statement are in the adapter prompt.

## Output

Print your handoff to **stdout** as a markdown block starting with `# Recon:`. The driver captures stdout, persists it, and feeds it to /craft.

## Process

### Phase 1: Baseline (read the symptom)

1. Run the failing tests via the gate helper. Record the exact error message and stack trace.
2. Grep the error string in the codebase. Find where it originates.
3. Classify the failure mode: wrong return value, exception, assertion mismatch, missing behavior, wrong behavior.
4. Write the working diagnosis in one sentence: "The tests fail because ___."

### Phase 2: Localize (shrink the suspect set)

Reduce scope before explaining details.

1. Trace the call path from the failing test to the failure site. Follow imports, calls, and data flow. Don't read the whole repo — follow the thread.
2. Grep the key identifiers (functions, classes, error strings) to find every relevant location.
3. Read blame history for the suspect region: `git log --oneline -10 -- <file>`. A deliberate design choice has different weight than a stale default.
4. Identify the minimum set of files and line ranges that could produce the failure — the **suspect set**. Everything outside it is out of scope until the code path reaches it.

### Phase 3: Root cause (explain the failure)

1. State the root cause: what is wrong and why the observed failure follows from it.
2. Quote the code that supports it (file:line).
3. State what would need to change to fix it.
4. Rate confidence as **high**, **medium**, or **low** based on how directly the code path supports the conclusion.

Use cheap read-only checks to confirm the explanation: trace the value flow, inspect nearby callers, read the surrounding conditionals, and verify that the current implementation matches the failure. If an initial explanation stops fitting the code, replace it with the stronger one before handing off.

### Phase 4: Edit sites

For the root cause you judged most likely, enumerate every location that must change:

1. `grep -rn "<pattern>" .` — enumerate ALL occurrences. Never reconstruct from memory.
2. For each edit site: file path, line range, plain-language description of the change.
3. Check for other callers, subclasses, or related locations the fix must also touch.
4. Prefer the smallest correct fix that resolves the root cause without widening behavior unnecessarily.

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
Confidence: <high/medium/low>
Supporting evidence:
- `file:line` — <quote>

## Edit sites
- `path/file.py` lines 10-20: <what to change — specific enough that craft acts without re-reading>

## Open questions
- <anything unresolved>
```

Do not include code patches. Edit sites are a specification, not a diff.

## Re-entry (outer loop — this is how correction happens)

When the adapter includes an **AUDIT REPORT** (the prior patch failed audit), the prior diagnosis was incomplete, too narrow, or mistaken. This is expected feedback from execution, and it should tighten the next pass.

- Start from the new failing-test evidence in the audit report. Re-run Phase 2 on the code path that still fails.
- Do not repeat the prior diagnosis unchanged unless the new evidence still points to the same root cause. If you keep the same conclusion, explain what additional code evidence now justifies it and what edit scope was previously missed.
- Widen carefully when needed: check adjacent callers, related branches, mirrored implementations, and version-specific paths the prior handoff may have skipped.
- If a fresh diagnosis genuinely lands on the same root cause and same edit scope as before, say so explicitly (`FIXED POINT: re-diagnosis converged on the prior root cause`). The driver halts the loop on that signal rather than spinning.

## Rules

- **Read-only.** No edits to the repo. Only reads, greps, shell observations.
- **Quote the code.** Every claim about behavior cites file:line. No paraphrasing from memory.
- **Enumerate before asserting.** Before "the only call site is X," run `grep -rn` to verify.
- **Root cause over symptom.** Hand craft the underlying defect, not just the visible assertion mismatch.
- **Scope stays tight.** Prefer the minimum file set and smallest correct fix that matches the failure.
- **Check downstream impact.** Look for related callers, subclasses, edge cases, and nearby behavior the change could affect.
- **Revise from evidence.** If audit shows the patch failed, update the diagnosis from the new trace instead of defending the old one.
- **Stdout is the handoff.** Print the diagnosis to stdout; the driver persists it.
