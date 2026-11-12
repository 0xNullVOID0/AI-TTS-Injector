# 🎙️ AI-TTS-Injector

> **Work in Progress:** An application-agnostic, Windows(currently) overlay that uses local OCR to capture unselectable on-screen text and inject dynamically synthesized speech via local or remote AI Voice APIs.

### 💡The Problem & Core Value

Most text-to-speech tools rely on hookable game engines, modding frameworks, or native UI text elements such as just being able to select it in your browser or text editor. **AI-TTS-Injector** takes a completely **application-agnostic approach** by operating strictly as a visual layer on top of your targeted application via direct window capture.

Because it never injects(despite the name) code into or interacts with a program's binary files, it guarantees **near-universal compatibility** across virtually any software—from emulated classic games and indie titles lacking native voice acting, to comics, visual novels, web browsers, and digital readers. If Windows can render it on screen, this tool can read it aloud.

## Features

- **Target-window tracking:** Hooks target application focus using Windows focus events so capture regions remain locked to your chosen window while avoiding programs on Blacklist.
- **Region selection:** Save separate speaker-name and dialogue regions per window title.
- **OCR:** EasyOCR extracts English text from captured screen regions.
- **Text corrections:** Apply configured word corrections to OCR output.
- **Smart Voice Mapping:** Automatically detects speaker/character names within OCR regions and routes lines to assigned custom voice profiles (`VOICE_MAP`).
- **Multi-Engine Pipeline:** Support for local CUDA-accelerated models like Kokoro-FastAPI or external OpenAI-style `/v1/audio/speech` models/APIs like Fish Audio through OpenRouter  
- **Queued playback:** Buffer generated WAV or PCM files and play them locally; skip, stop, and resume controls are available.
- **Control panel:** A floating panel exposes runtime controls and opens the settings window.

Fish Audio currently uses its configured voice ID; per-speaker voice mapping is used with Kokoro. Autoplay controls are present but the autoplay workflow is not complete. Full-window OCR is experimental; configure name and dialogue regions for the intended workflow.

### ⚙️ How It Works

```text
┌─────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│ Target Window   │ ───>  │ Window Capture   │ ───>  │ EasyOCR Engine   │
│ (selected app)  │       │ (name/text crops)│       │ (PyTorch / GPU)  │
└─────────────────┘       └──────────────────┘       └────────┬─────────┘
                                                               │
┌─────────────────┐       ┌──────────────────┐       ┌────────▼─────────┐
│ AudioPlayer     │ <───  │ Kokoro / Fish    │ <─────│ Text Corrections │
│ (WAV / PCM)     │       │ VoiceEngine      │       │ + Voice Mapping  │
└─────────────────┘       └──────────────────┘       └──────────────────┘
```

1. Lock the active application window as the target.
2. Select the name and dialogue regions; coordinates are saved per window title.
3. Enable OCR and click in the target window after the displayed line is ready.
4. EasyOCR reads the configured regions, then configured text corrections are applied.
5. The speaker name is matched against `VOICE_MAP`; unmatched names use the default Kokoro voice.
6. `VoiceEngine` sends the text and selected voice to Kokoro or Fish Audio.
7. The response is saved as an audio clip and handed to `AudioPlayer` for queued playback.

## Project Status

| Area | State |
| --- | --- |
| Windows target selection and focus tracking | Implemented; Windows only |
| Speaker and dialogue region selection | Implemented; coordinates persist per window title |
| EasyOCR extraction | Integrated; accuracy and reading order need work for different configurations |
| OCR text corrections | Configurable, currently word-based |
| Kokoro-FastAPI backend | Managed Docker Compose startup and health check are implemented |
| Fish Audio backend | OpenRouter client path is implemented; requires API key |
| WAV and PCM playback | Queued playback with skip, stop, and resume controls |
| Control panel | Available; some controls and runtime changes remain incomplete |
| Non-Windows platforms | Not supported |

## Requirements

- Windows 10 or 11.
- Python 3.12 (locked to .12 due to dependency requirements)
- [uv](https://docs.astral.sh/uv/)
- NVIDIA GPU recommended for EasyOCR and required by the supplied GPU Kokoro container configuration.
- Docker Desktop with Docker Compose v2 for the managed and easy Kokoro backend install (can point to local non docker install as well).
- OpenRouter API key for Fish Audio.

Windows PyTorch packages use the CUDA 12.8 package index configured in `pyproject.toml`. If that does not match your GPU driver environment, adjust the PyTorch index configuration before installing.

The main dependency groups are:

- **OCR and capture:** `easyocr`, `opencv-python`, `mss`, `numpy`, `torch`, `torchvision`, and `torchaudio`.
- **Speech and audio:** `openai`, `sounddevice`, `soundfile`, and `audiosegment`.
- **Windows UI and input:** `pywin32`, `pygetwindow`, `keyboard`, `mouse`, `pynput`, `customtkinter`, and `screeninfo`.
- **Service and utilities:** Docker SDK, `httpx`, `websocket-client`, and supporting packages listed in `pyproject.toml`.

## Install

```powershell
git clone https://github.com/0xNullVOID0/AI-TTS-Injector.git
cd AI-TTS-Injector
uv sync
```

EasyOCR downloads its English model files the first time it is initialized. No separate Kokoro checkout or start script is required; the managed Kokoro backend is defined by this project's Compose configuration.

## Run

For the Kokoro backend, start Docker Desktop, then run:

```powershell
uv run python main.py
```

At startup, the app checks whether the configured Kokoro endpoint is healthy. If it is not, the app checks Docker and offers to start the managed Kokoro service. If the service cannot be made available, the app remains open in degraded mode; speech will not work until a backend is reachable. Selecting Fish Audio does not require the managed Kokoro service.

Startup sequence:

1. Load defaults or the local settings file.
2. Register the Windows focus hook and keyboard/mouse bindings.
3. Create the floating control panel.
4. Check the selected speech backend and, when needed, prompt for Docker readiness.
5. Run the Windows message pump and control panel event loop.

## Configuration

Defaults are stored in `config.json`. If `config.local.json` does not exist on first load, it is created from the defaults. Runtime setting changes are written to `config.local.json`; keep API keys and machine-specific paths there rather than in the defaults file.

For Fish Audio, the relevant settings can look like:

```json
{
  "ACTIVE_TTS_API": "FISH_AUDIO",
  "OPENROUTER_API_KEY": "your-key",
  "FISH_MODEL": "fish-audio/drama-3",
  "FISH_VOICE": "your-voice-id"
}
```

| Setting | Purpose |
| --- | --- |
| `ACTIVE_TTS_API` | Select `KOKORO` or `FISH_AUDIO`. |
| `KOKORO_HOST` / `KOKORO_PORT` | Kokoro service address. |
| `DEFAULT_KOKORO_VOICE` | Default voice used by Kokoro. |
| `FISH_MODEL` / `FISH_VOICE` | Fish Audio model and voice ID. |
| `OPENROUTER_API_KEY` | Credential for Fish Audio requests. |
| `VOICE_MAP` | Map speaker names to Kokoro voice IDs. |
| `TARGET_WINDOW_TITLE` | The selected target window. |
| `BLACKLIST` | Title fragments that prevent a window from being targeted. |
| `KEYBINDS` | Optional hotkey overrides. |
| `INTERVAL` / `AUTOPLAY_INTERVAL` | Scan and autoplay timing values. |
| `AUDIO_FOLDER` | Destination for generated audio files. |
| `WINDOW_CAPTURES_FOLDER` | Destination for debug captures. |
| `GUI_*` | Control-panel hotkey, position, size, opacity, and topmost behavior. |

Per-window selection coordinates are stored in `config.local.json` under generated `<WINDOW_TITLE>_NAME_COORDS` and `<WINDOW_TITLE>_TEXT_COORDS` keys.

## Usage

Default hotkeys:

| Key | Action |
| --- | --- |
| `Shift+'` | Set the active window as the target. |
| `Shift+[` | Select the speaker-name region. |
| `Shift+]` | Select the dialogue-text region. |
| `Shift+Up` | Enable OCR processing. |
| `Shift+Down` | Disable OCR processing. |
| `Shift+Home` | Show or hide the control panel. |
| `Shift+T` | Toggle testing mode. |
| `Right` | Skip the currently playing clip. |
| `Down` | Stop queue processing and playback. |
| `Up` | Resume queue processing and playback. |

Typical setup:

1. Start the app and choose a target window with `Shift+'`.
2. Use `Shift+[` and `Shift+]` to select the speaker and dialogue regions.
3. Enable OCR with `Shift+Up`.
4. Left-click inside the active target window to scan the displayed dialogue.
5. Use the playback controls to skip, stop, or resume audio.

Hotkeys can be overridden in the `KEYBINDS` object in the settings GUI or `config.local.json`.

## Limitations and Debugging

- Windows-specific hooks and input libraries mean other platforms are not supported.
- OCR text grouping and reading order can be incorrect, especially with dense pages, multiple columns, or vertical text.
- `DEBUG` enables saving selected name and dialogue crops to `WINDOW_CAPTURES_FOLDER` for inspection.
- Audio output files are written under `AUDIO_FOLDER`.
- If the control panel opens but no speech plays, verify that the selected backend is available and check the app's console output.

## Development and Tests

Run the test suite with:

```powershell
uv run python -m unittest discover -s tests -p "test_*.py"
```

Run Pyright with:

```powershell
uvx pyright
```

Pyright currently checks `audio_player.py` and `voice_engine.py` while type coverage is expanded incrementally.

## Project Layout

```text
main.py               Application entry point and Windows event dispatch
ocr.py                Window-region OCR and speaker lookup
text_processor.py     OCR text corrections
image_processor.py    Pre-OCR image preparation
voice_engine.py       TTS backend client and synthesis
audio_player.py       Audio clip metadata, decoding, and playback
queue_handler.py      Download and OCR queue coordination
docker_manager.py     Docker Compose lifecycle and service status
startup_checks.py     TTS backend readiness checks
config_handler.py     Runtime settings facade
config_store.py       JSON settings persistence
popup_gui.py          Floating control panel
window_handler.py     Window selection, capture, and focus events
snipping_selector.py  Region selection overlay
mkb_handler.py        Keyboard and mouse bindings
autoplay.py           Experimental autoplay loop
```

