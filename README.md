# 47 (100% free, local-first, no holograms)

A personal AI assistant: listens (or reads typed input), talks, reasons,
remembers past conversations, monitors your system like a live HUD, takes
actions on your laptop, and shows any generated data — including a labeled
3D visual for building/tool/vehicle/map-path questions — on a live 3D
dashboard.

## Real command-prompt access, admin included, open anything, live data

- **"run command <x>"** / **"execute <x>"** / **"run in the terminal <x>"** runs
  it in your actual OS shell (`cmd.exe` on Windows, `sh` elsewhere) and speaks
  back the output. Add "as administrator" / "as admin" / "with admin rights" /
  "elevated" anywhere in the sentence to run it elevated instead.
  - Windows: elevating opens a hidden elevated PowerShell that runs the
    command and redirects its output to a temp file, which is read back
    once it finishes — so output *is* captured now (a second UAC prompt is
    what you're approving, for that launcher, not the command itself).
  - macOS/Linux: elevating shells out to `sudo`, which will prompt for your
    password on whatever terminal you launched `main.py` from.
  - Either way, elevation goes through the **OS's own** elevation gate — 47
    doesn't hold admin rights itself and can't hand them out silently; that's
    not a limitation of this build, it's how UAC/sudo work everywhere, and
    disabling that gate isn't something this project will help with.
- **The one guardrail kept, on purpose:** 47's speech recognizer transcribes
  continuously in the background (that's how wake-word detection works at
  all), and free recognizers do occasionally mishear background noise as
  words. So a command matching an unmistakably destructive pattern (mass
  delete, disk format/partition, raw disk writes, shutdown/reboot — see the
  list in `shell.py`) asks for one spoken/typed **"confirm"** before it runs.
  Everything else, admin included, runs immediately with no friction.
- **"open terminal" / "open cmd" / "open powershell" / "open file explorer"**
  now open real OS tools, not just websites — `open_app_or_site` in
  `actions.py` special-cases these.
- **"fetch <url>"** now works on *either* brain (the old MCP fetch tool only
  worked when `ASSISTANT_BRAIN=groq`): it does a real HTTP GET, strips tags,
  and asks whichever brain you're running to summarize it.
- **"weather in <city>"** — live current conditions via Open-Meteo (free, no
  API key, two calls: geocode the place, then fetch current weather).
- **Where I drew a line, and why:** "real-time tracking" of a *person* —
  their phone, their car, their location without their knowledge — is
  surveillance/stalking territory, and that's a hard no regardless of whose
  laptop this runs on; it's not the same thing as fetching live *public* data
  (a web page, the weather, search results), which is fully built in above.
  If what you actually meant was live data feeds (stocks, sports scores, news,
  a specific site's live numbers), say so and I'll wire up the specific free
  API for it — same pattern as `get_weather()`.

## Tuned for i5 (11th gen) + Iris Xe, no discrete GPU

- **3D dashboard: nothing was downgraded.** The whole scene is a handful of
  low-poly boxes/spheres/tubes with no shadows and no post-processing —
  Iris Xe renders that at a locked 60fps with headroom to spare. The only
  actual laptop-specific change is capping `devicePixelRatio` (a 1440p+
  laptop panel reporting 2-3x scaling makes the iGPU render several times
  the pixels for zero visible difference at this detail level), plus an
  adaptive step in `dashboard.html` that *only* drops a notch if frame time
  genuinely goes bad and climbs right back once it recovers. Default is
  always full quality.
- **The local LLM is the part that actually strains this CPU.** Iris Xe
  can't accelerate LLM inference at all (no CUDA/ROCm path) — a "local"
  model runs purely on the 4 CPU cores, and the old default (`llama3`, 8B)
  means multi-second replies and every fan spinning up. Two ways to get
  top-tier answers without punishing the laptop:
  1. **Recommended: Groq (cloud, free, no card).** `main.py` now auto-picks
     Groq the moment `GROQ_API_KEY` is set — inference runs on Groq's
     hardware, not yours, so your CPU/iGPU stay idle and you get a smarter
     70B model *and* zero local load. This is the "don't compromise" option.
  2. **Fully offline:** default local model is now `llama3.2:3b` instead of
     the 8B `llama3` — a 4-core i5 can actually hold a real-time
     conversation with it. Ollama's thread count is also pinned
     (`OLLAMA_NUM_THREAD`, default = cores-2) so it doesn't starve the
     voice loop and Flask. Swap models any time:
     ```
     ollama pull llama3.2:3b   # good default
     ollama pull phi3.5        # also solid, similar size
     export OLLAMA_MODEL=phi3.5
     ```
     **Advanced, optional, not the default:** Intel's `ipex-llm` project can
     accelerate Ollama using the Iris Xe iGPU itself via SYCL, which is
     genuinely faster than CPU-only. Flagging honestly: on GitHub the repo
     currently shows *"Intel will not provide or guarantee development of
     or support for this project… this project has been identified as
     having known security issues."* I'm not defaulting to it or walking
     you through install for that reason — if you still want it, look up
     the current `ipex-llm` Ollama quickstart yourself and weigh that
     warning first.
- Everything else (speech recognition, the free online voice, on-demand
  screenshot/camera vision, MCP tool calls) is already network- or
  OS-level work, not local compute — no changes needed there for this CPU.

## What changed in this pass

**Bug fixes**
- `dashboard.html` is now under `templates/` — Flask's `render_template()`
  couldn't find it at the old location, so the dashboard route would have
  thrown a `TemplateNotFound` error on first run.
- `vision.py`: the Groq vision model name (`llama-3.2-90b-vision-preview`)
  was retired; updated to the current model, `meta-llama/llama-4-scout-17b-16e-instruct`.
- `main.py` reminder parsing: `"remind me in 10 minutes to call the bank"`
  used to store the *entire raw sentence* as the task description when the
  literal phrase `"remind me to"` wasn't present. Fixed with a proper prefix
  stripper in `time_parse.py`.
- `main.py` task-completion parsing: `"i completed the report"` matched
  against `"completed the report"` instead of `"the report"` (an off-by-one
  in the old `split()` logic), so it would almost never find the task. Fixed.
- `voice_loop()` used to crash the whole process on start if no working
  microphone was found (common in a VM, a headless box, or a laptop with a
  driver issue). It now logs a warning and disables voice input instead,
  leaving the typed-input channel fully usable.

**New: type-to-command / data entry**
You're not limited to voice anymore. The dashboard now has a text box at
the bottom — type a command or a fact and hit Enter/Send. It goes through
the *exact same* pipeline as a spoken `"hi 47"` command (no wake word
needed there, since typing into the box already means you're addressing
it): 47 can act on it, and it speaks the reply back out loud as well as
showing it on screen.

**New: 3D visuals for objects, not just charts**
Ask a "what does X look like" / building / tool / vehicle / map or path
question (spoken or typed) and 47 pushes a labeled 3D representation to
the dashboard — see `visual3d.py` and the `renderBuilding` /
`renderTool` / `renderVehicle` / `renderMapPath` functions in
`dashboard.html`. **Read this limit honestly:** there's no image-to-3D or
3D-asset-library pipeline in this free, local stack, so it can't generate
a literal, accurate 3D replica of any specific object you name. What it
does is recognize the *category* of thing you're asking about and build a
parametric, labeled 3D scene for that category — a boxed tower with lit
windows for "building", an abstract handle-and-head shape for "tool", a
ground plane with a glowing path and pins for "map/route/path", and so on.
It's a quick spatial visual, not a rendering engine.

**About "the real JARVIS voice"**
That's Paul Bettany's copyrighted voice performance tied to a real actor's
likeness — no legitimate free or paid tool can clone that. `tts_jarvis.py`
instead uses a free Microsoft Edge neural voice, `en-GB-RyanNeural`
(calm, deep-ish British male) by default, which is the closest legal
option in spirit, with a fully offline `pyttsx3` fallback if you have no
internet. Swap the online voice any time:
```
export JARVIS_VOICE="en-GB-ThomasNeural"
```

## 1. Install the free brain (choose one)

**Option A — fully offline (Ollama):**
- Download: https://ollama.com
- Run once: `ollama pull llama3`
- Runs automatically at http://localhost:11434, zero cost, zero account

**Option B — free cloud, sharper answers (Groq):**
- Sign up free, no credit card: https://console.groq.com
- Create an API key
- Set environment variables before running:
  ```
  export GROQ_API_KEY=gsk_...
  export ASSISTANT_BRAIN=groq
  ```
- This runs Llama 3.3 70B (open-source) on Groq's free tier — much sharper
  and faster than a small local model, and still $0.
- Free tier limits (subject to change, check console.groq.com): roughly
  30 requests/minute, ~14,400/day — plenty for personal use.

## 2. Install Python dependencies
```
pip install -r requirements.txt
```
On Windows you may also need: `pip install pipwin && pipwin install pyaudio`
For volume control on Windows: `pip install pycaw comtypes`
For screen/camera vision on Windows: `pip install pygetwindow`

## 3. Run it
```
python main.py
```
This starts:
- The voice loop (say something after "47 online") — or just type in the
  dashboard's text box if you have no mic
- An ambient monitoring thread (CPU/RAM/battery/network) streamed live
  to the dashboard, with proactive spoken alerts (e.g. low battery)
- A local dashboard, opened automatically at startup — the URL includes a
  required access token (see the security note below); a bare
  `http://localhost:5000` with no token will be refused.
- Persistent memory in `memory_47.db` — conversations and facts
  survive restarts

## Wake word (voice only — typing never needs it)
47 stays quiet on voice input unless addressed. Say **"hi 47"** followed by
your request — e.g. "hi 47, what's on my screen" or "hi 47, what does a
wrench look like". Everything else it overhears is ignored except quiet
passive task-detection (see below). Typed input in the dashboard box is
always treated as addressed — no wake word needed there. Change the phrase:
```
export WAKE_WORD="your phrase"
```
Note: this is software-side keyword matching on top of the free speech
recognizer, not a dedicated low-power wake-word engine (like Porcupine) —
it still transcribes everything, it just won't *act* unless it hears the
wake word.

## MCP tools (real multi-step actions, free)
47 can use [MCP](https://modelcontextprotocol.io) servers as tools, and the
brain (Groq/Llama 3.3 70B) decides when to call them and can chain multiple
calls in one answer. Shipped by default: the official **fetch** server, so
you can say (or type) things like:
- "hi 47, fetch this page and summarize it: https://example.com"
- "hi 47, look up what's on this site and tell me the pricing"

Setup:
```
pip install mcp mcp-server-fetch
```
First run auto-creates `mcp_servers.json`. Add more free MCP servers by
adding entries there — see https://github.com/modelcontextprotocol/servers
for options (filesystem access, git, sqlite, GitHub, Slack, and more).
Each entry just needs `name`, `command`, and `args` for how to launch it.
Note: tool-calling currently only runs on the Groq brain path (requires
`ASSISTANT_BRAIN=groq`); the offline Ollama path doesn't use tools yet.

## What works out of the box
- Conversation (voice or typed), with memory of past turns and remembered facts
- "remember that my project deadline is friday" — stores a fact 47
  will use in future conversations
- "open youtube" / "open github" / "open notepad" — opens sites/apps
- "find file <name>" — searches your filesystem, shows matches on dashboard
- "set volume to 40" — system volume control
- "search google for <topic>" — free DuckDuckGo search, shown as 3D bars
- "fetch <url> and summarize it" — real MCP tool call, works multi-step
  (needs `pip install mcp mcp-server-fetch` and `ASSISTANT_BRAIN=groq`)
- "what's on my screen" — takes one screenshot, describes it (needs GROQ_API_KEY)
- "what do you see" — takes one webcam photo, describes it (same as above)
- "what does a building/tool/car/map/route look like" — 3D category visual
  on the dashboard (see the honest limits above)
- Live system vitals HUD (top-right of dashboard) — CPU/RAM/disk/battery,
  always on, not just reactive to questions
- Active-window awareness — always knows which app/window is focused
  (no images captured for this, just the window title) and shows it live
  on the dashboard
- **Task memory** — say "remind me to call the bank in 20 minutes" and
  47 speaks the reminder when it's due; say "what are my tasks" to
  hear/see them all; say "done with the report" to mark one complete.
  It also **auto-detects tasks passively** from normal speech — saying
  "I need to finish the slides" logs a task even without a direct command.
- Any conversational reply also pushed to the dashboard text panel

## Privacy note on the vision features
- Active-window tracking runs continuously but only ever sees window
  *titles*, never pixels — it's the always-on layer. Under Wayland (or
  without `xdotool` installed), it disables itself and says so once in
  the console rather than failing silently forever.
- Screen and camera capture are **on-demand only** — one screenshot or
  one photo, taken exactly when you ask, then discarded after being sent
  to the vision model. Nothing runs a hidden background camera or screen
  recorder. If you want to disable window tracking too, just remove the
  `start_window_tracking` thread in `main.py`.

## Privacy note on voice input
- The default speech recognizer (`sr.recognize_google`) is a **free cloud
  API**, not something that runs on your machine. Every time `listen()`
  captures audio — which is continuous while the voice loop is running,
  not just after the wake word — that clip is sent to Google's servers
  for transcription. The wake word itself is only detected by inspecting
  the transcription that comes back; there's no offline/on-device
  wake-word gate in the free path, so ambient audio (background
  conversation, TV, etc.) is being sent for transcription too, not just
  things said *to* 47.
- If that's not acceptable for your situation, either:
  - set `VOICE_RECOGNIZER=sphinx` (after `pip install pocketsphinx`) for a
    fully offline recognizer — noticeably less accurate, but nothing
    leaves your machine, or
  - don't run the voice loop at all and use the dashboard's typed-input
    box instead, which never touches a microphone or a cloud STT API.

## Security note on the dashboard and shell access
The dashboard can run arbitrary shell commands on request — including
elevated ones — so it is gated behind a random access token generated on
first run (`.47_dashboard_token`, next to `main.py`) and binds to
`127.0.0.1` (this machine only) by default:
- The console prints the dashboard's full URL, token included, at
  startup, and opens it automatically. Bookmark *that* URL — a plain
  `http://localhost:5000` with no `?token=...` will be refused (403).
- Treat `.47_dashboard_token` like a password. Delete it (and restart) to
  rotate it if you think it's been seen by someone else.
- Set `DASHBOARD_HOST=0.0.0.0` only if you deliberately want this
  reachable from other devices on your LAN — it prints a loud warning
  when you do, because at that point the token is the *only* thing
  standing between a stranger on your network and a shell.
- The destructive-command confirmation ("say 'confirm' to run it anyway")
  is a safety net for **misheard/mistyped commands**, not a permission
  system — it's a fixed pattern list and can be phrased around on
  purpose. Don't rely on it to stop anyone who already has access to the
  dashboard; the token above is what controls *that*.

## What still needs a bit more setup (still free)
- **Email**: needs a one-time Gmail API OAuth setup (see actions.py)
- **Texts/calls**: no fully free option exists (Twilio has a trial credit,
  then a small per-message cost) — skip unless you need it

## Running the tests
A stdlib-only (`unittest`, no `pytest` needed) test suite lives in
`tests/` and covers the destructive-command patterns, per-session
confirmation isolation, fact dedup/capping, task cleanup, retry/backoff,
3D category classification, and the dashboard token gate:
```
python -m unittest discover -s tests -v
```

## Extending it
- `actions.py` — add new commands (more file ops, app-specific controls)
- `ambient.py` — add more monitored signals or proactive alert rules
- `memory.py` — add smarter fact-extraction (currently a simple keyword
  rule with basic normalization/capping — see `normalize_key()`)
- `visual3d.py` — add more object categories and matching dashboard scenes
- `tts_jarvis.py` — swap the voice, tune rate/pitch
- `main.py` `handle_command()` — add new phrase-routing rules
- `net_utils.py` — shared retry/backoff for any new outbound HTTP call
- `dashboard.html` — add new visualization types. Send data from Python:
  ```python
  push_to_dashboard("bars", {"labels": [...], "values": [...]})
  push_to_dashboard("network", {"nodes": [{"id": "A"}, {"id": "B"}]})
  push_to_dashboard("vitals", {"cpu_percent": ..., "ram_percent": ...})
  push_to_dashboard("object3d", {"type": "building", "label": "HQ Tower"})
  ```

## Honest limits vs. movie JARVIS
- Even with Groq's free Llama 3.3 70B, this is very good but still not
  Claude/GPT-4-class reasoning — free open-source models trade some
  intelligence for being free.
- The voice is a free, legal, JARVIS-*styled* neural voice — not the
  actual copyrighted movie character voice.
- The 3D visuals are labeled, category-level, parametric scenes — not
  literal, accurate 3D reconstructions of the specific thing you named.
- No true ambient sensing beyond your laptop (no cameras, city data,
  suit telemetry — obviously). The system-vitals HUD is the closest
  free analog: it's always watching *something* rather than only
  reacting when spoken to.
