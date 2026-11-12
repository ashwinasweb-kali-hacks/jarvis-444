# Handoff — running this project with OpenClaw, then OpenCode

The project folder already contains everything: `AGENTS.md` (rules + boot
sequence), `docs/JARVIS-OS-STAGES.md` (roadmap), `jarvis/persona.md` (product
persona), `opencode.json`. Work in a **copy under git** so you can undo anything.

```
cd JARVIS-OS-Stages-1-2
git init && git add -A && git commit -m "baseline"
```

## A. OpenClaw (first)
OpenClaw reads `AGENTS.md` from its workspace at the start of each session, and
it does not auto-discover other files — the boot sequence in `AGENTS.md` names them.

Option 1 (simplest): in OpenClaw, tell it the project path and send:
> Read /full/path/to/JARVIS-OS-Stages-1-2/AGENTS.md and follow it. Then start Task 2.1.

Option 2: copy `AGENTS.md` into your OpenClaw workspace (default
`~/.openclaw/workspace/`) and edit the three boot-sequence paths to absolute paths.
Do NOT save `persona.md` as `SOUL.md`: SOUL.md is the *coding agent's* character,
and you don't want your coding agent speaking like JARVIS.

## B. OpenCode (after)
```
cd JARVIS-OS-Stages-1-2
opencode
```
OpenCode loads `AGENTS.md` from the project root, and `opencode.json` adds
`docs/JARVIS-OS-STAGES.md` to its context automatically. First message:
> Follow AGENTS.md. Summarise the project in 6 lines, then start Task 2.1.

## Switching between the two
Both agents share the same files. Before switching, make the outgoing agent
update `PROGRESS.md` and `DECISIONS.md`, then `git commit`. The incoming agent
picks up from those files.

## Not tested
Nothing here was run against a live OpenClaw or OpenCode install. If a path or
config key differs on your version, adjust it and tell the agent to note it in DECISIONS.md.
