# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A real-time interview assistant that captures system audio, transcribes speech locally via Whisper, and generates AI responses using either a local Ollama model or the Claude API.

**Platform**: Windows 10/11 only (relies on WASAPI loopback audio capture).

## Setup & Running

```bash
# Setup
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Run with local Ollama (free, default)
python main.py

# Run with Claude API (requires ANTHROPIC_API_KEY in .env)
python main.py --provider claude
```

## Key CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--provider` | `ollama` | AI backend: `ollama` or `claude` |
| `--ollama-model` | `llama3.2` | Ollama model name |
| `--context` | — | User profile text for personalized responses |
| `--language` | `pt` | Audio language for Whisper |
| `--model` | `base` | Whisper model size: `tiny/base/small/medium/large-v3` |
| `--silence` | `1.2` | Seconds of silence to trigger transcription |
| `--threshold` | `0.01` | Audio RMS level threshold for speech detection |

## Architecture

**Flow**: WASAPI audio → silence detection → Whisper transcription → AI (Ollama or Claude) → streamed Rich terminal output

Four modules with clear responsibilities:

- **[audio_capture.py](audio_capture.py)** — `AudioCapture` class. Captures system loopback audio via PyAudioWPatch/WASAPI, detects speech/silence boundaries, invokes `on_audio_ready` callback with audio chunks.
- **[transcriber.py](transcriber.py)** — `Transcriber` class. Runs Whisper locally to convert audio chunks to text. No cloud API involved.
- **[assistant.py](assistant.py)** — Factory + two implementations. `create_assistant()` returns either `ClaudeAssistant` (Anthropic API, streaming) or `OllamaAssistant` (local HTTP, streaming). Both maintain the last 10 messages of conversation history and support a `user_context` string for personalization.
- **[main.py](main.py)** — Orchestrator. Parses CLI args, wires components together, runs the event loop, handles Rich UI output and graceful shutdown.

**Key patterns**: factory (`create_assistant`), callback (`on_audio_ready`), streaming responses.

## Environment

Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY` when using `--provider claude`.

## Debugging Audio

Use `debug_audio.py` to list available audio devices and diagnose WASAPI issues.
