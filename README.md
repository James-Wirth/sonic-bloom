# Sonic Bloom

A little terminal app that controls Apple Music on macOS via natural language.

```
> Play something whilst I assemble this Ikea shelf

  ⠋ Searching iTunes...

  ? Pick your track:
    › The Final Countdown – Europe
      Lose Yourself – Eminem
      Harder Better Faster Stronger – Daft Punk

  Good choice.

  ╭ ▶ Now Playing ────────────────────────────╮
  │ The Final Countdown — Europe              │
  │ The Final Countdown                       │
  │ vol 75 · shuffle off · repeat off         │
  ╰───────────────────────────────────────────╯
```

## Setup

Requires macOS, Python 3.11+, and Apple Music.

```sh
pip install sonic-bloom
sonic-bloom
```

You'll be prompted to choose a provider (Anthropic, OpenAI, or Ollama) and enter an API key.
