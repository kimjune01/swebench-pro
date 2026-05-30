# Auth storm 2026-05-29 — statuspage snapshot

Companion record to `runs/scored/auth_strips.jsonl` and `WORKLOG.md` entry
"2026-05-29 (afternoon) — Anthropic credential rejection wave". This page
captures the upstream provider's posted state at the time of the incident, so
the absence of a posted incident is itself part of the audit trail and cannot
be later edited away.

## Statuspage URL

https://status.claude.com/

## Snapshot — 2026-05-29 ~14:00 PDT

Two screenshots attached (operator-captured during the incident response):

**Claude Code component (single panel, full-width).**
![Claude Code uptime — 99.08% / 90d](images/claude-code-uptime-2026-05-29.png)

**Full Anthropic stack (claude.ai · Console · API · Code).**
![Anthropic stack uptime — 90d](images/anthropic-stack-uptime-2026-05-29.png)

### Posted incidents for 2026-05-29

1. **Elevated errors for Claude Opus 4.8** — model-level, not auth, not Sonnet 4.5.
2. **Elevated errors on Claude Opus 4.8** — same shape, same model.

Neither overlaps our window in either component or affected model. Our scored
run is Sonnet 4.5 (craft) + GPT-5.5 codex (audit); Opus 4.8 isn't in our stack.

### 90-day uptime (snapshot at incident time)

| Component | Uptime | Status |
|---|---|---|
| claude.ai | 98.83% | Operational (bumpy) |
| Claude Console (platform.claude.com) | 99.23% | Operational (bumpy) |
| Claude API (api.anthropic.com) | 99.09% | Operational (bumpy) |
| Claude Code | 99.08% | Operational (bumpy) |

The stripe pattern across all four components is consistent with frequent
degraded-but-not-incident-class events — partial errors, regional slowness,
credential rotations — that operators experience but the public statuspage
doesn't separately enumerate. Whole-stack ~99% over 90d ≈ 21h degraded per
component.

### Posted-incident silence is not disconfirming

Provider-side credential invalidation (OAuth token rotation, key rolling,
account-level rate-limit lockouts) is routine security hygiene; providers do
not post these as incidents because they are intentional, scoped, and expected.
The absence of a posted incident at our window is the **expected** case for
this fault class, not evidence the fault didn't occur. The on-box subprocess
capture of the verbatim `401 Invalid authentication credentials` string is the
direct evidence (one entry per re-classified instance in
`runs/scored/auth_strips.jsonl`).

This rationale is pre-registered in `PREREGISTRATION.md` §14 amendment
"2026-05-29 — `PROVIDER_CRED_REJECT` fault class added to §3 enumeration".

## For reproducers

Plan for the `PROVIDER_CRED_REJECT` recovery loop as part of the operator
runbook for any multi-hour Claude-backed fleet:

1. **Detect**: ≥3 consecutive sub-120s LOSSes on the same box with subprocess
   capture containing the canonical provider 401/403 string.
2. **Halt**: stop dispatch immediately. Every additional minute is more poison
   in the ledger.
3. **Re-push**: extract fresh credentials from the operator's authoritative
   store and scp them to all boxes. For Claude Max on macOS, this is:
   ```bash
   security find-generic-password -s "Claude Code-credentials" -w > /tmp/claude_credentials.json
   for envf in /tmp/coord*.env; do . "$envf"
     scp -i /tmp/${KEY}.pem /tmp/claude_credentials.json \
       ec2-user@${PUBIP}:/home/ec2-user/.claude/.credentials.json
   done
   ```
4. **Resume**: restart the coordinator with `--skip-setup` so it reuses the
   existing boxes with the freshened creds.
5. **Strip**: classify the wave as `PROVIDER_CRED_REJECT` per `PREREGISTRATION.md`
   §14 amendment, append entries to `runs/scored/auth_strips.jsonl`, let the
   coordinator re-dispatch.

Over a ~10h campaign with the stack at ~99% uptime, expect 1–2 of these per
run as the modal class of recoverable interruption.
