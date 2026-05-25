#!/usr/bin/env python3
"""Rung 4 driver — single-diagnostician recon + outer loop. Grading is the official eval.py.

Per instance (model runs LOCALLY; SUT is an offline container on the box):
  pull -> run -> git apply test_patch -> COMMIT it -> warm online (caches deps,
  captures FAIL-ON-BASE) -> cut net -> OUTER LOOP:

    recon  : ONE Sonnet diagnosis -> structured handoff. The adversary is the gate
             + the outer loop (iteration), not a parallel blind.
    craft  : Sonnet generates the patch, a LOCAL codex subagent challenges it (volley),
             the gate arbitrates. gate loop (<=8), live in container.
    audit  : full gate, classify regressions vs the captured fail-on-base, emit
             VERDICT + RE-ENTER route. NO git stash (the base capture is the baseline).

CONTAMINATION NOTE: craft uses codex (GPT-5.5, recent cutoff). This is a LEADERBOARD /
spectacle configuration, NOT a contamination-clean run — codex's cutoff postdates the
instances. For the clean-science track (post-cutoff firewall), drop the codex volley and
run craft single-model. codex runs on the plan machine; only the container is offline.

  If audit != RESOLVED and depth < MAX_OUTER:
    RE-ENTER: recon  -> re-diagnose (kill report = new H0; recon re-runs)
    RE-ENTER: craft  -> narrow the over-broad fix (recon was right; skip re-diagnose)
  Fixed-point halt: recon reports re-diagnosis converged on the prior root cause.

  Capture model_patch = `git diff HEAD` regardless of verdict -> teardown.

Hypothesis graph accumulates per instance at r4_hgraph_<iid>.md (crash checkpoint).

RUNG 5 = RUNG 4 + the attestation hash-as-precondition (PRO_PORT.md lever #3), and it runs
LOCALLY (OrbStack on the Mac), not over ssh to a box. Two changes from rung4:

  1. LOCAL DISPATCH. `run()` executes commands in a local shell instead of `ssh sudo ...`;
     x86_64 eval images run under `--platform linux/amd64` emulation. No box, no sudo.

  2. THE CONTRACT. The final verdict is NOT the agent's audit verdict and NOT the live-tree
     gate. After capture, the SERIALIZED source-only prediction is re-attested on a FRESH
     CLEAN container and graded by swebench's OWN parser. The win carries a prediction
     sha256; a red attestation overrides an agent "RESOLVED" (the gate-divergence class —
     pytest-5787, django-14170 — is caught here instead of slipping through green).

  3. CAPTURE-AT-TIMEOUT. The craft `claude` call is capped (CRAFT_CAP, default 3600s) and the
     timeout is NON-FATAL: the agent edits the container, so on a cap-trip we break the loop and
     capture the in-progress `git diff HEAD` instead of crashing to a 0-byte patch. Targets the
     craft-orchestration-hang DNFs (sympy-19040, django-15957, matplotlib-25311) where the suite
     is fast (P1: 7.79s) but the agent/codex ran away for the full hour. Caps are env-overridable.

Usage: rung5_driver.py <round_tasks.json> <instance_id> [...]   (runs locally on OrbStack)
"""
import json, subprocess, sys, time, pathlib, os, re, hashlib
from datasets import load_dataset
from swebench.harness.test_spec.test_spec import make_test_spec
from swebench.harness.grading import (
    get_logs_eval, get_eval_tests_report, get_resolution_status)
from swebench.harness.constants import (
    START_TEST_OUTPUT, END_TEST_OUTPUT, ResolvedStatus)

HERE = pathlib.Path("/tmp/swebench-abduction")
MAX_OUTER = 3
# Wall-clock caps (s) on the per-stage `claude` subprocess. Craft is capped lower because the
# DNFs were craft orchestration hangs (P1: the suite is fast); on a craft cap-trip we capture
# the in-progress container diff rather than erroring to a 0-byte patch.
RECON_CAP  = int(os.environ.get("RECON_CAP", "2000"))
CRAFT_CAP  = int(os.environ.get("CRAFT_CAP", "3600"))
AUDIT_CAP  = int(os.environ.get("AUDIT_CAP", "1200"))

# Skills are repo-local (hardlinked to the canonical copies). Resolve relative to
# this file so the repo is self-contained for anyone who clones it.
_SKILLS = pathlib.Path(__file__).resolve().parent.parent / "skills"
RECON_SKILL = (_SKILLS / "recon/skill.md").read_text()
CRAFT_SKILL = (_SKILLS / "craft/skill.md").read_text()
AUDIT_SKILL = (_SKILLS / "audit/skill.md").read_text()

# Model = Claude Sonnet by default; override with RCA_MODEL for any model your
# `claude` CLI / API key can reach.
MODEL = os.environ.get("RCA_MODEL", "claude-sonnet-4-5")

def plan_env():
    """Auth-mode agnostic. Default: pass the environment through, so an
    ANTHROPIC_API_KEY (API access) is honored and, if absent, the `claude` CLI
    falls back to its logged-in subscription session. Set CLAUDE_SUBSCRIPTION=1
    to force the subscription path by dropping the API key (useful when you have
    a key in your shell but want to bill a Max/Pro plan instead). codex uses its
    own auth (ChatGPT login or OPENAI_API_KEY) untouched."""
    e = os.environ.copy()
    if os.environ.get("CLAUDE_SUBSCRIPTION"):
        e.pop("ANTHROPIC_API_KEY", None)
    return e

TASKS = {d["instance_id"]: d for d in json.load(open(sys.argv[1]))}
STEM = pathlib.Path(sys.argv[1]).stem
LEDGER = HERE/f"rung5_results_{STEM}.jsonl"
PATCHES = HERE/f"rung5_patches_{STEM}.jsonl"
PLATFORM = os.environ.get("PLATFORM", "linux/amd64")

def _localize(remote):
    """Rewrite the box-shaped command (built with `sudo docker ...`) for local OrbStack:
    drop sudo, and force --platform on the image-creating subcommands (pull/run) so x86_64
    eval images run under emulation on arm64. Other docker subcommands need no platform."""
    remote = remote.replace("sudo docker run -d ", f"docker run -d --platform {PLATFORM} ")
    remote = remote.replace("sudo docker pull ", f"docker pull --platform {PLATFORM} ")
    return remote.replace("sudo docker ", "docker ")

def ssh(remote, timeout=600, inp=None):
    """Local dispatch — the rung4 call sites are unchanged; only the destination moved
    from the box to this machine's shell."""
    return subprocess.run(["bash","-lc", _localize(remote)],
        capture_output=True, text=True, timeout=timeout, input=inp)

def log(obj):
    with open(LEDGER,"a") as f: f.write(json.dumps(obj)+"\n")
    sys.stderr.write(f"[{obj.get('instance')}] {obj.get('stage')}: {obj.get('msg','')}\n")
    sys.stderr.flush()

def setup(inst):
    iid = inst["instance_id"]; img = inst["image_name"].replace("docker.io/","")
    ssh(f"sudo docker pull {img} 2>&1 | tail -1", timeout=1200)
    cid = ssh(f"sudo docker run -d {img} sleep infinity").stdout.strip()
    if not cid or len(cid) < 12:
        log({"instance":iid,"stage":"setup","msg":f"run failed: {cid[:80]}"}); return None
    root = inst.get("repo_dir") or ssh(f"sudo docker exec {cid} pwd").stdout.strip() or "/"
    # Stage the test patch OUTSIDE the repo (/tmp, not {root}) so `git add -A` can't
    # sweep the scaffolding file into the tree. A committed tp.patch leaks a `delete
    # tp.patch` hunk into the captured prediction, which fails to apply on the official
    # harness's clean base and trips git's -R heuristic (django-15987 false-positive).
    ssh(f"cat > /tmp/tp.patch && sudo docker cp /tmp/tp.patch {cid}:/tmp/tp.patch",
        inp=inst["test_patch"])
    ap = ssh(f"sudo docker exec {cid} bash -lc 'cd {root} && git apply /tmp/tp.patch && "
             f"git -c user.email=r4@x -c user.name=r4 add -A && "
             f"git -c user.email=r4@x -c user.name=r4 commit -q -m testpatch && "
             f"echo APPLIED $(git rev-parse HEAD)'")
    if "APPLIED" not in ap.stdout:
        log({"instance":iid,"stage":"setup","msg":f"git apply/commit failed: {(ap.stdout+ap.stderr)[:200]}"})
        return (cid, root, False, None)
    tsha = ap.stdout.split("APPLIED")[1].strip().split()[0]
    return (cid, root, True, tsha)

def warm_and_failbase(inst, cid, root):
    """Run the official test_cmd ONCE online: caches deps AND captures fail-on-base.
    The captured output is audit's baseline for 'pre-existing failure'."""
    tc = (inst.get("install_config") or {}).get("test_cmd","")
    if not tc: return ""
    act = inst.get("env_activate",""); pre = f"{act} 2>/dev/null; " if act else ""
    r = ssh(f"sudo docker exec {cid} bash -lc 'cd {root} && {pre}{tc} 2>&1 | tail -120'", timeout=1800)
    tag = inst["instance_id"].replace("/","_")
    base = f"$ {tc}\n\n{r.stdout}{r.stderr}"
    (HERE/f"r4_failbase_{tag}.txt").write_text(base)
    return base

def helpers(inst, cid, root, tsha):
    iid = inst["instance_id"]; tag = iid.replace("/","_").replace("__","_")
    act = inst.get("env_activate",""); pre = f"{act} 2>/dev/null; " if act else ""
    box = f"/tmp/box-sh-{tag}"
    s = (f"#!/bin/bash\n"
         f"printf '%s' \"$*\" | docker exec -i {cid} bash -c 'cat >/tmp/_bc' && "
         f"docker exec {cid} bash -lc 'cd {root} && {pre}bash /tmp/_bc'\n")
    pathlib.Path(box).write_text(s); subprocess.run(["chmod","+x",box])
    tc = (inst.get("install_config") or {}).get("test_cmd","").replace("'","'\\''")
    # SOURCE-ONLY GATE. Restore the gold test files (committed at tsha) before EVERY gate
    # run, so the agent's stopping signal is graded against the GOLD tests — exactly what
    # testify and the official harness do (they reset test files to base and re-apply the
    # gold test patch). Without this, an agent edit to a test false-greens the gate
    # (django-14170): the gate runs the WEAKENED test, capture strips the edit, and testify
    # then reds the source-only patch — caught, but the agent already stopped on the lie.
    # Restoring closes the escape hatch: the agent must fix SOURCE. Gold-blind on public Pro
    # (paths come from the test_patch headers); on private Pro there is no visible F2P gate,
    # so testfiles is empty, the prefix is empty, and the source-only CAPTURE is the backstop.
    testfiles = [l[6:] for l in inst.get("test_patch","").splitlines() if l.startswith("+++ b/")]
    restore = f"git checkout {tsha} -- {' '.join(testfiles)} 2>/dev/null; " if testfiles else ""
    gate = f"/tmp/gate-{tag}"
    g = (f"#!/bin/bash\n"
         f"docker exec {cid} bash -lc 'cd {root} && {restore}{pre}{tc} 2>&1 | tail -120'\n")
    pathlib.Path(gate).write_text(g); subprocess.run(["chmod","+x",gate])
    return box, gate

def claude(prompt_text, cwd, tag, timeout=2400):
    pf = HERE/f"r4_prompt_{tag}.txt"; pf.write_text(prompt_text)
    cwd = pathlib.Path(cwd); cwd.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    timed_out = False
    try:
        p = subprocess.run(
            ["claude","--print","--model","claude-sonnet-4-5",
             "--dangerously-skip-permissions","--disallowedTools","WebSearch,WebFetch,Task"],
            stdin=open(pf), capture_output=True, text=True, timeout=timeout,
            cwd=str(cwd), env=plan_env())
        stdout, stderr = p.stdout, p.stderr
    except subprocess.TimeoutExpired as e:
        # Non-fatal: the agent edits the CONTAINER, so its in-progress work survives the kill.
        # Return partial stdout + the flag; the caller decides whether to capture-at-timeout.
        timed_out = True
        stdout = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
    dt = time.time()-t0
    (HERE/f"r4_out_{tag}.txt").write_text(stdout+"\n---STDERR---\n"+stderr)
    return stdout, dt, timed_out

# ── recon: single diagnostician (gate + outer loop is the adversary) ──────────

def recon(inst, box, gate, hgraph, kill_report, depth):
    iid = inst["instance_id"]; tag = f"recon_{iid.replace('/','_')}_d{depth}"
    added = "\n".join(l[1:] for l in inst["test_patch"].splitlines()
                      if l.startswith("+") and not l.startswith("+++"))
    testfiles = [l[6:] for l in inst["test_patch"].splitlines() if l.startswith("+++ b/")]
    kr = (f"\nAUDIT KILL REPORT (prior diagnosis failed — treat as new H0; do NOT "
          f"re-propose the killed root cause):\n{kill_report}\n" if kill_report else "")
    adapter = (
        f"You will follow the /recon skill below. Diagnose from the code alone and print "
        f"your handoff to stdout starting `# Recon:`.\n\n"
        f"ENVIRONMENT:\n"
        f"- Code is in an offline container. Run ALL reads via: `{box} '<cmd>'` "
        f"(it already cd's to repo root — do NOT prepend cd). No internet, no gh, no codex.\n"
        f"- Run the failing tests: `{gate}`\n"
        f"- The fix must be SOURCE-ONLY: test files are gold-locked (the gate restores them "
        f"before every run). Never hand off 'edit/weaken the test' as a fix — diagnose the "
        f"source cause that makes the GOLD tests pass.\n"
        f"- Append hypothesis nodes to: {hgraph} (never truncate).\n"
        f"- Failing tests live in: {testfiles}\n\n"
        f"FAIL_TO_PASS (must pass): {str(inst['FAIL_TO_PASS'])[:600]}\n\n"
        f"PROBLEM:\n{inst['problem_statement'][:4000]}\n\n"
        f"ADDED FAILING TESTS:\n{added[:2500]}\n"
        f"{kr}"
        f"\n===================== THE /recon SKILL =====================\n{RECON_SKILL}\n"
    )
    out, dt, _to = claude(adapter, HERE/f"r4_cwd_{tag}", tag, timeout=RECON_CAP)
    fixed_point = "FIXED POINT" in out.upper()
    log({"instance":iid,"stage":"recon","depth":depth,"wall_s":round(dt),
         "fixed_point":fixed_point,"timed_out":_to})
    return out, fixed_point

# ── craft ─────────────────────────────────────────────────────────────────────

def craft(inst, box, gate, hgraph, handoff, kill_report, depth):
    iid = inst["instance_id"]; tag = f"craft_{iid.replace('/','_')}_d{depth}"
    narrow = (f"\nAUDIT KILL REPORT — a PASS_TO_PASS test regressed. recon was right; "
              f"the fix is too broad. Enter NARROW mode: keep FAIL_TO_PASS passing AND "
              f"restore the regressed test.\n{kill_report}\n" if kill_report else "")
    adapter = (
        f"You will follow the /craft skill below. You generate the patch from the recon "
        f"handoff; codex challenges it; the gate arbitrates.\n\n"
        f"ENVIRONMENT:\n"
        f"- Offline container. Edit/read via: `{box} '<cmd>'` (already at repo root — "
        f"do NOT prepend cd; use sed/python3/patch inside it).\n"
        f"- Verify with the gate: `{gate}` (max 8 iterations).\n"
        f"- SOURCE-ONLY. Test files are gold-locked: the gate restores them to the reference "
        f"version before every run, so any edit you make to a test is silently reverted and "
        f"never graded (the official harness does the same). A green gate must come from "
        f"changing SOURCE under the package, not from weakening a test. If a PASS_TO_PASS test "
        f"regresses, the fix is too broad — narrow the source change; do NOT touch the test.\n"
        f"- `codex` runs LOCALLY (not in the container, so it can't read the repo or run "
        f"the gate). Bridge it: pull file contents via the box helper, paste them into the "
        f"codex prompt. Invoke via stdin heredoc: `cat <<'EOF' | codex exec -` ... `EOF`. "
        f"ALWAYS volley with codex: show it your drafted diff BEFORE the first gate run, "
        f"and show it the gate output + diff on EVERY gate failure before revising. Never "
        f"gate a fix codex hasn't seen. ~6-8 codex calls; it converges in 2-3.\n"
        f"- Append gate-loop nodes to: {hgraph}.\n\n"
        f"FAIL_TO_PASS (must pass): {str(inst['FAIL_TO_PASS'])[:600]}\n\n"
        f"RECON HANDOFF (canonical — act on this):\n{handoff[:7000]}\n"
        f"{narrow}\n"
        f"When all FAIL_TO_PASS pass in the gate, print RESOLVED (a green gate ends the "
        f"loop even if codex still has notes). If the diagnosis looks wrong after 3 stuck "
        f"iterations, print `NOT-RESOLVED — re-diagnose`. Only judge from gate output — "
        f"never your reasoning, never codex's approval.\n\n"
        f"===================== THE /craft SKILL =====================\n{CRAFT_SKILL}\n"
    )
    out, dt, timed_out = claude(adapter, HERE/f"r4_cwd_{tag}", tag, timeout=CRAFT_CAP)
    redirect = "re-diagnose" in out.lower()
    claim = ("RESOLVED" in out) and ("NOT-RESOLVED" not in out)
    log({"instance":iid,"stage":"craft","depth":depth,"wall_s":round(dt),
         "claim":claim,"wants_rediagnose":redirect,"timed_out":timed_out})
    return out, redirect, timed_out

# ── audit ─────────────────────────────────────────────────────────────────────

def audit(inst, box, gate, hgraph, failbase, depth):
    iid = inst["instance_id"]; tag = f"audit_{iid.replace('/','_')}_d{depth}"
    adapter = (
        f"You will follow the /audit skill below. The craft edits are live in the tree.\n\n"
        f"ENVIRONMENT:\n"
        f"- Offline container. Read via `{box} '<cmd>'` (already at root). NEVER mutate "
        f"the tree (no git stash / apply / edits).\n"
        f"- Full gate: `{gate}`.\n"
        f"- Append breakdown to: {hgraph}.\n\n"
        f"FAIL_TO_PASS: {str(inst['FAIL_TO_PASS'])[:600]}\n"
        f"PASS_TO_PASS: {str((inst.get('PASS_TO_PASS') or []))[:800]}\n\n"
        f"FAIL-ON-BASE CAPTURE (your baseline for pre-existing failures — a test failing "
        f"here was already broken before the patch):\n{failbase[:3500]}\n\n"
        f"End with two lines exactly:\nVERDICT: <RESOLVED|NOT_RESOLVED|PARTIAL>\n"
        f"RE-ENTER: <recon|craft|none>\n\n"
        f"===================== THE /audit SKILL =====================\n{AUDIT_SKILL}\n"
    )
    out, dt, _to = claude(adapter, HERE/f"r4_cwd_{tag}", tag, timeout=AUDIT_CAP)
    verdict, route = "UNKNOWN", "none"
    for line in reversed(out.strip().splitlines()):
        l = line.strip()
        m = re.match(r"VERDICT:\s*(RESOLVED|NOT_RESOLVED|PARTIAL)", l)
        if m and verdict == "UNKNOWN": verdict = m.group(1)
        m = re.match(r"RE-ENTER:\s*(recon|craft|none)", l)
        if m and route == "none" and "RE-ENTER:" in l: route = m.group(1)
    log({"instance":iid,"stage":"audit","depth":depth,"wall_s":round(dt),
         "verdict":verdict,"route":route})
    return out, verdict, route

# ── patch capture / teardown ──────────────────────────────────────────────────

import fnmatch

# Build artifacts / agent backups that are never part of a real fix. Matched on the
# diff's b/ path; dropped from the captured prediction regardless of whether the
# in-container `find` cleanup fired (it silently missed *.bak on django-13023).
_DETRITUS_GLOBS = ("*.bak", "*.bak[0-9]*", "*.orig", "*.rej", "*.pyc", "*.so")
_DETRITUS_DIRS = ("__pycache__/", ".pytest_cache/", "result_images/", ".egg-info/")

def _is_detritus(path):
    if any(fnmatch.fnmatch(path, g) for g in _DETRITUS_GLOBS): return True
    return any(seg in path for seg in _DETRITUS_DIRS)

# Test-path conventions, used ONLY as a private-Pro fallback when the gold test_patch
# (and thus the exact testfiles list) isn't visible. On public Pro the exact list is
# precise and this is never consulted.
_TESTFILE_GLOBS = ("test_*.py", "*_test.py", "tests.py", "conftest.py")
def _is_testfile(path):
    base = path.rsplit("/", 1)[-1]
    if any(fnmatch.fnmatch(base, g) for g in _TESTFILE_GLOBS): return True
    p = f"/{path}"
    return p.startswith("/tests/") or "/tests/" in p or "/test/" in p

def _strip_test_blocks(diff, testfiles):
    """Drop per-file blocks the official harness owns (test files) or that are pure
    detritus (build artifacts, *.bak backups). Done in Python on the full diff —
    shell-side `:(exclude)` pathspecs collide with the bash -lc single-quote wrapping
    and silently empty the whole capture; the `find -delete` cleanup is also unreliable
    through that quoting. This pass is the quoting-safe backstop. Subtractive only:
    these paths are never a legitimate fix, so dropping them can't break a valid patch.

    Public Pro: `testfiles` is the exact gold list (precise). Private Pro: it's empty, so
    fall back to test-path conventions — the source-only contract must still hold when the
    held-out test set is invisible."""
    tf = set(testfiles or [])
    use_convention = not tf
    out, keep = [], True
    for line in diff.splitlines(keepends=True):
        if line.startswith("diff --git "):
            # "diff --git a/<p> b/<p>" — take the b/ path
            parts = line.split()
            bpath = parts[3][2:] if len(parts) >= 4 and parts[3].startswith("b/") else None
            is_test = (bpath in tf) or (use_convention and bool(bpath) and _is_testfile(bpath))
            keep = (not is_test) and not (bpath and _is_detritus(bpath))
        if keep:
            out.append(line)
    return "".join(out)

def capture_patch(inst, cid, root, tsha):
    iid = inst["instance_id"]; tag = iid.replace("/","_")
    # Strip agent detritus AND generated test artifacts before diffing, so the captured
    # model_patch is the fix, not test-run output (matplotlib result_images, pyc, caches,
    # compiled libs). Without this, `git add -A` swept 100s of KB of artifacts into patches.
    r = ssh(f"sudo docker exec {cid} bash -lc 'cd {root} && "
            f"find . -path ./.git -prune -o \\( -name \"*.bak\" -o -name \"*.bak[0-9]*\" -o -name \"*.orig\" -o -name \"*.pyc\" -o -name \"*.so\" \\) -print -delete >/dev/null 2>&1; "
            f"find . -path ./.git -prune -o -type d \\( -name __pycache__ -o -name .pytest_cache -o -name result_images -o -name \"*.egg-info\" \\) -exec rm -rf {{}} + >/dev/null 2>&1; "
            f"git add -A >/dev/null 2>&1; "
            f"git -c core.fileMode=false diff {tsha}'", timeout=120)
    # Source-only prediction: drop the test files the official harness owns (it resets
    # them to base and re-applies the gold test patch itself). An incidental agent edit to
    # a test file collides with that re-application and trips git's -R heuristic, reversing
    # the real fix (django-15987 false-positive). Paths come from the test_patch headers.
    testfiles = [l[6:] for l in inst["test_patch"].splitlines() if l.startswith("+++ b/")]
    patch = _strip_test_blocks(r.stdout, testfiles)
    diag = ssh(f"sudo docker exec {cid} bash -lc 'cd {root} && "
               f"echo ===STATUS===; git status --short | head -40; "
               f"echo ===LOG===; git log --oneline -4; "
               f"echo ===STAT===; git diff {tsha} --stat | tail -20'", timeout=120)
    (HERE/f"r4_capture_diag_{tag}.txt").write_text(diag.stdout+diag.stderr)
    if not patch.strip():
        log({"instance":iid,"stage":"capture","msg":"EMPTY patch — see capture_diag"})
    return patch

def verify_gate(inst, cid, root, tsha):
    """Driver-side final gate run on the agent's tree, AFTER the loop. Two purposes:
    (1) an independent confirmation of the verdict (we re-run the tests ourselves
    rather than trusting the agent's audit), and (2) the saved passing-test output
    artifact for this trial. Saved per instance as r4_passgate_<id>.txt. Restores the
    gold test files first (same source-only contract as the iteration gate), so the saved
    artifact reflects the gold tests, never an agent-weakened one."""
    tc = (inst.get("install_config") or {}).get("test_cmd","")
    if not tc: return "", None
    act = inst.get("env_activate",""); pre = f"{act} 2>/dev/null; " if act else ""
    testfiles = [l[6:] for l in inst.get("test_patch","").splitlines() if l.startswith("+++ b/")]
    restore = f"git checkout {tsha} -- {' '.join(testfiles)} 2>/dev/null; " if testfiles else ""
    r = ssh(f"sudo docker exec {cid} bash -lc 'cd {root} && {restore}{pre}{tc} 2>&1 | tail -300'", timeout=1800)
    tag = inst["instance_id"].replace("/","_")
    out = f"$ {tc}\n\n{r.stdout}{r.stderr}"
    (HERE/f"r4_passgate_{tag}.txt").write_text(out)
    # independent F2P check — PYTEST-SPECIFIC. For non-pytest runners (django runtests,
    # sympy bin/test) the output isn't "PASSED <id>"-shaped, so return None (unknown)
    # rather than a misleading False. The official grader is the authority regardless.
    f2p = inst.get("FAIL_TO_PASS") or []
    pytest_shaped = ("PASSED" in r.stdout) or re.search(r"\d+ passed", r.stdout)
    if not pytest_shaped:
        return out, None
    def passed(name):
        base = name.split("::")[-1]
        return (f"PASSED {name}" in r.stdout) or (f"{name} PASSED" in r.stdout) or \
               (f"PASSED" in r.stdout and base in r.stdout and f"FAILED {name}" not in r.stdout)
    all_f2p_pass = all(passed(n) for n in f2p) if f2p else None
    return out, all_f2p_pass

def teardown(inst, cid):
    img = inst["image_name"].replace("docker.io/","")
    ssh(f"sudo docker rm -f {cid} 2>/dev/null; sudo docker rmi {img} 2>/dev/null; echo cleaned")

# ── testify: the attestation contract (the rung5 addition) ────────────────────

_DS = None
def _spec(iid):
    """swebench TestSpec for iid — selects the official per-repo log parser. Dataset is
    loaded once and cached."""
    global _DS
    if _DS is None:
        _DS = {r["instance_id"]: r
               for r in load_dataset("princeton-nlp/SWE-bench_Verified", split="test")}
    return make_test_spec(_DS[iid], namespace="swebench")

def testify(inst, patch):
    """THE CONTRACT. Re-grade the captured SERIALIZED source-only prediction on a FRESH,
    CLEAN container, scored by swebench's OWN parser — so the verdict equals the official
    grader's by construction, not by trusting the agent's audit or the live-tree gate. A
    submittable win must come back here resolved=True AND carry prediction_sha256; a red
    attestation against an agent 'RESOLVED' is the caught gate-divergence."""
    iid = inst["instance_id"]; tag = iid.replace("/","_")
    pred_sha = hashlib.sha256(patch.encode()).hexdigest()
    base = {"instance_id": iid, "prediction_sha256": pred_sha, "resolved": False}
    if not patch.strip():
        return {**base, "decision": "rejected", "reason": "empty prediction"}
    img = inst["image_name"].replace("docker.io/","")
    cid = ssh(f"sudo docker run -d {img} sleep infinity").stdout.strip()
    if len(cid) < 12:
        return {**base, "decision": "errored", "reason": "testify container did not start"}
    try:
        root = inst.get("repo_dir", "/testbed")
        ssh(f"cat > /tmp/tp_at.patch && sudo docker cp /tmp/tp_at.patch {cid}:/tmp/tp.patch",
            inp=inst["test_patch"])
        ap = ssh(f"sudo docker exec {cid} bash -lc 'cd {root} && git apply /tmp/tp.patch && "
                 f"git -c user.email=a@x -c user.name=a add -A && "
                 f"git -c user.email=a@x -c user.name=a commit -q -m tp && echo OK'")
        if "OK" not in ap.stdout:
            return {**base, "decision": "errored", "reason": "test patch apply failed"}
        ssh(f"cat > /tmp/pred_at.patch && sudo docker cp /tmp/pred_at.patch {cid}:/tmp/pred.patch",
            inp=patch)
        apr = ssh(f"sudo docker exec {cid} bash -lc 'cd {root} && git apply /tmp/pred.patch && echo OK'")
        if "OK" not in apr.stdout:
            # Official harness would also fail to apply this on a clean base. Honest red.
            return {**base, "decision": "rejected", "reason": "prediction did not apply on clean base",
                    "apply_stderr": apr.stderr[-400:]}
        tc = (inst.get("install_config") or {}).get("test_cmd", "")
        act = inst.get("env_activate", ""); pre = f"{act} 2>/dev/null; " if act else ""
        r = ssh(f"sudo docker exec {cid} bash -lc 'cd {root} && {pre}{tc}'", timeout=1800)
        # Markers wrapped in Python (not shell) — sidesteps the nested single-quote trap.
        log_fp = str(HERE/f"r5_testify_{tag}.log")
        pathlib.Path(log_fp).write_text(
            f"{START_TEST_OUTPUT}\n{r.stdout}{r.stderr}\n{END_TEST_OUTPUT}\n")
        status_map, found = get_logs_eval(_spec(iid), log_fp)
        report = get_eval_tests_report(status_map, {
            "FAIL_TO_PASS": inst.get("FAIL_TO_PASS", []),
            "PASS_TO_PASS": inst.get("PASS_TO_PASS", [])})
        resolution = get_resolution_status(report)
        return {**base, "decision": "decided", "markers_found": found,
                "resolution": resolution,
                "resolved": resolution == ResolvedStatus.FULL.value,
                "f2p_failures": report["FAIL_TO_PASS"]["failure"],
                "p2p_failures": report["PASS_TO_PASS"]["failure"],
                "f2p_pass": len(report["FAIL_TO_PASS"]["success"]),
                "p2p_pass": len(report["PASS_TO_PASS"]["success"]),
                "testify_log": log_fp}
    finally:
        ssh(f"sudo docker rm -f {cid} 2>/dev/null; echo done")

# ── outer loop ────────────────────────────────────────────────────────────────

def process(iid):
    inst = TASKS[iid]
    HERE.mkdir(parents=True, exist_ok=True)
    log({"instance":iid,"stage":"start"})

    s = setup(inst)
    if not s: return
    cid, root, applied, tsha = s
    if not applied: teardown(inst, cid); return

    failbase = warm_and_failbase(inst, cid, root)
    box, gate = helpers(inst, cid, root, tsha)
    ssh(f"sudo docker network disconnect bridge {cid} 2>/dev/null; echo done")  # offline

    tag = iid.replace("/","_")
    hgraph = str(HERE/f"r4_hgraph_{tag}.md")
    pathlib.Path(hgraph).write_text(f"# Hypothesis graph: {iid}\n")

    verdict, route, kill_report, handoff = "UNKNOWN", "recon", None, None
    prev_route = None
    for depth in range(MAX_OUTER):
        # RECON — unless audit routed straight back to craft (recon was right)
        if route == "recon" or handoff is None:
            handoff, fixed_point = recon(inst, box, gate, hgraph, kill_report, depth)
            if fixed_point and depth > 0:
                log({"instance":iid,"stage":"halt","msg":"fixed point: re-diagnosis converged"})
                break
        # CRAFT
        craft_out, wants_rediagnose, craft_timed_out = craft(inst, box, gate, hgraph, handoff, kill_report, depth)
        if craft_timed_out:
            # Capture-at-timeout: the agent's in-progress edits are still in the container.
            # Break the loop and let the post-loop capture + testify grade whatever exists,
            # instead of crashing to a 0-byte patch (the DNF class — sympy-19040, etc.).
            verdict = "CRAFT_TIMEOUT"
            log({"instance":iid,"stage":"halt","depth":depth,
                 "msg":f"craft hit CRAFT_CAP={CRAFT_CAP}s — capturing in-progress diff"})
            break
        if wants_rediagnose and depth < MAX_OUTER-1:
            # craft says the hypothesis is wrong — feed its note back to recon next iter
            kill_report = f"craft could not implement the diagnosis:\n{craft_out[-2000:]}"
            route = "recon"; prev_route = None; continue
        # AUDIT
        audit_out, verdict, raw_route = audit(inst, box, gate, hgraph, failbase, depth)
        route = raw_route
        if verdict == "RESOLVED" or route == "none":
            break
        # No-progress escalation: a regression that survived ONE narrow attempt means the
        # approach conflicts with the P2P test — re-diagnosing beats grinding craft (which
        # would just retry the same edit). Allow one narrow, then route recon.
        if route == "craft" and prev_route == "craft":
            log({"instance":iid,"stage":"escalate",
                 "msg":"narrow mode stalled on persistent regression -> route recon (re-diagnose)"})
            route = "recon"
            kill_report = ("NARROW MODE STALLED: a PASS_TO_PASS regression persisted after a "
                           "narrow attempt. The chosen root cause / edit site conflicts with the "
                           "regressed test. Re-diagnose with a DIFFERENT approach.\n" + audit_out[-1800:])
        elif depth < MAX_OUTER-1:
            kill_report = audit_out[-2500:]  # routes recon (re-diagnose) or craft (narrow, first time)
        else:
            log({"instance":iid,"stage":"halt","msg":f"depth budget exhausted at {verdict}"})
        prev_route = raw_route

    # Driver-side final gate: save passing-test output + independently confirm verdict.
    passout, drv_f2p_pass = verify_gate(inst, cid, root, tsha)
    log({"instance":iid,"stage":"verify_gate","agent_verdict":verdict,
         "driver_f2p_pass":drv_f2p_pass,
         "passgate_file":str(HERE/f"r4_passgate_{tag}.txt")})

    patch = capture_patch(inst, cid, root, tsha)
    pf = HERE/f"r5_patch_{tag}.diff"; pf.write_text(patch)

    # THE CONTRACT. Re-grade the captured prediction on a fresh clean container with the
    # official parser. This — not the agent's audit — is the final verdict. Done before
    # teardown so the image is still present.
    att = testify(inst, patch)
    agent_verdict = verdict
    final_resolved = bool(att.get("resolved"))
    divergence = (agent_verdict == "RESOLVED") and not final_resolved
    submittable = final_resolved and att.get("decision") == "decided"
    log({"instance":iid,"stage":"testify","agent_verdict":agent_verdict,
         "testify_decision":att.get("decision"),"testify_resolution":att.get("resolution"),
         "testify_resolved":final_resolved,"gate_divergence_caught":divergence,
         "prediction_sha256":att.get("prediction_sha256"),
         "f2p_failures":att.get("f2p_failures"),"p2p_failures":att.get("p2p_failures")})

    with open(PATCHES,"a") as f:
        f.write(json.dumps({"instance_id":iid,"patch":patch,
                            "prediction_sha256":att.get("prediction_sha256"),
                            "submittable":submittable,"testify":att})+"\n")
    log({"instance":iid,"stage":"done","agent_verdict":agent_verdict,
         "final_resolved":final_resolved,"submittable":submittable,
         "gate_divergence_caught":divergence,
         "patch_bytes":len(patch),"patch_file":str(pf),"hgraph":hgraph})
    teardown(inst, cid)

if __name__ == "__main__":
    for iid in sys.argv[2:]:
        try: process(iid)
        except Exception as e:
            log({"instance":iid,"stage":"ERROR","msg":f"{type(e).__name__}: {str(e)[:200]}"})
    sys.stderr.write("rung5 driver done\n")
