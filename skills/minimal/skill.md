---
name: minimal
description: Read-only diagnosis phase for SWE-bench instances. Reproduce the failure, identify the code that needs to change, and print a concise handoff for /craft. No edits, no external access.
argument-hint: <instance-id>
allowed-tools: Read, Grep, Glob, Bash
---

# Recon: Codebase Diagnosis for Bench

Work in the container, run the failing tests, find the code path that causes the failure, and hand off the most likely fix area. Do not edit files. Use the helper commands named by the adapter, and run from the repo root.

Print your result to **stdout** as a markdown block starting with `# Recon:` so /craft can consume it. Keep the handoff concrete: what fails, where it fails, what code is responsible, and what files need to change.

Use this structure:

```markdown
# Recon: <instance-id>

## Failure summary
<what the tests check, how they fail, error message>

## Suspect set
- `path/file.py` lines 10-40: <why suspect>

## Root cause
<what is wrong and why>

## Edit sites
- `path/file.py` lines 10-20: <what needs to change>

## Open questions
- <anything unresolved>
```

If audit reports that the prior patch failed, re-run the diagnosis from the new failure output and update the handoff. Keep it read-only, grounded in the code, and specific enough that craft can implement the fix.
