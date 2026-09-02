
# 🎙️ AI-TTS-Injector

> **Work in Progress:** An application-agnostic, Windows(currently) overlay that uses local OCR to capture unselectable on-screen text and inject dynamically synthesized speech via local or remote AI Voice APIs.

---

### 💡The Problem & Core Value

Most text-to-speech tools rely on hookable game engines, modding frameworks, or native UI text elements such as just being able to select it in your browser or text editor. **AI-TTS-Injector** takes a completely **application-agnostic approach** by operating strictly as a visual layer on top of your targeted application via direct window capture.

Because it never injects(despite the name) code into or interacts with a program's binary files, it guarantees **near-universal compatibility** across virtually any software—from emulated classic games and indie titles lacking native voice acting, to comics, visual novels, web browsers, and digital readers. If Windows can render it on screen, this tool can read it aloud.

---

### ✨ Features & Current Capabilities

* **Window Locking:** Hooks target application focus so capture regions remain locked to your chosen window.
* **Flexible Snipping & Regions:** Define and save targeted screen regions for dynamic text updates or trigger manual click-to-scan captures.
* **Smart Voice Mapping:** Automatically detects speaker/character names within OCR regions and routes lines to assigned custom voice profiles (`VOICE_MAP`).
* **Multi-Engine Pipeline:** Out-of-the-box support for local CUDA-accelerated models like Kokoro-FastAPI which is what most development has been based around but external OpenAI-style `/v1/audio/speech` models/APIs would basically be plug and play with possibly only minor vendor specific adjustments. Local ChatterboxTTS is still WIP and uncommitted  
* **Queued Audio Playback:** Handles incoming voice lines through an asynchronous audio queue`.
* **Always-on-Top Control Panel:** Compact overlay UI featuring autoplay toggles and interval settings, region selection control still needs to be added, just keybinds for that right now.

---

### ⚙️ How It Works

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ Target Window   │ ───>  │ EasyOCR Engine  │ ───>  │ Character Voice │
│ (Window Capture)│       │ (PyTorch / GPU) │       │ Name Mapping    │
└─────────────────┘       └─────────────────┘       └─────────────────┘
                                                             │
┌─────────────────┐       ┌─────────────────┐                │
│ Local Audio     │ <───  │ Local / Remote  │ <──────────────┘
│ Queue Playback  │       │ AI Voice API      │
└─────────────────┘       └─────────────────┘

```

1. **Window Focus Hook:** Locks onto the focused application using native WinEvent hooks (`pywin32`) which you can set as the target window to be watched and processed using the SET_TARGET_WINDOW keybind.
2. **Region Snipping:** Captures designated visual areas for speaker names and dialogue text, persisting crop coordinates per window title.
3. **OCR Processing:** Runs EasyOCR (CUDA-accelerated via PyTorch) on captured frame regions to extract raw text strings.
4. **Speaker & Voice Mapping:** Matches parsed speaker names against configured voice profiles (`VOICE_MAP`) to assign target parameters.
5. **TTS Dispatch:** Posts clean text payloads to a Kokoro-FastAPI (`/v1/audio/speech`) endpoint or custom remote HTTP API.
6. **Audio Output:** Queues generated audio streams and handles local playback with skip/stop controls via `sounddevice`.

Optional path: Skip the local Kokoro setup and point `KOKORO_URL` at any compatible TTS HTTP API.

---

### ⚠️ Current Project State

This repository represents a working but still very much WIP base. Please keep in mind:

* Currently targeted for **Windows environments**(heavy use of low level win32api).
* Expect rough edges, non-standard reading orders (such as vertical manga text or multi-panel comics) are currently unoptimized, as custom text-flow modes are still in development.

---

## Status

| Area | State                                                                  |
| --- |------------------------------------------------------------------------|
| Window targeting + focus hook | Working                                                                |
| Region snipping (name / text) | Working, persisted per window title                                    |
| EasyOCR + image preprocess | Working, GPU assumed                                                   |
| Kokoro-FastAPI auto-boot | Working on Windows (PowerShell start script)                           |
| Remote / custom AI Voice API | Config-ready (`KOKORO_HOST` / `PORT` / `URL`)                          |
| Playback queue, skip, stop | Working                                                                |
| Live control panel | Partial (interval, autoplay, start/stop)                               |
| Settings GUI & Voice Picker | Not built, currently managed via config files                          |
| Non-Windows | Not supported at the moment (`pywin32`, Win32 event hooks, PowerShell) |
| Extra engines | Kokoro active; Chatterbox branch WIP; Bark/F5 considered               

---

## Requirements

### System

- Windows 10/11
- Python **3.12+**
- NVIDIA GPU recommended (EasyOCR `gpu=True` + Kokoro GPU start script)
- [uv] for dependency install
- A local [Kokoro-FastAPI](https://github.com/remsky/Kokoro-FastAPI) checkout **or** another OpenAI-compatible speech endpoint

### Python stack (from `pyproject.toml`)

- **TTS / audio:** `httpx`, `openai`, `sounddevice`, `soundfile`, `audiosegment`
- **OCR / vision:** `easyocr`, `opencv-python`, `mss`, `numpy`, `torch`, `torchvision`, `torchaudio`
- **Desktop:** `pywin32`, `pygetwindow`, `keyboard`, `mouse`, `pynput`, `customtkinter`, `screeninfo`
- **Misc:** `fasttext-wheel`, `pyenchant`, `websocket-client`, `nest-asyncio`

PyTorch on Windows is pinned to the **cu128** index in `pyproject.toml`. Change that index if your CUDA version differs.

---

## Install

### 1. Clone this repo

```bash
git clone https://github.com/0xNullVOID0/AI-TTS-Injector.git
cd AI-TTS-Injector
```

### 2. Create the env and install deps

```bash
uv sync
```

If `uv sync` pulls the wrong Torch build, install CUDA wheels yourself, then sync the rest:

```bash
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
uv sync
```

EasyOCR will download English detection/recognition weights on first run.

### 3. Install Kokoro-FastAPI (local backend)

This project does **not** vendor Kokoro. It launches an existing install.

1. Clone and set up [Kokoro-FastAPI](https://github.com/remsky/Kokoro-FastAPI) somewhere on disk.
2. Confirm its GPU/CPU start script works on its own (`start-gpu.ps1` is the default this repo looks for).
3. Point this project at that folder in config (next section).

On boot, `kokoro_api.py` checks `KOKORO_HOST:KOKORO_PORT`. If nothing is listening it runs:

```text
powershell.exe -NoProfile -ExecutionPolicy Bypass -File <KOKORO_FOLDER>/<KOKORO_START_SCRIPT>
```

from a cleaned environment so this repo’s `.venv` does not leak into Kokoro’s.

If the port is already open, it just connects.

### 4. Custom TTS API instead of local Kokoro

You can skip auto-boot and talk to any server that accepts a Kokoro / OpenAI-style speech POST.

Set these in `config.json` / `config.local.json`:

```json
"KOKORO_HOST": "http://localhost",
"KOKORO_PORT": 8880,
"KOKORO_URL": "http://localhost:8880/v1/audio/speech"
```

`kokoro_tts.py` sends:

```json
{
  "model": "kokoro",
  "input": "<ocr text>",
  "voice": "<voice id>",
  "lang_code": "a",
  "cleaner": "american_english",
  "response_format": "wav",
  "stream": false
}
```

If your backend uses a different schema, adapt `kokoro_tts.py` and `queue_handler.py` (`requests.post`).

---

## Configure

First run copies `config.json` → `config.local.json`. Edits at runtime go to the local file (gitignored). Keep secrets and machine paths there.

Important keys:

| Key | Meaning |
| --- | --- |
| `DEBUG` | `"True"` keeps the Kokoro process alive after this app exits. `"False"` kills it on shutdown. |
| `KOKORO_FOLDER` | Absolute path to your Kokoro-FastAPI checkout |
| `KOKORO_START_SCRIPT` | Script to launch (default `start-gpu.ps1`) |
| `KOKORO_HOST` / `KOKORO_PORT` / `KOKORO_URL` | Backend address |
| `DEFAULT_VOICE` | Fallback Kokoro voice (`af_bella`, `af_heart`, …) |
| `VOICE_MAP` | `{ "CharacterName": "kokoro_voice_id" }` |
| `TARGET_WINDOW_TITLE` | Last locked window title |
| `BLACKLIST` | Window titles that cannot become the target (e.g. IDE) |
| `INTERVAL` / `AUTOPLAY_INTERVAL` | Seconds between scans / autoplay ticks |
| `AUDIO_FOLDER` | Where generated WAVs are written |
| `KEYBINDS` | Intended binds (not all are wired yet; see hotkeys below) |

Per-window snip regions are stored as `<WINDOW_TITLE>_NAME_COORDS` and `<WINDOW_TITLE>_TEXT_COORDS`.

---

## Run

```bash
uv run python main.py
```

Flow on start:

1. Load config (local override if present).
2. Register the WinEvent focus hook.
3. Bind hotkeys / mouse click.
4. Start the control-panel thread.
5. Boot or attach to the TTS API.
6. Pump Windows messages until you Ctrl+C.

---

## Usage

1. Focus the game / reader window.
2. **Shift + .** — lock that window as the target (skipped if the title is blacklisted).
3. **Shift + [** — snip the **name** region.
4. **Shift + ]** — snip the **text** region.
5. **Shift + Up** — enable OCR processing.
6. Left-click inside the target window — capture, OCR, speak (after a short delay so the line can settle).
7. **Scroll Lock** — toggle autoplay (only if OCR is on).
8. **Shift + Home** — show / hide the control panel (interval sliders, system loop, autoplay).

Playback:

| Key | Action |
| --- | --- |
| Right | Skip current line |
| Down | Stop queue / playback |
| Up | Resume queue |

If name + text regions are not set, the whole window is OCR’d and `DEFAULT_VOICE` is used.

---

## Project layout

```text
main.py               Entry, WinEvent hook, hotkey dispatch
config_handler.py     Singleton config + config.local.json persistence
kokoro_api.py         Detect / boot Kokoro-FastAPI
kokoro_tts.py         Build speech request, push to download queue
ocr.py                EasyOCR, name/text crops, voice lookup
image_processor.py    Pre-OCR image cleanup
text_processor.py     OCR text cleanup
queue_handler.py      Download / play / OCR worker threads
window_handler.py     Capture, focus, process path, blacklist
snipping_selector.py  Overlay region picker
popup_gui.py          Always-on-top control panel
mkb_handler.py        Keyboard + mouse binds
autoplay.py           Autoplay loop
AudioHandler.py       Audio helpers (early)
logger.py / profiler.py / utils.py
assets/sfx            Placeholder SFX dir
```

---

## Debug vs production

- `DEBUG=True`: Kokoro is started in a new process group and is **not** killed when `main.py` exits. Useful while iterating.
- `DEBUG=False`: Kokoro is terminated on exit via `atexit`.
- Debug also writes name/text crop PNGs under `screenshots/` when a non-duplicate line is scanned.

---

## Roadmap

- Full settings GUI (voices, target window, OCR tuning)
- Better OCR post-process (scale, dictionary check, optional LLM fix-up)
- Per-window OCR profiles (text size, vertical layout, text and speech order)
- Speech rate hotkeys
- Optional Bark / Orpheus backends
- Live translation

---
