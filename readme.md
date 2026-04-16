# TTS Studio

> OpenAI Text-to-Speech — Single-File Web App

A zero-dependency, single HTML file for converting text to speech via the OpenAI TTS API. Runs entirely in your browser. No server, no install, no build step.

---

## Usage

1. Download `tts-studio.html`
2. Open it in any modern browser (Chrome, Firefox, Safari, Edge)
3. Enter your OpenAI API key
4. Paste your text, pick a voice and model, hit **Konvertieren**

Or host it anywhere static — GitHub Pages, Netlify, a local server. Nothing to configure.

---

## Features

### Chunking Engine
The OpenAI TTS API has a hard limit of 4,096 characters per request. TTS Studio automatically splits longer texts into chunks of up to 4,000 characters, processes them sequentially, and stitches the resulting audio back into a single file.

Splits are made at natural boundaries in priority order: paragraph break → line break → sentence end → word boundary → hard cut (last resort).

### Progress UI
A progress bar and per-chunk status indicators (grey → pulsing yellow → green / red on error) show exactly where a multi-chunk job stands. A cancel button lets you stop after the current chunk completes cleanly.

### Rate Limit Handling
On HTTP 429 (rate limit), the app waits 12 seconds and retries the chunk automatically — once. Any other API error (401, 500, network failure) stops the job immediately with a clear message.

### Live Cost Estimation
As you type, the app calculates an estimated cost based on character count and the selected model's per-million-character price. For chunked jobs it shows cost per chunk and total. Updated on every keystroke and model change.

### Model Info
Each model displays its price, quality rating, and a plain-language description of what it's best suited for.

| Model | Price | Quality | Best for |
|---|---|---|---|
| `tts-1` | $15 / 1M chars | ★★★☆☆ | Drafts, notes, short to medium content |
| `tts-1-hd` | $30 / 1M chars | ★★★★★ | Final productions, audiobooks, published content |
| `gpt-4o-mini-tts` | $15 / 1M chars | ★★★☆☆ | When voice style control via Instructions is needed |

### Voice Instructions
`gpt-4o-mini-tts` supports an `instructions` parameter for controlling speaking style. TTS Studio includes 7 built-in presets:

| Preset | Best for |
|---|---|
| 📚 Scholar | Academic texts, essays, non-fiction |
| 🎙 Narrator | Novels, short stories, fiction |
| 📰 Newsreader | Articles, reports, news copy |
| 🧘 Meditation | Guided exercises, mindfulness scripts |
| ⚙️ Technical | Documentation, tutorials, how-to guides |
| 💬 Conversational | Dialogues, podcasts, informal content |
| 🎭 Dramatic | Poetry, plays, expressive prose |

Instructions are fully editable. Editing away from a preset switches the selector to "Custom" automatically.

### Markdown Stripping
Optional toggle to strip Markdown formatting (headings, bold, italic, links, code blocks, lists) before sending to the API. A live preview shows the first 300 characters of the cleaned text.

### Audio Output
The combined audio plays directly in the browser via a native `<audio>` element and can be downloaded in the selected format.

### Format Notes
Each audio format shows a note on chunk-join compatibility:

- **mp3** — recommended for long texts, chunks join seamlessly
- **aac** — good quality, joins are usually inaudible
- **opus** — smallest file size, joins may be audible
- **flac** — lossless, large files, joins may be audible

### Settings Persistence
All settings (model, voice, speed, format, markdown toggle, preset, instructions) are saved to `localStorage` and restored on next open. The API key is **never** persisted — it lives only in memory for the duration of the session.

---

## Privacy

- Your text and API key are sent only to `api.openai.com`. Nothing else.
- The API key is not stored anywhere (no `localStorage`, no cookies).
- No analytics, no external requests except the Google Fonts import and the OpenAI API call.

---

## Requirements

- A modern browser with `fetch` and `Blob` support (all evergreen browsers)
- An [OpenAI API key](https://platform.openai.com/api-keys) with TTS access

---

## Pricing Reference

Prices shown in the app are sourced from [platform.openai.com/docs/pricing](https://platform.openai.com/docs/pricing). They are hardcoded estimates — verify current pricing before relying on them for billing decisions.


