# VideoClarity

VideoClarity is a Python command-line tool that turns YouTube captions into learning notes. Give it one or more video links, and it retrieves the spoken transcript, keeps the timestamps, and saves notes you can read or use in another application.

Use it to review educational videos, revisit technical tutorials, or collect notes from several videos. With the optional LLM mode, it explains concepts in everyday language and adds clearly labeled examples to help you understand them.

## Summary modes

| Mode | What you get | What you need |
| --- | --- | --- |
| Basic (default) | Selected transcript excerpts from across the video, with timestamp links | Internet access for YouTube captions; no LLM API key |
| LLM | A plain-language overview, main ideas, concept explanations, added examples, and takeaways | An OpenAI API key and a compatible model ID |

Both modes can reuse a saved JSON transcript. Basic mode works fully offline with saved input. LLM mode still contacts OpenAI.

## What it does

- Retrieves manual or automatic YouTube captions with timestamps and language preferences.
- **LLM mode:** explains the main ideas in everyday language, defines concepts, and adds clearly labeled teaching examples using OpenAI.
- **Basic mode:** selects representative transcript excerpts from across the video without an API key. This is an extractive preview, not a plain-language rewrite.
- Processes long transcripts in sections and combines notes without silently dropping the end of the video.
- Saves captions before summarization and supports saved JSON input for repeatable, offline tests.
- Handles multiple video links independently; one failure does not cancel the remaining videos.

## What content does it analyze?

**The current version reads transcripts only.** It uses YouTube's existing captions or a saved JSON transcript as its source. LLM mode explains that text; it does not watch or listen to the video.

It does **not** analyze video frames, diagrams, on-screen code, or visual-only demonstrations, and does not transcribe audio when captions are unavailable. Private, restricted, uncaptioned, or network-blocked videos may fail with an actionable error. Caption mistakes can carry into the notes.

## Technology stack

The application runs locally in your terminal and writes its results to files.

| Technology | Role in VideoClarity |
| --- | --- |
| **Python 3.10+** | Application language and runtime |
| **youtube-transcript-api** (`>=1.2,<2`) | Retrieves manual or automatically generated YouTube captions and their timestamps |
| **Requests** | Supplies the HTTP session with timeouts for caption retrieval; installed through `youtube-transcript-api` |
| **OpenAI Responses API** (optional) | Generates simple explanations and teaching examples in LLM mode; the user selects the model |
| **Python standard library** | `argparse` handles CLI arguments; `urllib.request` sends OpenAI requests; `dataclasses`, `json`, and `pathlib` manage transcript data and files; `re` and `collections.Counter` support basic excerpt selection |
| **Markdown and JSON** | Store readable notes, structured summary output, and reusable transcripts on disk |
| **pip, venv, and setuptools** | Install dependencies, isolate the Python environment, and package the `video-clarity` command |
| **unittest and unittest.mock** | Test parsing, summarization flow, exports, retries, and errors without paid API calls |
| **GitHub Actions** | Runs the automated tests on Python 3.10, 3.12, and 3.13 |

OpenAI requests use Python's built-in HTTP client. The project does not require the OpenAI Python SDK, LangChain, a database, or a web server.

## How it works

1. **Read the input.** Validate each YouTube URL or video ID and apply the requested caption-language preferences.
2. **Get the transcript.** Retrieve captions from YouTube or load a saved JSON transcript. Clean the text and validate its timestamps.
3. **Save the source.** Write the transcript to disk before summarization so it can be reused if a later API request fails.
4. **Create the notes.** Basic mode selects excerpts across the video. LLM mode splits long transcripts into sections, summarizes each section, combines the notes, and generates beginner-friendly explanations with added examples.
5. **Export the results.** Save Markdown and JSON summaries, with timestamp links back to the video.

## Project structure

```text
video_clarity/
  cli.py                  Command-line options and batch processing
  core.py                 Caption retrieval, summarization, and exports
  __main__.py             Entry point for python -m video_clarity
tests/test_core.py        Automated tests
examples/demo.transcript.json
                          Synthetic transcript for an offline demo
.github/workflows/tests.yml
                          GitHub Actions test configuration
pyproject.toml            Dependencies, packaging, and CLI entry point
TESTING.md                Initial validation record and test limitations
```

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
