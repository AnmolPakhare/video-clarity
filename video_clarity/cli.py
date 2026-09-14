"""Command-line interface. Run python -m video_clarity --help."""
import argparse
import os
import sys
from pathlib import Path

from .core import (ClarityError, OpenAILLM, basic_summary, fetch_transcript,
                   llm_summary, load_transcript, save_summary, save_transcript, video_id)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Turn YouTube captions into understandable learning notes.")
    parser.add_argument("videos", nargs="+", help="YouTube video URLs or IDs")
    parser.add_argument("--mode", choices=("basic", "llm"), default="basic")
    parser.add_argument("--model", default=os.environ.get("OPENAI_MODEL"), help="OpenAI model ID for LLM mode")
    parser.add_argument("--languages", nargs="+", default=["en"], help="Preferred caption languages, in order")
    parser.add_argument("--output-language", default="English", help="Language for LLM learning notes")
    parser.add_argument("--transcript", type=Path, help="Saved JSON transcript; accepts exactly one video")
    parser.add_argument("--output", type=Path, default=Path("results"))
    parser.add_argument("--chunk-size", type=int, default=12000)
    parser.add_argument("--max-calls", type=int, default=40, help="Maximum logical LLM calls per video (each may retry twice)")
    args = parser.parse_args(argv)
    if args.transcript and len(args.videos) != 1:
        parser.error("--transcript requires exactly one video")
    if not 128 <= args.chunk_size <= 24000:
        parser.error("--chunk-size must be between 128 and 24000")
    if args.max_calls < 1:
        parser.error("--max-calls must be positive")
    if args.mode == "llm" and (not args.model or not os.environ.get("OPENAI_API_KEY")):
        parser.error("LLM mode requires OPENAI_API_KEY and --model (or OPENAI_MODEL)")
    failures = 0
    for value in args.videos:
        try:
            identifier = video_id(value)
            print(f"Reading captions for {identifier}...", file=sys.stderr)
            transcript = load_transcript(args.transcript, identifier) if args.transcript else fetch_transcript(identifier, args.languages)
            saved = save_transcript(transcript, args.output)
            print(f"Saved {len(transcript.segments)} caption segments: {saved}", file=sys.stderr)
            if args.mode == "llm":
                llm = OpenAILLM(os.environ["OPENAI_API_KEY"], args.model, args.max_calls)
                summary = llm_summary(transcript, llm, args.output_language, args.chunk_size)
            else:
                summary = basic_summary(transcript)
            print(save_summary(transcript, summary, args.mode, args.output,
                               args.model if args.mode == "llm" else None))
        except (ClarityError, OSError) as exc:
            failures += 1
            print(f"Error for {value}: {exc}", file=sys.stderr)
    return 1 if failures else 0
