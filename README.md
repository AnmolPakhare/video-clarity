# VideoClarity

VideoClarity is a Python command-line tool that turns YouTube videos into learning notes. It can use spoken captions, or combine captions with actual video frames to capture diagrams, on-screen code, slide text, formulas, and demonstrations that speech alone can miss.

Use it to review educational videos, revisit technical tutorials, or collect notes from several videos. LLM and vision modes explain concepts in everyday language and add clearly labeled teaching examples. Timestamp links and saved frames let you review the source evidence.

## Summary modes

| Mode | What you get | What you need |
| --- | --- | --- |
| Basic (default) | Selected transcript excerpts from across the video, with timestamp links | Internet access for YouTube captions; no LLM API key |
| LLM | A plain-language overview, main ideas, concept explanations, added examples, and takeaways | An OpenAI API key and a compatible model ID |
| Vision | Captions plus visual analysis of sampled frames: diagrams, visible code, slides, and demo states | Video dependencies, an OpenAI API key, and a model that supports image input |

All modes can reuse a saved JSON transcript. Basic mode works fully offline with saved input. LLM mode still contacts OpenAI.
Vision mode can use a YouTube download or a local video file. Its `--extract-only` option saves frames without an API key; this option does not interpret the frames or generate a summary.

## What it does

- Retrieves manual or automatic YouTube captions with timestamps and language preferences.
- **LLM mode:** explains the main ideas in everyday language, defines concepts, and adds clearly labeled teaching examples using OpenAI.
- **Basic mode:** selects representative transcript excerpts from across the video without an API key. This is an extractive preview, not a plain-language rewrite.
- Processes long transcripts in sections and combines notes without silently dropping the end of the video.
- Saves captions before summarization and supports saved JSON input for repeatable, offline tests.
- Handles multiple video links independently; one failure does not cancel the remaining videos.
- **Vision mode:** samples real video frames across the timeline, asks a vision-capable LLM to describe diagrams and read visible code, and combines visual findings with available captions.
- Saves frame images, a timestamp manifest, and visual observations so you can inspect the evidence and any partial results.

## What content does it analyze?

**Basic and LLM modes read transcripts. Vision mode also analyzes actual video frames.** It uses a model that accepts images to read visible text and code, describe diagram nodes and connections, and explain the information the visuals add.

Vision mode samples still images; it does not continuously watch every frame or listen to audio. Brief visuals, animations, scrolling code, and small or blurry text may be missed. Increase the sample density for detailed tutorials. Model prompts require unreadable code/text to be marked instead of guessed, but important details should still be checked against the saved images.

When YouTube captions are unavailable, vision mode continues with visual evidence only and reports that limitation. There is no speech-to-text fallback. Private, restricted, or network-blocked video downloads may fail; you can supply a local copy using `--video-file`.

## Technology stack

The application runs locally in your terminal and writes its results to files.

| Technology | Role in VideoClarity |
| --- | --- |
| **Python 3.10+** | Application language and runtime |
| **youtube-transcript-api** (`>=1.2,<2`) | Retrieves manual or automatically generated YouTube captions and their timestamps |
| **Requests** | Supplies the HTTP session with timeouts for caption retrieval; installed through `youtube-transcript-api` |
| **OpenAI Responses API** (optional) | Generates simple explanations and teaching examples in LLM mode; the user selects the model |
| **yt-dlp** (vision extra) | Downloads a video stream up to 1080p for frame analysis |
| **OpenCV headless / NumPy** (vision extra) | Decodes local video, samples frames, and saves JPEG images without opening a desktop window |
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
4. **Create the notes.** Basic mode selects excerpts across the video. LLM mode summarizes transcript sections. Vision mode also extracts video frames, analyzes images in batches of four, and combines visual observations with spoken notes. Generated examples stay separately labeled.
5. **Export the results.** Save Markdown and JSON summaries, with timestamp links back to the video.

## Project structure

```text
video_clarity/
  cli.py                  Command-line options and batch processing
  core.py                 Caption retrieval, summarization, and exports
  vision.py               Video download, frame extraction, and visual analysis
  __main__.py             Entry point for python -m video_clarity
tests/test_core.py        Automated tests
tests/test_vision.py      Visual-analysis and real video-decoding tests
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

## Capture diagrams, code, and other visual information

Install the video dependencies in your virtual environment:

```sh
python -m pip install -e ".[vision]"
```

Set `OPENAI_API_KEY` and `OPENAI_MODEL` as described below. For vision mode, the selected model must accept image inputs through the Responses API.

```sh
video-clarity "https://www.youtube.com/watch?v=NuWRAiYnjxw" --mode vision --output results/vision
```

This downloads the video, saves sampled frames, analyzes diagrams and visible code, and produces notes that distinguish spoken claims, visual evidence, and generated examples. Readable on-screen code is requested in fenced code blocks; it is never executed. The video download is temporary; extracted JPEGs remain in the output directory.

Additional files in vision mode:

- `VIDEO_ID.frames.json`: sampled timestamps, timing source, frame paths, and any decode failures.
- `VIDEO_ID.frames-*/frame-*.jpg`: the actual images supplied to the model. Each extraction uses a new folder.
- `VIDEO_ID.visual-notes.json`: observations from each image batch. Completed batches remain saved if a later API request fails.
- `VIDEO_ID.summary.md` and `.summary.json`: combined notes and visual-analysis metadata. The Markdown includes links to the saved frames.

```sh
# Inspect extracted frames first, without an API key or LLM charges
video-clarity NuWRAiYnjxw --mode vision --extract-only --output results/frames

# Analyze a local copy of the same video instead of downloading it
video-clarity NuWRAiYnjxw --mode vision --video-file lecture.mp4

# Analyze visuals without retrieving captions
video-clarity NuWRAiYnjxw --mode vision --video-file lecture.mp4 --no-captions

# Use denser samples for slides and code (more images can increase API cost)
video-clarity NuWRAiYnjxw --mode vision --frame-interval 5 --max-frames 80 --max-calls 60
```

By default, the tool targets one frame every 15 seconds, with a cap of 40 frames. If the cap is reached, samples are spread across the entire video rather than stopping early. `--max-frames` accepts 2–200. `--max-download-mb` defaults to 500 MiB. Local files should contain the same footage and timeline as the supplied YouTube ID so timestamp links remain useful.

Vision mode sends sampled images as well as notes/captions to OpenAI. Image analysis incurs API usage charges. `--max-calls` is shared across image analysis and text synthesis for each video. Download failures may require updating yt-dlp or installing a supported JavaScript runtime such as Node.js or Deno; a local MP4 with H.264 video is another supported input.

## Try transcript-only mode

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

The automated tests use synthetic captions, generated video clips, and mocked LLM responses; no network or paid API calls are required. They cover URL validation, chunk coverage, real video decoding, frame timestamps, image request payloads, exports, partial failures, retries, and incomplete LLM output. Install `.[vision]` to run the decoder tests; otherwise those tests are skipped. GitHub Actions installs the vision extra and runs the tests on Python 3.10, 3.12, and 3.13.

The implementation uses the current [`youtube-transcript-api` interface](https://github.com/jdepoix/youtube-transcript-api) and the [OpenAI Responses API](https://developers.openai.com/api/reference/typescript/resources/beta/subresources/responses/methods/create).
Video analysis uses [yt-dlp](https://github.com/yt-dlp/yt-dlp), [OpenCV VideoCapture](https://docs.opencv.org/4.x/d8/dfe/classcv_1_1VideoCapture.html), and [OpenAI image inputs](https://developers.openai.com/api/docs/guides/images-vision).
