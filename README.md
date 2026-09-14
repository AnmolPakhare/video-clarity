# VideoClarity

Turn YouTube captions into timestamped learning notes. Give it one or more video URLs, then read the results as Markdown or use the JSON in another application.

## What it does

- Retrieves manual or automatic YouTube captions with timestamps and language preferences.
- **LLM mode:** explains the main ideas in everyday language, defines concepts, and adds clearly labeled teaching examples using OpenAI.
- **Basic mode:** selects representative transcript excerpts from across the video without an API key. This is an extractive preview, not a plain-language rewrite.
- Processes long transcripts in sections and combines notes without silently dropping the end of the video.
- Saves captions before summarization and supports saved JSON input for repeatable, offline tests.
- Handles multiple video links independently; one failure does not cancel the remaining videos.

This version reads spoken captions. It does **not** analyze video frames, diagrams, or visual-only demonstrations, and does not transcribe audio when captions are unavailable. Private, restricted, uncaptioned, or network-blocked videos may fail with an actionable error. Caption mistakes can carry into the notes.

## Install

Requires Python 3.10 or newer. From this repository folder:

```sh
python -m venv .venv
```

Activate on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

On macOS/Linux:

```sh
source .venv/bin/activate
```

Then install:

```sh
python -m pip install -e .
```

## Try the supplied video

```sh
video-clarity "https://www.youtube.com/watch?v=NuWRAiYnjxw"
```

This runs basic mode without an LLM key. Results are written to `results/`:

- `NuWRAiYnjxw.transcript.json`: the retrieved transcript and metadata.
- `NuWRAiYnjxw.summary.md`: readable notes with video links.
- `NuWRAiYnjxw.summary.json`: mode, model, source metadata, and Markdown content.

Rerunning the same video into the same output directory replaces those files. Use a different `--output` directory to preserve a previous run.

## Plain-language explanations and examples

Set your API key in the terminal locally. Do not paste it into chat or commit it. Choose an OpenAI model available to your API account that supports the Responses API; model selection is explicit.

Windows PowerShell:

```powershell
$env:OPENAI_API_KEY = 'YOUR_API_KEY'
$env:OPENAI_MODEL = 'YOUR_MODEL_ID'
video-clarity 'https://www.youtube.com/watch?v=NuWRAiYnjxw' --mode llm
```

macOS/Linux:

```sh
export OPENAI_API_KEY='YOUR_API_KEY'
export OPENAI_MODEL='YOUR_MODEL_ID'
video-clarity 'https://www.youtube.com/watch?v=NuWRAiYnjxw' --mode llm
```

The resulting notes contain an overview, main ideas, concepts explained, added examples, and takeaways. Prompts require the model to distinguish the speaker's claims from generated teaching examples. This is a prompting safeguard, not a factuality guarantee; verify important claims against the timestamped source.

LLM mode sends caption text and intermediate notes to OpenAI and can incur API charges. Requests set `store: false`. The default limit is 40 logical requests per video; each request may retry twice on rate limits or transient server errors. This is a request limit, not a currency budget. The tool does not read `.env` files automatically.

## More examples

```sh
# Multiple videos
video-clarity 'VIDEO_URL_1' 'VIDEO_URL_2' --output results/batch

# Caption preference: Hindi first, English second
video-clarity 'https://www.youtube.com/watch?v=NuWRAiYnjxw' --languages hi en

# Explain in Hindi (requires LLM configuration)
video-clarity 'https://www.youtube.com/watch?v=NuWRAiYnjxw' --mode llm --output-language Hindi

# Reuse retrieved captions without contacting YouTube
video-clarity NuWRAiYnjxw --transcript results/NuWRAiYnjxw.transcript.json --mode llm

# Fully offline demo using a synthetic transcript
video-clarity abcdefghijk --transcript examples/demo.transcript.json --output results/demo

# Alternative invocation
python -m video_clarity --help
```

`--transcript` accepts one video and either an array of `{ "text": "...", "start": 0, "duration": 2 }` rows or an object with `video_id`, `language`, and `segments`. Timestamps are seconds. Input must be in chronological order.

Exit code `0` means every video succeeded; `1` means one or more failed; `2` indicates invalid CLI arguments.

## Development and tests

```sh
python -m unittest discover -s tests -v
```

The automated tests use synthetic captions and mocked LLM responses; no network or paid API calls are required. They cover hostile/non-video URLs, malformed captions, chunk coverage, exports, batch failures, API request format, retries, and incomplete LLM output. GitHub Actions runs the same tests on Python 3.10, 3.12, and 3.13.

The implementation uses the current [`youtube-transcript-api` interface](https://github.com/jdepoix/youtube-transcript-api) and the [OpenAI Responses API](https://developers.openai.com/api/reference/typescript/resources/beta/subresources/responses/methods/create).
