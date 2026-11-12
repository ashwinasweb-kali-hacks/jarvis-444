# JARVIS-OS

> A fan-made, local-first AI assistant OS in the spirit of Tony Stark's workshop.

JARVIS-OS replaces the desktop with a voice-first holographic HUD: floating cyan
glass panels, a Three.js quantum-core hologram, WebXR support for standalone
headsets (Meta Quest 3), a local speech pipeline, and a brain that answers from
free cloud models **or** a fully offline GGUF model.

No kernel hacks. It runs on a stock Linux kernel with a kiosk compositor, and the
Python daemon does all the thinking.

---

## What works today

| Area | Status |
|---|---|
| Mic → silence detection → local `faster-whisper` STT | ✅ |
| Spoken acknowledgements (CC BY-NC voice pack) | ✅ |
| HUD shell: panels, telemetry, log, arc-reactor orb | ✅ |
| Three.js workshop scene (bike, car, quantum core, nebula) | ✅ |
| WebXR / Meta Quest 3 (HTTPS + controller input) | ✅ |
| Typed command box (reliable fallback for voice) | ✅ |
| Brain with 5-tier fallback chain | ✅ |
| Phone panel + GlobalFone adapter (OS dialer fallback) | ✅ |
| MCP server (`jarvis-workshop`, 17 tools) | ✅ |
| Bootable ISO + GRUB + DRM compositor | 🧪 experimental |
| Wake word, gestures, installer | ⬜ planned |

Full roadmap: [`docs/JARVIS-OS-STAGES.md`](docs/JARVIS-OS-STAGES.md).

---

## Quick start (Windows)

```powershell
git clone https://github.com/<you>/JARVIS-OS.git
cd JARVIS-OS
py -3 -m venv .venv
.venv\Scripts\python.exe -m ensurepip --upgrade
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m jarvis.daemon
```

Then open <http://127.0.0.1:8765/>.

### Linux / macOS

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python -m jarvis.daemon
```

Optional extras (TTS, audio players, local GGUF): `requirements-optional.txt`.
The default voice out is `edge-tts` (free neural voices, needs internet); set
`JARVIS_TTS_MODEL=piper` (or `pyttsx3`) for fully offline speech.

### Headset (Meta Quest 3)

Standalone browsers only allow WebXR over HTTPS. Use the VR launcher, accept the
self-signed certificate once, then open `https://<your-lan-ip>:8765/`:

```powershell
.\run-jarvis-vr.bat
```

In the headset: **trigger = speak**, **squeeze = reset**, or press 🥽 / `Shift+V`.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Shell — HUD panels, orb, Three.js holograms, WebXR      │  what you see
├──────────────────────────────────────────────────────────┤
│  Daemon — voice → brain → tools → UI commands (port 8765)│  the only "user"
├──────────────────────────────────────────────────────────┤
│  Wayland/DRM compositor in kiosk mode (no desktop)       │
├──────────────────────────────────────────────────────────┤
│  systemd + minimal base distro                           │
├──────────────────────────────────────────────────────────┤
│  Stock Linux kernel                                      │
└──────────────────────────────────────────────────────────┘
```

The shell never decides anything on its own — it obeys UI commands from the
daemon (`open_panel`, `close_panel`, `hologram`, `arrange`, `focus`).

---

## The brain

`jarvis/brain.py` exposes one function: `respond(text, context) -> Reply`
(spoken text + optional structured actions). The provider chain, in order:

1. **9Router / OpenCode CLI** — free models through a local gateway
   (`9router/free-auto` → DeepSeek → GLM → MiMo, plus Groq GPT-OSS 120B).
2. **Direct Gemini API** — `gemini-3.8-flash` (needs `GEMINI_API_KEY`).
3. **OpenJarvis** — optional local agent source tree.
4. **Local GGUF** — `gpt4all` + any chat-tuned `.gguf` (fully offline, no key).
5. **Deterministic stub** — 0-token keyword engine, always answers.

Every tier is optional. With no network at all, tier 4 or 5 still replies, so
JARVIS never dies on a dead API.

### Configuration

All settings are environment-overridable (see `jarvis/config.py`):

| Variable | Default | Meaning |
|---|---|---|
| `JARVIS_MODEL` | `small.en` | Raw faster-whisper size (`tiny`…`large-v3`) |
| `JARVIS_STT_MODEL` | `faster-whisper-small.en` | STT model id from `jarvis/voice_models.py` |
| `JARVIS_TTS_MODEL` | `edge-tts` | TTS engine id (`edge-tts`, `piper`, `kokoro`, `pyttsx3`) |
| `JARVIS_PIPER_VOICE` | `~/.jarvis/voices/<voice>.onnx` | Piper voice file for offline TTS |
| `JARVIS_INPUT_DEVICE` | system default | Mic device index (`--list-devices`) |
| `JARVIS_SILENCE_MS` | `770` | Silence before the recording stops |
| `JARVIS_MAX_RECORD_MS` | `15000` | Hard recording cap |
| `JARVIS_TLS` | `0` | `1` enables HTTPS (required for WebXR) |
| `JARVIS_MODE` | `stub` | `stub` / `local` / `cloud` |
| `JARVIS_GLOBALFONE_URL` | — | GlobalFone gateway endpoint |

API keys live in `~/.jarvis/keys.json` (never in the repo) or in environment
variables. Use the in-app **API Keys** panel or `set_api_key` over MCP.

---

## Phone

`📞 PHONE` opens a floating 12-key dialer. `CALL` sends
`call <number> via globalfone` to the brain, which invokes the `globalfone_call`
tool. If `JARVIS_GLOBALFONE_URL` and a vault token are configured it uses the
GlobalFone gateway; otherwise it falls back to the OS `tel:` handler and says so.

---

## Testing

```powershell
.venv\Scripts\python.exe -m pytest -q
```

The suite is headless: no mic, speakers, GPU or network needed.
Silence detection, hallucination filtering, config overrides, the permission
gate and the daemon dispatch are all covered with mocks.

**63 passed, 3 skipped.**

Manual checks the owner must do (a machine cannot hear or see):

- Speak a short and a long sentence; both should be transcribed.
- Stay silent; no acknowledgement should play.
- Ask "what time is it" and hear a spoken reply.
- Put on the Quest 3 and confirm the HUD renders at a smooth frame rate.

---

## Safety

- Tools are allow-listed with a `safe` / `confirm` / `blocked` risk level.
- Destructive actions (delete, format, shutdown, network changes) ask first.
- Every action is appended to `~/.jarvis/actions.log`.
- LLM output is never passed to a shell; tools take validated arguments.
- No secrets are committed; `gateway/` and key files are gitignored.

---

## Licensing and credits

This is a **non-commercial fan project**. Iron Man, JARVIS and Stark Industries
are Marvel/Disney property; no film assets are shipped here.

| Asset | Licence | Notes |
|---|---|---|
| `assets/openpeon-jarvis/` voice lines | **CC BY-NC 4.0** | Credit retained. Non-commercial use only. Replace before any wider release. |
| Three.js | MIT | Vendored build in `shell/three.min.js`. |
| Intro music | *not shipped* | Point `JARVIS_INTRO_FILE` at your own file. Do not redistribute copyrighted audio. |
| Hologram models | generated in code | No ripped movie models. |

The workshop reference image is **not** included in this repository.

---

## Project docs

- [`docs/JARVIS-OS-STAGES.md`](docs/JARVIS-OS-STAGES.md) — the full roadmap
- [`PROGRESS.md`](PROGRESS.md) — what is done, what is next
- [`DECISIONS.md`](DECISIONS.md) — every non-obvious choice, with reasons
- [`docs/LOCAL-AI-GATEWAY.md`](docs/LOCAL-AI-GATEWAY.md) — gateway runbook
