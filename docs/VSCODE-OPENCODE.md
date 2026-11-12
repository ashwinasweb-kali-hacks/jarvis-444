# OpenCode + VS Code + Gravitas

What is wired, and how to check it. No API keys are stored in this repo.

## 1. JARVIS MCP server

One server, two consumers. It is a stdio MCP server:

```
<Python 3.14> -m jarvis.mcp_server      (working directory: repo root)
```

| Consumer | Config file | Status |
| --- | --- | --- |
| OpenCode | `opencode.json` → `mcp.servers.jarvis-workshop` | already connected (`opencode mcp list`) |
| VS Code (Copilot / local harness) | `.vscode/mcp.json` → `servers.jarvis-workshop` | add-and-trust on first use |

### Verify in VS Code

1. Open the repo in VS Code.
2. Command Palette → **MCP: List Servers** (or **Chat: Open Customizations → MCP Servers**).
3. Start/trust `jarvis-workshop`, then ask the agent to call `system_stats`.

The tools exposed are the same 15 JARVIS tools: `system_stats`, `open_panel`,
`read_file`, `list_dir`, `process_list`, `network_status`, `pc_automation`,
`call`, `globalfone_call`, and friends.

## 2. OpenCode inside VS Code

OpenCode is a CLI/TUI, not a Marketplace extension. It runs in VS Code's
integrated terminal, using this repo's `opencode.json`:

- `Tasks: Run Task` → **OpenCode: start JARVIS session**
- `Tasks: Run Task` → **OpenCode: list MCP servers**
- `Tasks: Run Task` → **OpenCode: connect provider (OAuth / browser)**

The last task runs `opencode auth login`. Choose a provider, pick its OAuth
method, and authorise once in the browser. Tokens are stored by OpenCode, not in
this repo. Do not paste API keys into chat or commit them.

## 3. More models

`opencode.json` declares the free OpenRouter models that were live when this was
written (verified against `https://openrouter.ai/api/v1/models` with
`pricing.prompt == 0`). They appear under `/models` as
`openrouter/<model-id>:free`.

To add more:

- **OAuth providers:** run `opencode auth login` and pick GitHub Copilot,
  ChatGPT, Azure (Entra ID), or Google Vertex. Model lists are fetched after
  sign-in, so no IDs need to be hard-coded.
- **More OpenRouter models:** add entries under
  `providers.openrouter.models` in `opencode.json`.
- **Local models:** start Ollama, LM Studio, or vLLM; discovery is automatic.

## 4. Gravitas

`.opencode/skills/gravitas/SKILL.md` is the upstream MIT skill, vendored and
unmodified (see `NOTICE.md` beside it). It is advertised to the model and loaded
only when a coding task needs it — no always-on token cost.

Trigger it explicitly with `@gravitas`, or let the model pick it for
implementation, debugging, review, or migration work.

## 5. Checks

```powershell
opencode mcp list                     # jarvis-workshop  connected
.venv\Scripts\python.exe -m pytest -q # tests
Invoke-RestMethod http://127.0.0.1:8765/api/health
```
