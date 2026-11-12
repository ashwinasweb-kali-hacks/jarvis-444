# JARVIS-OS — Stage-by-Stage Build Brief

**Audience:** the coding agent (OpenClaw + Gemini 3.8 Flash).
**Owner:** the project creator.
**Status:** Stages 1–2 exist (voice in → local transcription → acknowledgement sound). Everything after is planned here.

![Target look](../assets/reference/workshop-reference.png)

*Visual target: the Iron Man workshop. Treat this image as the style reference for the shell (Stage 5) and hologram viewer (Stage 6). It is a movie still, so keep it as a private reference only. Do not ship it inside the OS image.*

---

## 0. Kickoff prompt (paste this first)

```
You are building JARVIS-OS, a custom Linux-kernel OS whose ONLY interface is the
JARVIS voice assistant, styled like Tony Stark's workshop.
Read JARVIS-OS-STAGES.md fully. Then:
1. Summarise the project back in 6 lines. No code yet.
2. Work on the CURRENT STAGE only (see section 3, "Current stage").
3. Finish one task at a time: show the diff, say how to verify, update
   PROGRESS.md and DECISIONS.md, then STOP and wait for "next".
Follow section 2 (Ground rules) exactly. If unsure, ask. Never invent APIs.
```

---

## 1. The vision (plain English)

A computer you **talk to**. There is no desktop to click through. You boot it, a short **JARVIS intro music** plays, and floating cyan **panels** and **holographic wireframes** appear on screen like in the image. You say what you want ("show me the engine model", "open my notes", "what's on the network?") and JARVIS does it, answers in his dry butler voice, and arranges the panels.

What the reference image shows (build toward this):

| In the image | What we build |
|---|---|
| Four floating glass screens with cyan/teal UI on near-black | A panel system: translucent dark cards, thin cyan borders, glow, small data widgets |
| Wireframe motorcycle, cars and suit overlaid in the room | A 3D hologram viewer: cyan wireframe models you can rotate/zoom by voice |
| Person with arms spread, commanding it | Voice first; optional gesture control later (arms spread = "open everything") |
| Curved desk, dark workshop, warm accent lights | Dark theme, amber accent used sparingly for warnings, cyan for normal |

### The key architecture decision

**We do not write a kernel.** "Custom OS with a Linux kernel" means: take the **stock Linux kernel**, put a small base distribution on top, and replace the whole user experience with JARVIS.

```
┌────────────────────────────────────────────────────────┐
│  JARVIS Shell (HUD panels + hologram viewer)           │  ← what you see
├────────────────────────────────────────────────────────┤
│  JARVIS Daemon: voice → brain → tools → UI commands    │  ← the only "user"
├────────────────────────────────────────────────────────┤
│  Wayland compositor in kiosk mode (no normal desktop)  │
├────────────────────────────────────────────────────────┤
│  systemd + minimal base distro (Debian or Arch based)  │
├────────────────────────────────────────────────────────┤
│  Stock Linux kernel                                    │
└────────────────────────────────────────────────────────┘
```

**JARVIS-only does not mean no escape hatch.** A recovery mode with a normal terminal and keyboard login must always exist (Stage 8). If JARVIS breaks, the machine must still be usable.

---

## 2. Ground rules (for the agent)

1. **One stage at a time, one task at a time.** Finish → verify → report → wait for "next".
2. **Smallest working change.** No drive-by rewrites or renames outside the task.
3. **Develop inside a VM** (QEMU/KVM or VirtualBox). Never run experimental boot, partition or image tools on the host disk. Say so loudly before any command that could erase a disk.
4. **Offline-first.** Stages 1–2 use no cloud and no API keys. Later cloud use (e.g. FreeLLMAPI) must sit behind one interface, be **off by default**, and read keys from environment variables only, never from repo files.
5. **Never fabricate.** If you are not sure a library function, flag or package name exists, say so and check docs or `--help`. Do not guess.
6. **Be honest about testing.** You cannot hear audio, see a screen or boot hardware unless a tool lets you. State exactly which checks you ran (unit tests, mocks, QEMU headless) and which need the owner to try by hand. Never write "tested on microphone/speakers" unless it was.
7. **Safety for actions.** JARVIS can run commands on the system. Every tool is allow-listed, logged, and anything destructive (delete, format, shutdown, network changes) requires spoken or typed confirmation.
8. **Log decisions.** One line per non-obvious choice in `DECISIONS.md`, with the reason. Update `PROGRESS.md` after every task.
9. **Keep attribution and licenses.** Never edit `assets/openpeon-jarvis/LICENSE` or remove credits. See section 5.
10. **Short reports.** For each task: *what changed → how to verify → risks.*

---

## 3. Stages

### Current stage: **2 (hardening) → then 3**

Legend: ✅ exists · 🔧 improve now · ⬜ planned

---

### Stage 1 ✅ — Audio spine
Mic → 3 s recording → local `faster-whisper tiny` → text.

---

### Stage 2 🔧 — Voice output + hardening
✅ Random acknowledgement MP3 plays after speech.
🔧 Fix the known problems **before** building on top:

| Task | Do | Done when |
|---|---|---|
| 2.1 Shared core | Create a shared `jarvis/` package (`audio_in.py`, `stt.py`). Stage folders import it. Pass a float32 16 kHz numpy array straight to faster-whisper, with no temp WAV. | One `stt.py` in the repo; no `NamedTemporaryFile` |
| 2.2 Preload model | Load Whisper once at startup, print `Loading… / Ready.` | First utterance is as fast as the second |
| 2.3 Smart recording | Replace the fixed 3 s window with silence detection (RMS first; `webrtcvad`/Silero only if RMS is flaky). Stop after ~0.8 s silence, cap ~15 s, ignore clips under ~0.3 s. | Short and long sentences both captured; silence never calls Whisper |
| 2.4 Noise filter | Drop segments with high `no_speech_prob` / low `avg_logprob`; `language="en"`, `condition_on_previous_text=False`; small blocklist for known hallucinations ("Thank you.", "you"). | Room noise never triggers an acknowledgement |
| 2.5 Config + logging | Dataclass config overridable via env vars (`JARVIS_MODEL`, `JARVIS_INPUT_DEVICE`, `JARVIS_SILENCE_MS`…). Use `logging`. Add `--list-devices`. Friendly error if no mic. | No hard-coded constants in `main.py` |
| 2.6 Safe audio output | `Popen` (non-blocking); don't record while a sound plays; if no player is installed, warn once and return `False`, never crash. Make `manifest.json` paths match the real folder, or read the manifest and log the label. | Removing all players gives one warning and the loop continues |
| 2.7 Tidy deps | Cache the pyttsx3 engine and import it lazily. Split `requirements.txt` / `requirements-optional.txt`. Pin versions. | Fresh venv with core requirements runs both stages |
| 2.8 Tests | `pytest`, no hardware needed: silence detector on synthetic arrays, hallucination filter, `speak_line` with mocked `shutil.which`, config overrides. | `python -m pytest -q` passes headless |
| 2.9 Docs | Fix the README's Windows activation typo (`.venv\Scripts\activate`), update layout, add licensing box. | A stranger can run it from the README |

---

### Stage 3 ⬜ — The brain (JARVIS daemon + persona)
**Goal:** turn text into a decision. Voice no longer just beeps: JARVIS understands and answers.

- Create `jarvis/brain.py` with one function: `respond(text, context) -> Reply`.
  `Reply` = spoken text + optional list of **actions** (structured, e.g. `{"tool": "open_panel", "args": {...}}`).
- Provider is chosen by env var behind that one function: `stub` (default) → `local` (Ollama or similar) → `cloud` (e.g. FreeLLMAPI). Off by default.
- **Persona prompt** in a plain file `jarvis/persona.md`: calm, dry, polite, short answers, "sir". Replies under ~2 sentences unless asked.
- Turn the loop into a **daemon**: a long-running process (`jarvis-daemon`) with an IPC socket (Unix socket or D-Bus) so the shell can later connect to it.
- Speech out: local TTS (Piper or pyttsx3) for real answers; the bundled MP3s stay as quick acknowledgements. Default engine is `edge-tts` (free neural, needs internet), with piper/pyttsx3 as offline fallbacks.
- Short-term memory: last ~10 turns in RAM only.

**Done when:** you speak, hear an acknowledgement sound, then a spoken reply from the stub/local brain; the daemon runs headless and accepts text over its socket for testing.

---

### Stage 4 ⬜ — The tool layer (JARVIS actually controls the machine)
**Goal:** safe, structured actions.

- `jarvis/tools/` with one file per tool, each declaring: name, JSON-schema args, `risk` level (`safe` / `confirm` / `blocked`).
- First tools: open/close app, volume, brightness, time/date, system stats (CPU/RAM/disk), file search in the home folder, read a note, list network status.
- **Permission gate:** `safe` runs immediately; `confirm` makes JARVIS ask ("Shall I proceed, sir?") and wait for a yes; `blocked` is never run.
- **Never** pass LLM output straight to a shell. Tools take validated arguments and call fixed commands.
- Append-only action log (`~/.jarvis/actions.log`).

**Done when:** "what's my CPU usage" and "open the browser" work; "delete my documents" asks for confirmation and is refused if you say no; unit tests cover the gate.

---

### Stage 5 ⬜ — The shell (HUD panels, the workshop look)
**Goal:** replace the desktop with floating JARVIS panels, matching the reference image.

- **Compositor:** a Wayland compositor in kiosk mode (e.g. `cage` or `sway` with a locked config) launching only the JARVIS shell fullscreen.
- **Shell tech (pick one, record it in `DECISIONS.md`):** Qt Quick/QML, or a Chromium/Tauri kiosk showing a web UI. Web UI is faster to iterate on and shares code with Stage 6.
- **Design tokens:** background near-black `#05080c`; primary cyan `#3be8ff`; deep teal `#0b5563`; warning amber `#ffb347`; thin 1 px borders with soft glow; translucent panels; monospace/techno font with a real fallback.
- **Panel system:** draggable/arrangeable cards with a type each: *system stats, notes, media, network, chat/log, 3D viewer.* Layout matches the image: a wide row of 3–4 panels at desk level with space behind for holograms.
- **Voice-driven layout:** daemon sends UI commands such as `open_panel`, `close_panel`, `arrange`, `focus`. The shell never decides on its own, it obeys.
- **Status ring:** a small animated JARVIS orb that shows idle / listening / thinking / speaking.

**Done when:** in a VM, "show system stats" opens a styled panel, "close it" removes it, and the orb changes state while you talk.

---

### Stage 6 ⬜ — Hologram viewer
**Goal:** the glowing wireframe models from the image.

- 3D view inside the shell (Three.js if web UI, or Godot/Qt3D if native).
- Wireframe/edge shader in cyan with soft glow, slow idle rotation, subtle scanline/flicker.
- Voice commands: "show the motorcycle", "rotate", "zoom in", "explode view", "dismiss".
- **Asset pipeline:** models live in `assets/holo/` as `.glb`/`.obj`. Start with **free or self-made** models (a simple bike, car, and suit silhouette). Don't ship ripped movie models.
- Optional: overlay a hologram in the room space behind the panels, like the bike and cars in the image.

**Done when:** "show the motorcycle" brings up a rotating cyan wireframe; "dismiss" removes it; runs at a smooth frame rate in the VM.

---

### Stage 7 ⬜ — Boot experience and intro music
**Goal:** the moment you power it on feels like Stark's workshop.

- Custom boot splash (Plymouth theme): dark screen, cyan ring/logo animation. No scrolling kernel text (keep it available in recovery).
- **Intro music:** plays when the shell starts, not in early boot (Plymouth has no easy audio path). Use a systemd user service ordered after the audio server, or let the shell play it on first frame. Make the file path configurable: `JARVIS_INTRO_FILE`.
- Sequence: splash → intro music → panels fade in → JARVIS says a greeting from the `session.start` pack category.
- **Auto-login** straight into the kiosk shell. No login screen or desktop.
- Add a setting to mute or skip the intro.

**Done when:** a VM boots to the shell with music and greeting, and the whole sequence can be skipped with a config flag.

---

### Stage 8 ⬜ — OS image, installer and recovery
**Goal:** a bootable system anyone can try.

- Build with a reproducible tool: `live-build` (Debian) or `archiso` (Arch). Script it in `os/` (`build.sh`, package list, overlay files). Record the chosen base in `DECISIONS.md`.
- Everything packaged as systemd services: `jarvis-daemon`, `jarvis-shell`, optional intro service.
- **Recovery mode (mandatory):** a boot menu entry that drops to a normal TTY/desktop with keyboard login, plus a way to disable the JARVIS services. Also a documented physical-keyboard shortcut to switch to a TTY.
- Output: a bootable `.iso` and a QEMU launch script. **Test only in a VM.**
- Installer: start by documenting "run as live ISO"; add real disk install last, with big warnings.

**Done when:** `./build.sh` produces an ISO that boots in QEMU straight into JARVIS, and the recovery entry boots into a usable shell.

---

### Stage 9 ⬜ — Always-on, wake word, gestures
- **Wake word** ("Jarvis") with an offline engine such as openWakeWord, so he's always listening but only reacts when called. Visible mic-on indicator and a hard mute key.
- Optional **gesture control** via webcam (e.g. MediaPipe): arms spread = open all panels, swipe = dismiss. Camera is **off by default** and clearly indicated when active.
- Echo handling so JARVIS doesn't hear himself.
- Optional: multiple languages, voice profile of the owner.

---

### Stage 10 ⬜ — Polish, security and release
- Security pass: no network listeners by default; daemon socket restricted to the user; secrets only from env or a locked file.
- Performance pass on low-end hardware (smaller Whisper model options, lighter shaders).
- Accessibility: on-screen text mirror of everything JARVIS says; keyboard fallback.
- Licensing review (section 5), screenshots, demo video, README with install and recovery instructions.

---

## 4. Definition of done (per stage)

- [ ] Works in a VM from a clean checkout following the README.
- [ ] Tests pass without audio, GPU or other special hardware.
- [ ] `PROGRESS.md` and `DECISIONS.md` updated.
- [ ] Recovery path still works (from Stage 8 onward).
- [ ] No secrets in the repo.
- [ ] Anything that couldn't be tested by the agent is listed under "Needs human test".

---

## 5. Licensing and content notes (read before shipping anything)

| Item | Status | What to do |
|---|---|---|
| `openpeon-jarvis` voice lines | **CC BY-NC 4.0.** Non-commercial only, credit required. AI voice inspired by a real actor's JARVIS. | Keep attribution. Personal/fan use only. Before any wider release, replace with self-generated or properly licensed voice lines. |
| **Intro music from a YouTube short** | Almost certainly copyrighted. Downloading it may also break YouTube's terms. | For **personal local use** the owner may keep their own copy outside the repo and point `JARVIS_INTRO_FILE` at it. **Do not commit or distribute it.** The repo ships a royalty-free or self-made placeholder instead. |
| Workshop screenshot, Iron Man / JARVIS / Stark names and styling | Marvel/Disney property. | Reference only. Call the project a fan project, don't use it commercially, don't use ripped film assets in the image. |
| Hologram models | Must be free-licensed or self-made. | Record each model's source and license in `assets/holo/CREDITS.md`. |

---

## 6. Behaviour to preserve from Stages 1–2

- Sample rate **16 000 Hz**, mono, float32.
- STT default: `WhisperModel("small.en", device="cpu", compute_type="int8")`
  (best free accuracy that stays realtime on CPU; `JARVIS_MODEL=tiny` for slow
  machines). Catalog and alternatives live in `jarvis/voice_models.py`.
- Empty transcript → `(No speech detected)`.
- Ctrl-C exits cleanly with `JARVIS stopped.`
- Acknowledgement category: `"task.acknowledge"`; players tried in order `mpg123` → `ffplay` → `afplay`.
- Both stage folders stay separately runnable with `python -m core.main`.

---

## 7. Suggested repo layout (target)

```
JARVIS-OS/
├── jarvis/                 # shared Python package (audio, stt, tts, brain, tools, config)
├── daemon/                 # jarvis-daemon entry point + IPC
├── shell/                  # HUD panels, orb, hologram viewer (UI code)
├── os/                     # image build scripts, systemd units, plymouth theme, overlay files
├── assets/
│   ├── openpeon-jarvis/    # sound pack + license (untouched)
│   ├── holo/               # 3D models + CREDITS.md
│   ├── intro/              # placeholder intro (royalty-free)
│   └── reference/          # style reference images (private)
├── stage-1/  stage-2/ …    # runnable stage snapshots
├── tests/
└── README.md  PROGRESS.md  DECISIONS.md
```
