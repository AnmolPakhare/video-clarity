# Validation record

## Version 0.2.0: video-frame analysis

Validated on Windows with Python 3.12.7, youtube-transcript-api 1.2.4, yt-dlp 2026.8.19, and OpenCV headless 4.14.0.94.

- **27 automated tests passed**, including all original transcript tests and new frame-analysis tests.
- Generated a real video containing a diagram and code, decoded it with OpenCV, and verified that beginning/end samples preserve distinct visual content.
- Verified relative output directories, caption-free extraction without an API key, image payload construction, all-frame batching, partial-result persistence, and source-aware summary exports.
- Downloaded the supplied video `NuWRAiYnjxw` and extracted **37 JPEG frames**, from 0.000 to 538.967 seconds, with no failed decodes. The downloaded stream reports a duration of 539.233 seconds. Its 218 caption segments were reused from the earlier test.
- Inspected a saved 1920×1080 frame and confirmed that slide text was readable.
- Vision requests and final synthesis were tested with mocked model responses. **Live interpretation by an OpenAI vision model has not been tested because no API key is configured.** Extraction success does not establish model accuracy on diagrams or code.

Reproduce frame extraction without a model key:

```sh
python -m pip install -e ".[vision]"
video-clarity NuWRAiYnjxw --mode vision --extract-only --output results/frames
python -m unittest discover -s tests -v
```

## Version 0.1.0: initial transcript implementation

Validated locally on Windows with Python 3.12.7 and youtube-transcript-api 1.2.4.

## Passed

- `python -m pip install -e .`: editable package install and console entry point.
- `python -m unittest discover -s tests -v`: 14 automated tests passed.
- `video-clarity --help`: installed CLI runs.
- Offline CLI against `examples/demo.transcript.json`: writes transcript JSON, summary JSON, and Markdown.
- Live CLI against `https://www.youtube.com/watch?v=NuWRAiYnjxw`: retrieved 218 English automatic-caption segments and wrote all three outputs. This verifies the Python caption extraction and basic mode on the requested video.

## Not yet verified

- Live OpenAI summarization: no OPENAI_API_KEY is configured in the execution environment. The HTTP request contract, response parsing, prompt construction, chunk coverage, retries, and call limit were tested with mocks. This does not verify the quality of a real model-generated summary.
- The initial GitHub Actions matrix subsequently passed on Python 3.10, 3.12, and 3.13: [run 34882591387](https://github.com/AnmolPakhare/video-clarity/actions/runs/34882591387).
- Independent comparison with the visible Chrome transcript panel: Chrome was unavailable in the agent's browser tools. The live caption test above used the actual Python tool requested by the user.

The full retrieved transcript and basic output are local test artifacts outside the source repository. They are not fixtures in the automated test suite.
