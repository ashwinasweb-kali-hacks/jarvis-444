# AGENTS.md — JARVIS-OS

JARVIS-OS is a custom Linux-kernel OS whose only interface is the JARVIS voice
assistant (Iron Man workshop look). Python voice loop exists (Stages 1–2).
Everything else is planned in `docs/JARVIS-OS-STAGES.md`.

## Boot sequence (read these, in order, at the start of every session)
1. `docs/JARVIS-OS-STAGES.md` — the roadmap, ground rules, per-stage tasks.
2. `PROGRESS.md` — what is done and what is next.
3. `DECISIONS.md` — choices already made. Do not reverse them silently.

## Current stage
**Stage 2 hardening (tasks 2.1–2.9), then Stage 3.** Work on the current stage only.

## Working rules
- One task at a time. Finish → show diff → say how to verify → update
  `PROGRESS.md` and `DECISIONS.md` → STOP and wait for "next".
- Smallest working change. No drive-by rewrites or renames.
- Never invent library functions or flags. If unsure, say so and check `--help`/docs.
- You cannot hear audio or see the screen. Say exactly what you tested
  (unit tests/mocks) and what the owner must test by hand. Never claim
  "tested on microphone/speakers" unless true.
- Run risky system, boot or disk commands only in a VM, never on the host.
- No API keys in the repo. Cloud/LLM use stays behind one interface, off by default.
- Keep `assets/openpeon-jarvis/LICENSE` and attribution untouched. Do not modify the MP3s.
- Keep both `stage-1` and `stage-2` runnable with `python -m core.main`.
- Reports are short: what changed → how to verify → risks.

## IMPORTANT: `jarvis/persona.md` is a product file, NOT your persona
It defines how the JARVIS *product* speaks to the end user. Do not talk like
JARVIS yourself. Read it only when working on Stage 3 (`jarvis/brain.py`),
where its system prompt (section 9) is loaded by the code.

## Reference only
`assets/reference/workshop-reference.png` — style target for Stage 5/6.
Never copy it into the OS image.
