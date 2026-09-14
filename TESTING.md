# Validation record

Validated locally on Windows with Python 3.12.7 and youtube-transcript-api 1.2.4.

## Passed

- `python -m pip install -e .`: editable package install and console entry point.
- `python -m unittest discover -s tests -v`: 14 automated tests passed.
- `video-clarity --help`: installed CLI runs.
- Offline CLI against `examples/demo.transcript.json`: writes transcript JSON, summary JSON, and Markdown.
- Live CLI against `https://www.youtube.com/watch?v=NuWRAiYnjxw`: retrieved 218 English automatic-caption segments and wrote all three outputs. This verifies the Python caption extraction and basic mode on the requested video.

## Not yet verified

- Live OpenAI summarization: no OPENAI_API_KEY is configured in the execution environment. The HTTP request contract, response parsing, prompt construction, chunk coverage, retries, and call limit were tested with mocks. This does not verify the quality of a real model-generated summary.
- GitHub Actions matrix: workflow is included; remote execution requires publishing the repository.
- Independent comparison with the visible Chrome transcript panel: Chrome was unavailable in the agent's browser tools. The live caption test above used the actual Python tool requested by the user.

The full retrieved transcript and basic output are local test artifacts outside the source repository. They are not fixtures in the automated test suite.
