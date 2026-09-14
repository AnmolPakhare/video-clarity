"""Command-line interface. Run python -m video_clarity --help."""
import argparse
import os
import math
import sys
from pathlib import Path

from .core import (ClarityError, OpenAILLM, Transcript, basic_summary, fetch_transcript,
                   llm_summary, load_transcript, save_summary, save_transcript, video_id)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Turn YouTube captions and video frames into understandable learning notes.")
    parser.add_argument("videos", nargs="+", help="YouTube video URLs or IDs")
    parser.add_argument("--mode", choices=("basic", "llm", "vision"), default="basic")
    parser.add_argument("--model", default=os.environ.get("OPENAI_MODEL"), help="OpenAI model ID for LLM mode")
    parser.add_argument("--languages", nargs="+", default=["en"], help="Preferred caption languages, in order")
    parser.add_argument("--output-language", default="English", help="Language for LLM learning notes")
    parser.add_argument("--transcript", type=Path, help="Saved JSON transcript; accepts exactly one video")
    parser.add_argument("--output", type=Path, default=Path("results"))
    parser.add_argument("--chunk-size", type=int, default=12000)
    parser.add_argument("--max-calls", type=int, default=40, help="Maximum logical LLM calls per video (each may retry twice)")
    parser.add_argument("--video-file", type=Path, help="Local video instead of a download (vision mode, one video ID/URL)")
    parser.add_argument("--extract-only", action="store_true", help="Save video frames without calling an LLM (vision mode)")
    parser.add_argument("--no-captions", action="store_true", help="Analyze frames without fetching captions (vision mode)")
    parser.add_argument("--frame-interval", type=float, default=15, help="Desired seconds between frames (default: 15)")
    parser.add_argument("--max-frames", type=int, default=40, help="Frame cap; samples span the whole video (2-200)")
    parser.add_argument("--max-download-mb", type=int, default=500, help="Maximum video download size in MiB")
    args = parser.parse_args(argv)
    if args.transcript and len(args.videos) != 1:
        parser.error("--transcript requires exactly one video")
    if args.video_file and len(args.videos) != 1:
        parser.error("--video-file requires exactly one video ID/URL for source links")
    if (args.video_file or args.extract_only or args.no_captions) and args.mode != "vision":
        parser.error("--video-file, --extract-only, and --no-captions require --mode vision")
    if args.transcript and args.no_captions:
        parser.error("--transcript and --no-captions cannot be combined")
    if not math.isfinite(args.frame_interval) or args.frame_interval <= 0:
        parser.error("--frame-interval must be finite and positive")
    if not 2 <= args.max_frames <= 200 or args.max_download_mb < 1:
        parser.error("--max-frames must be 2-200 and --max-download-mb must be positive")
    if not 128 <= args.chunk_size <= 24000:
        parser.error("--chunk-size must be between 128 and 24000")
    if args.max_calls < 1:
        parser.error("--max-calls must be positive")
    if args.mode in ("llm", "vision") and not args.extract_only and (not args.model or not os.environ.get("OPENAI_API_KEY")):
        parser.error("LLM/vision mode requires OPENAI_API_KEY and --model (or OPENAI_MODEL)")
    failures = 0
    for value in args.videos:
        try:
            identifier = video_id(value)
            print(f"Reading captions for {identifier}...", file=sys.stderr)
            if args.transcript:
                transcript = load_transcript(args.transcript, identifier)
            elif args.no_captions:
                transcript = Transcript(identifier, "none", "No captions requested", [])
            else:
                try:
                    transcript = fetch_transcript(identifier, args.languages)
                except ClarityError as exc:
                    if args.mode != "vision":
                        raise
                    print(f"Caption retrieval failed; continuing with visual evidence only: {exc}", file=sys.stderr)
                    transcript = Transcript(identifier, "none", "Captions unavailable", [])
            if transcript.segments:
                saved = save_transcript(transcript, args.output)
                print(f"Saved {len(transcript.segments)} caption segments: {saved}", file=sys.stderr)
            visual_metadata = None
            if args.mode == "vision":
                from .vision import analyze_video, prepare_frames
                print("Extracting video frames...", file=sys.stderr)
                manifest, manifest_path = prepare_frames(identifier, args.output, args.video_file,
                                                        args.frame_interval, args.max_frames, args.max_download_mb)
                print(f"Saved {len(manifest['frames'])} frames: {manifest_path}", file=sys.stderr)
                if args.extract_only:
                    print(f"{manifest_path} (extraction only; no visual interpretation or summary generated)")
                    continue
                llm = OpenAILLM(os.environ["OPENAI_API_KEY"], args.model, args.max_calls)
                summary, visual_metadata = analyze_video(transcript, manifest, args.output, llm,
                                                        args.output_language, args.chunk_size)
            elif args.mode == "llm":
                llm = OpenAILLM(os.environ["OPENAI_API_KEY"], args.model, args.max_calls)
                summary = llm_summary(transcript, llm, args.output_language, args.chunk_size)
            else:
                summary = basic_summary(transcript)
            print(save_summary(transcript, summary, args.mode, args.output,
                               args.model if args.mode in ("llm", "vision") else None, visual_metadata))
        except (ClarityError, OSError) as exc:
            failures += 1
            print(f"Error for {value}: {exc}", file=sys.stderr)
    return 1 if failures else 0
