# Local zero-cost AI gateway (9Router)

Status: **running** at `http://127.0.0.1:20128` (localhost only, not LAN-exposed).
OpenCode v2.2.5 is **verified** to route through it: `GATEWAY_V2_OK` was returned by
`oc/deepseek-v4.1-flash-free`.

## What is installed

| Piece | Where | Cost |
| --- | --- | --- |
| 9Router v0.5.112 (MIT) | global npm package | free |
| Dashboard + OpenAI-compatible API | `http://127.0.0.1:20128` | free |
| Local API key | `gateway/.9router-key` (gitignored, 0600) | free |
| Dashboard password | `gateway/.9router-password` (gitignored) | free |
| Key exposed to OpenCode | user env var `NINE_ROUTER_API_KEY` | free |
| Fallback proxy source | `gateway/auth2api/` (not running) | needs paid Claude/ChatGPT |
| Free-endpoint references | `gateway/awesome-freellm-apis/`, `gateway/awesome-free-ai-coding/` | reference only |

`gateway/` is gitignored: no keys, tokens, or cloned repos enter the JARVIS repository.

## Endpoints

```
OpenAI-compatible base : http://127.0.0.1:20128/v1
Models                 : GET  /v1/models              (public, 862 entries)
Chat completions       : POST /v1/chat/completions    (Bearer key required)
Dashboard              : http://127.0.0.1:20128/dashboard
Health check           : curl -H "Authorization: Bearer $env:NINE_ROUTER_API_KEY" http://127.0.0.1:20128/v1/models
```

## Verified free models

Only the **OpenCode Free lane** (`noAuth: true` in the provider registry) can serve
models with no account. A full pass over the catalog (867 entries) showed every
other namespace returns `404 No active credentials`, because those providers need
an OAuth login or API key. Probing again after connecting nothing does not change
that.

| Model ID | Status | Notes |
| --- | --- | --- |
| `free-auto` | **default** | Combo: deepseek → glm → mimo. Automatic fallback. |
| `oc/deepseek-v4.1-flash-free` | PASS | fastest; ~1.3 s |
| `oc/glm-5.3-flash-free` | PASS | ~1.4 s |
| `oc/mimo-v2.6-flash-free` | PASS | ~2.7 s; needs a normal token budget (a 16-token cap returns empty content) |
| `oc/big-pickle` | PASS (slow) | ~39 s cold start, so it is offered but **not** in the default chain |

Deterministic failures, excluded from config on purpose:

| Model ID | Error |
| --- | --- |
| `oc/jev-1.13-free` | `400 ModelProtocolUnsupported` |
| `oc/muse-spark-1.2-contributor-free` | `400 Model is unavailable` |
| `oc/muse-spark-1.3-contributor-free` | `400 Model is unavailable` |
| `oc/union-alpha` | `400 Model is unavailable` |
| `mmf/mimo-auto` | `400 Unsupported model` — Xiaomi ended the free MiMo channel upstream |
| `kgw/*` | Kilo gateway needs a valid Kilo token; the stored connection was invalid (401) and has been **disabled**, not deleted |

### Fallback is proven, not assumed

`gateway/setup-free.js` created a throwaway combo with a known-bad model first
(`oc/union-alpha` → `oc/deepseek-v4.1-flash-free`). The request still returned
`200 "OK"`, so the chain falls through on failure. The throwaway combo was deleted.

### Free lanes that still need your one-time login

These are `category: "free"` in the registry but are OAuth-based:

| Provider | Prefix | Reality |
| --- | --- | --- |
| Kiro AI | `kr/` | ~50 free credits/month; **deprecated + ToS risk notice** in the registry |
| Gemini CLI | `gc/` | Google account, free tier; safest official free option |
| Devin CLI | — | OAuth |

Connect them at **Dashboard → Providers → Connect**. Each opens one browser tab.
After connecting, `node gateway/probe-free.js` verifies the new models before you
add them anywhere.

## Token refresh, cooldowns, rotation

9Router implements these internally (verified from its README and source, not by us
faking a config file):

- **Auto token refresh** — OAuth access tokens are refreshed before expiry.
- **Quota tracking / cooldowns** — exhausted accounts cool down and requests fall
  through to the next tier/account.
- **Multi-account round-robin** — add the same provider more than once; routing
  rotates and fails over automatically.
- **3-tier fallback** — subscription → cheap → free.

To add your own OAuth accounts (the part that needs a human):

1. Open `http://127.0.0.1:20128/dashboard`.
2. Password: contents of `gateway/.9router-password` (24 random chars generated at
   first start).
3. **Providers → Connect** one of:
   - **OpenCode Free** — no login, already the source of the three models above.
   - **Kiro AI** — ~50 free credits/month (Claude 4.5, GLM-5, MiniMax).
   - **GitHub Copilot / Claude Code / Codex** — only if you already pay for them.
4. To get round-robin: connect the **same** provider twice with different accounts.
5. Create a **Combo** (Dashboard → Combos) to order fallbacks, e.g.
   `oc/deepseek-v4.1-flash-free` → `kr/claude-sonnet-4.5`.

OAuth opens a browser tab once per account. Nothing else needs a tab.

## OpenCode wiring

Both files declare the same V2 provider (the 9router CLI's `connect` writes the
deprecated V1 `provider` shape, so it was not used):

- `~/.config/opencode/opencode.json` — global default.
- `E:\jarvis\opencode.json` — project default, with the existing MCP server,
  OpenRouter free models, and Gravitas skill preserved.

The key is **not** in either file. It comes from `NINE_ROUTER_API_KEY`, which is
set at the user level with `setx`. Restart OpenCode once so the background service
inherits it, then:

```
opencode run --model 9router/oc/deepseek-v4.1-flash-free "hello"
```

## VS Code

- Extensions: Cline, Continue, Python + Pylance, ESLint, Prettier, GitLens,
  Dev Containers, One Dark Pro, Material Icon Theme.
- Theme is set per-workspace in `.vscode/settings.json`.
- Continue (`~/.continue/config.yaml`) lists five 9Router models: `free-auto`
  first, then DeepSeek, GLM, MiMo, Big Pickle.
- OpenCode default is `9router/free-auto` (global and project configs).
- Tasks: `Ctrl+Shift+P → Tasks: Run Task` →
  **9Router: start gateway**, **9Router: health**, **9Router: probe free models**,
  **9Router: open dashboard**.

## Free models as MCP tools

The verified models are exposed to any MCP client through the existing
`jarvis-workshop` stdio server (`jarvis/mcp_server.py`), so OpenCode, Cline and
VS Code see them without a second server. Implementation lives in
`jarvis/free_models.py`; the catalog there is the single source of truth.

| Tool | What it does |
| --- | --- |
| `list_free_models` | Catalog + default chain + live availability. `{"live": true}` (default) queries `/v1/models`. |
| `free_models_health` | Reachability only. `{"probe": true}` sends a real completion to every model and reports pass/fail with latency. |
| `ask_free_model` | One completion. `{"prompt": "...", "model": "free-auto", "system": "...", "max_tokens": 512}`. |

`ask_free_model` returns `{"ok": false, "error": ...}` for a missing key, a bad
HTTP status, or an empty completion — it never raises into the MCP loop, so a
caller gets a readable error instead of a broken connection.

Key resolution order (first win, never logged):

1. `NINE_ROUTER_API_KEY` environment variable.
2. `jarvis.keyvault` entry `nine_router` (`~/.jarvis/keys.json`, file permissions only).
3. `gateway/.9router-key` (or the path in `JARVIS_GATEWAY_KEY_FILE`).

Other settings: `JARVIS_GATEWAY_URL` (default `http://127.0.0.1:20128`).

Verify without a client:

```
$reqs = @('{"jsonrpc":"2.0","id":2,"method":"tools/list"}',
          '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"free_models_health","arguments":{"probe":true}}}')
$reqs | .venv\Scripts\python.exe -m jarvis.mcp_server
```

`opencode mcp list` should show `jarvis-workshop` connected with **15** tools
(12 existing + 3 free-model ones).

## Free cloud compute for heavy tasks

Local hardware is not the only option. `.devcontainer/devcontainer.json` is ready
for GitHub Codespaces / VS Code Dev Containers:

- Codespaces free tier for personal accounts is **60 core-hours/month** (verify the
  current quota on GitHub — it changes).
- It forwards ports `8765` (JARVIS) and `20128` (9Router).
- The gateway itself must run **in the same Codespace**; a cloud Codespace cannot
  reach a gateway on your home PC.

Alternatives, none configured here because each needs your account: Google Colab
(free GPU, notebook-first), Kaggle Notebooks (free GPU hours), Hugging Face Spaces
(free CPU tier). Do not put API keys in any notebook you share.

## Fallback proxy: auth2api

`gateway/auth2api/` is cloned but **not configured or started**. Its own README says
the Claude path needs a Claude Max subscription and the Codex path needs ChatGPT
Plus/Pro. Your accounts are free tier, so it cannot serve models. It is kept only
as a fallback if you later get a paid subscription. Note also that relaying
subscription OAuth sessions through third-party tools is against OpenAI's and
Anthropic's terms; 9Router's own README flags the same for subscription providers.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `401` on `/v1/chat/completions` | Key missing/stale. Re-read `gateway/.9router-key`, re-run `setx NINE_ROUTER_API_KEY <key>`, restart OpenCode. |
| Dashboard: "Too many failed attempts" | The lockout is **in-memory** with progressive steps of 30s, 2m, 10m, 30m after 5 wrong entries. Restart the gateway (`scripts/start-9router.ps1` after stopping the 9router node processes) — the counter resets instantly. |
| Dashboard: "Security risk: no password set" | 9Router only treats a **stored bcrypt hash** as a password; `INITIAL_PASSWORD` alone does not count. `node gateway/set-password.js` logs in with the password in `.9router-password` and persists the hash, so the warning disappears and the same password keeps working. |
| Gateway process dies ~a minute after start | A **tunnel auto-start** (`[Tunnel] enable start`) ran because `tunnelEnabled` was true. It resolved `github.com` through the cloudflare worker, failed, and the router exited. Keep tunnels off: `node gateway/disable-remote.js` sets `tunnelEnabled` and `tailscaleEnabled` to false. Then `scripts/start-9router.ps1`. |
| Gateway down after reboot | `powershell -File scripts/start-9router.ps1` or the VS Code task. |
| Dashboard password lost | Delete the stored hash via Dashboard reset, or re-run with `INITIAL_PASSWORD`. |
| OpenCode says model unavailable | Confirm `http://127.0.0.1:20128/v1/models` lists the model with your key. |
| Port 20128 busy | `9router --port 20129`, then update `baseURL` in both config files. |
