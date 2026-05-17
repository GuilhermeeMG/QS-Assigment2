# Assignment 2 — Explanation and Next Steps

This document explains what the repository currently contains, how it maps to the
Assignment 2 requirements (LEO-satellite fault tolerance + fault injection with
ucXception), what is still missing, and the concrete next steps to reach a
submittable deliverable by **2026-05-15**.

---

## 1. What the assignment actually asks for

From [QS_Assignment2_v1.pdf](QS_Assignment2_v1.pdf):

| # | Required deliverable | Status in repo |
|---|---|---|
| A | Pick **one** FR from Assignment 0 and justify the choice | Not done — both FRs are still wrapped in the FT layer |
| B | Implement fault tolerance for the highest-priority faults | Partially done — 4 FT prototypes exist (v1..v4) |
| C | Evaluate baseline vs improved using ucXception fault injection | Not started |
| D | Report (<3000 words, PDF) with the 7 bullets listed in the brief | Not started |

Important constraints lifted directly from the brief:

- Target runtime per execution: **10–50 s**, by looping the function thousands/millions of times.
- The function output **must be printed** so silent data corruption (SDC) can be detected by comparing logs.
- ucXception is provided either at `valu3s.dei.uc.pt` (shared) or via the local `docker-compose.yml` (already in the repo).

---

## 2. What we have today

### 2.1 Baseline implementations (Assignment 0)

- [fr1_scheduler.py](fr1_scheduler.py) — FR1: priority-based task scheduler with preemption.
- [fr2_checksum.py](fr2_checksum.py) — FR2: 8-bit XOR checksum validator.

### 2.2 Fault-tolerant prototypes

All four versions are essentially **the same TMR pattern** (Triple Modular Redundancy with a tie-breaker third call) wrapped around the original function. Differences:

| File | Strategy | Hard timeout? | Overhead | Notes |
|---|---|---|---|---|
| [frx_ft_v1.py](frx_ft_v1.py) | 2 calls + 1 tie-breaker | No | Lowest | If all 3 results differ, returns `None` implicitly (silent fail) |
| [frx_ft_v2.py](frx_ft_v2.py) | TMR + per-call timing | No (observability only) | Low | Logs `[watchdog] ...` to stderr above `max_seconds`, but never aborts |
| [frx_ft_v3.py](frx_ft_v3.py) | TMR with **process-per-call** | Yes (process kill) | **Very high** — spawns a process for every call, so for `REPS=1_000_000` it will not finish in minutes |
| [frx_ft_v4.py](frx_ft_v4.py) | TMR with **persistent worker** + IPC timeout | Yes | Medium — one long-lived worker, restart only on timeout |

### 2.3 Other artefacts

- [docker-compose.yml](docker-compose.yml) — ucXception backend + frontend, ready to `docker-compose up -d`.
- [notes.txt](notes.txt) — Portuguese brainstorm: TMR idea, watchdog timer, the SDC concern (target = 0%), ABFT idea (only useful for matrix-shaped problems), preference for sequential re-execution over parallel.
- [README.md](README.md) — short summary of the four versions.

### 2.4 Concrete code-level issues spotted during the read

1. **v1 silently returns `None`** when `result1 != result2 != result3` — this is itself a silent failure and needs an explicit fallback (`raise`, log + safe default, etc.). [frx_ft_v1.py:13-22](frx_ft_v1.py#L13-L22)
2. **No version prints the result** in the main loop — `schedule_tasks_ft(...)` is called but discarded. The assignment explicitly requires printing so SDC runs are detectable from the log diff. [frx_ft_v1.py:34-36](frx_ft_v1.py#L34-L36), [frx_ft_v2.py:90-93](frx_ft_v2.py#L90-L93), [frx_ft_v3.py:131-134](frx_ft_v3.py#L131-L134), [frx_ft_v4.py:177-180](frx_ft_v4.py#L177-L180)
3. **v3 will not hit the 10–50 s target**. With process-per-call and `REPS=1_000_000`, runtime is hours. Either drop `REPS` drastically for v3 or drop v3 from the final candidates.
4. **v2's "watchdog" is observability, not tolerance** — it reports slow calls but never recovers. Either rebrand it (TMR + monitoring, not "watchdog") or upgrade it to actually abort.
5. **`ft_redundance` is duplicated four times** with diverging tweaks. Once a final version is chosen, collapse to a single module.
6. **FR not yet chosen.** Both `schedule_tasks_ft` and `checksum_ft` still exist in every file; the main loop only exercises the scheduler (the checksum line is commented out everywhere). The choice needs a written justification (see §4).

---

## 3. How the deliverables map to what's in the repo

For each report bullet from the brief:

1. **Fault models** — *Missing.* Need a written description (LEO context: SEUs/bit flips, SEFIs, transient hangs, crashes; what propagates into Python: variable corruption, control-flow corruption, hung calls, exceptions, full process crash).
2. **List of FT mechanisms considered (incl. not implemented)** — *Partial.* Implemented: TMR, watchdog timer, process isolation. Not implemented (and need a written justification): N-version programming, ABFT, checkpointing/restart, recovery blocks, ECC at data level.
3. **Brief explanation of applied mechanisms + why** — *Partial in [README.md](README.md).* Needs to be promoted into the report and tied to the fault model.
4. **Why some mechanisms were not implemented** — *Missing.* (e.g., ABFT only fits matrix workloads, not a scheduler; N-version needs an independent re-implementation we don't have time for; checkpointing has no useful state to checkpoint here.)
5. **Fault injection campaigns** — *Not run.* Needs a campaign plan (see §5).
6. **Results / comparison** — *Not produced.* Needs the table (baseline vs FT: SDC %, hang %, crash %, correct %, runtime overhead).
7. **Work division & references** — *Missing.*

---

## 4. Recommended decisions to lock in

### 4.1 Pick FR1 (scheduler) as the target

Rationale to put in the report:

- **More fault surface.** FR1 has loops, mutable state (`ready`, `pending_idx`, `time`, `remaining`), priority comparisons, and several branches — many places where a bit flip can produce an *incorrect-but-not-crashing* result (SDC). FR2's XOR loop is a single accumulator: most bit flips either crash or are caught the next packet.
- **Higher mission impact.** A wrong scheduling decision in orbit can starve a critical task (thermal control, attitude control, downlink window). A wrong checksum verdict mostly causes a retransmission.
- **Better for showing FT value.** TMR shines on functions whose outputs are deterministic and complex enough that masking actually helps. The scheduler returns a list whose order matters, so SDC is visible; the checksum returns a single bool with only two possible values, so randomly-flipped outputs hit the right value 50% of the time — TMR looks artificially good.

(Keep the FR2 wrapper in the codebase as a secondary demo — the reviewer may ask.)

### 4.2 Pick v4 as the final FT version

- v1 has the silent-`None` bug.
- v2 doesn't actually tolerate hangs.
- v3 cannot meet the 10–50 s runtime target with realistic `REPS`.
- v4 keeps TMR + hard timeout + acceptable overhead — the closest to what a real LEO mission would deploy.

Before submission, fix in v4:
- Print the result of every iteration to stdout (so the FI campaign can detect SDC).
- Replace the `result_mismatch_123` silent `None` with an explicit "ERROR" sentinel so the SDC detector can count those distinctly.
- Tune `REPS` and `MAX_SECONDS` so a clean run lands inside the 10–50 s window.

### 4.3 Identify the highest-priority faults

For LEO, prioritise (in this order):
1. **SDC in the scheduler output** — a wrong sequence with no error signal.
2. **Hangs** — function never returns (e.g., corrupted loop counter that never decrements).
3. **Crashes** — process dies mid-pass.

TMR + hard timeout + sentinel-on-mismatch covers all three.

---

## 5. Concrete next steps (in execution order)

Each step lists what to do and what the *output artefact* is. Treat this as a checklist.

### Step 1 — Lock the choice and clean up the code
- [ ] Decide formally on FR1 + v4. Write a 1-paragraph justification (reuse §4.1 / §4.2).
- [ ] In v4: print the result inside the main loop; replace the silent `None` on triple mismatch with `"ERROR_TMR"` (or similar).
- [ ] Add a baseline runner (`frx_baseline.py`) that just calls `schedule_tasks(...)` in a loop and prints the result, with the same `REPS` as v4. This is what ucXception will compare against.
- [ ] Calibrate `REPS` so a clean run is 10–50 s on the test machine.

### Step 2 — Define the fault injection plan
- [ ] Choose the ucXception fault model (register bit flips are the standard for radiation emulation).
- [ ] Choose number of runs per campaign — typical: **golden run** (no faults) + **N=200..500 fault runs** for baseline + same N for the FT version. Document N in the report.
- [ ] Define the failure-mode taxonomy used to classify each run: `Correct`, `SDC`, `Hang`, `Crash`, `Detected-and-recovered`. Save it as a small `failure_modes.md` to keep the classification consistent across team members.

### Step 3 — Run the campaigns
- [ ] `docker-compose up -d` from the repo root to start ucXception locally (avoids the shared-server queue).
- [ ] Upload the **baseline** binary/script and run the campaign; export results.
- [ ] Upload the **v4 FT** version and re-run the same campaign with the same fault profile and same workload.
- [ ] Save raw output logs into a `results/` directory (gitignored or kept — your call) for post-processing.

### Step 4 — Compare and tabulate
- [ ] Diff each FI run's stdout against the golden run to detect SDC.
- [ ] Build a comparison table:

  | Run class | Baseline (n=…) | FT v4 (n=…) |
  |---|---|---|
  | Correct | x % | x % |
  | SDC | x % | x % |
  | Hang | x % | x % |
  | Crash | x % | x % |
  | Detected (TMR mismatch / timeout) | n/a | x % |
  | Mean runtime overhead | 1× | x.x× |

- [ ] Plot or describe: where TMR helps, where it doesn't, what the runtime cost buys you.

### Step 5 — Write the report
- [ ] PDF, < 3000 words. Required sections (1:1 from the brief):
  1. Fault models considered.
  2. List of FT mechanisms considered (TMR, watchdog/timeout, process isolation; **and** the rejected ones: NVP, ABFT, recovery blocks, checkpointing — with reasons).
  3. Brief explanation of applied mechanisms and why.
  4. Justification for non-implemented mechanisms.
  5. Description of FI campaigns (tool, fault model, N, target).
  6. Results + baseline-vs-improved comparison (the table from Step 4).
  7. Work division.
  8. References.
- [ ] Include at least the 3 references from the brief (NASA tutorial, IEEE 994913, NVP chapter) plus any extra reading actually used.

### Step 6 — Submission
- [ ] Zip the source code (final FT version + baseline + any helper scripts) + report PDF.
- [ ] Submit to Inforestudante before **2026-05-15 23:59**.
- [ ] Register a defense slot (week after the deadline). Grading is **individual** at defense — every team member should be able to explain every choice in §4.

---

## 6. Open questions for the team

Before Step 1, agree on:

1. **FR choice** — the recommendation here is FR1, but if the team prefers FR2, the report needs a different justification (and the demo needs to use a payload size that actually exercises the XOR loop, not 0/1-byte inputs).
2. **Final FT version** — v4 is the recommendation; if the team wants to keep multiple versions for the report's "considered" list, decide which is the *implemented and evaluated* one.
3. **Where do we run ucXception** — local Docker (more reproducible, recommended) vs the shared `valu3s.dei.uc.pt` (faster setup, but contended).
4. **Who owns what** — fault-injection driver, results analysis, report writing, defense prep. The report needs an explicit work-division section.
