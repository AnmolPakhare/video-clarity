import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from video_clarity.cli import main
from video_clarity.core import (ClarityError, OpenAILLM, Segment, Transcript,
    basic_summary, chunk_transcript, clean_segments, llm_summary,
    load_transcript, save_summary, save_transcript, timestamp, video_id)

ID = "NuWRAiYnjxw"


class VideoTests(unittest.TestCase):
    def test_supported_urls(self):
        for value in [ID, f"https://youtu.be/{ID}?t=20", f"https://www.youtube.com/watch?v={ID}&list=abc",
                      f"youtube.com/shorts/{ID}", f"https://m.youtube.com/live/{ID}", f"https://youtube.com/embed/{ID}"]:
            with self.subTest(value=value):
                self.assertEqual(video_id(value), ID)

    def test_rejects_unrelated_hosts_and_non_video_urls(self):
        for value in [f"https://evil.test/watch?v={ID}", f"https://youtube.com.evil.test/watch?v={ID}",
                      "https://youtube.com/playlist?list=123", "https://youtube.com/@test", "bad", f"ftp://youtu.be/{ID}"]:
            with self.subTest(value=value), self.assertRaises(ClarityError):
                video_id(value)

    def test_cleaning_and_validation(self):
        self.assertEqual(clean_segments([{"text": "<i>A &amp; B</i>\n", "start": 1}]), [Segment("A & B", 1)])
        for rows in [[], None, [{}], [{"text": 7, "start": 0}], [{"text": "a", "start": -1}],
                     [{"text": "a", "start": float("nan")}], [{"text": "a", "start": 3}, {"text": "b", "start": 1}]]:
            with self.subTest(rows=rows), self.assertRaises(ClarityError):
                clean_segments(rows)

    def test_chunking_preserves_all_text_and_bounds(self):
        segments = [Segment("a" * 700, 0), Segment("end of the video", 100)]
        chunks = chunk_transcript(segments, 128)
        self.assertTrue(all(len(chunk) <= 128 for chunk in chunks))
        self.assertEqual(sum(chunk.count("a") for chunk in chunks), 700)
        self.assertIn("end of the video", chunks[-1])
        self.assertTrue(all(chunk for chunk in chunks))

    def test_timestamp_hours(self):
        self.assertEqual(timestamp(3661.5), "1:01:01")

    def test_basic_covers_end_and_has_real_links(self):
        transcript = Transcript(ID, "en", "test", [Segment(f"topic{i} " * 70, i * 10) for i in range(32)])
        result = basic_summary(transcript)
        self.assertIn("https://youtu.be/" + ID, result)
        self.assertIn("?t=280", result)
        self.assertIn("does not rewrite", result)

    def test_roundtrip_and_id_mismatch(self):
        transcript = Transcript(ID, "hi", "test", [Segment("Hello", 0), Segment("End", 5)])
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            path = save_transcript(transcript, output)
            loaded = load_transcript(path, ID)
            self.assertEqual(loaded.segments, transcript.segments)
            with self.assertRaises(ClarityError):
                load_transcript(path, "abcdefghijk")
            markdown = save_summary(transcript, "Summary", "basic", output)
            self.assertIn("Summary", markdown.read_text(encoding="utf-8"))
            self.assertEqual(json.loads((output / f"{ID}.summary.json").read_text())["segment_count"], 2)

    def test_llm_processes_every_chunk_and_labels_added_examples(self):
        class FakeLLM:
            def __init__(self):
                self.inputs = []
            def generate(self, instructions, material):
                self.inputs.append((instructions, material))
                return "[0:00] Notes"
        llm = FakeLLM()
        transcript = Transcript(ID, "en", "test", [Segment("first " * 100, 0), Segment("final idea", 99)])
        chunks = chunk_transcript(transcript.segments, 128)
        llm_summary(transcript, llm, chunk_size=128)
        self.assertEqual([material for _, material in llm.inputs[:-1]], chunks)
        self.assertIn("generated illustrations", llm.inputs[-1][0])
        self.assertIn("untrusted", llm.inputs[-1][0])

    @patch("video_clarity.core.urlopen")
    def test_api_contract_and_text_extraction(self, urlopen):
        response = {"status": "completed", "output": [{"type": "reasoning"},
                    {"type": "message", "content": [{"type": "output_text", "text": "Clear notes"}]}]}
        urlopen.return_value.__enter__.return_value = io.StringIO(json.dumps(response))
        self.assertEqual(OpenAILLM("test-key", "test-model").generate("instructions", "transcript"), "Clear notes")
        request = urlopen.call_args.args[0]
        payload = json.loads(request.data)
        self.assertFalse(payload["store"])
        self.assertEqual(payload["model"], "test-model")
        self.assertEqual(payload["input"], "transcript")

    @patch("video_clarity.core.urlopen")
    def test_incomplete_response_rejected(self, urlopen):
        urlopen.return_value.__enter__.return_value = io.StringIO('{"status":"incomplete","output":[]}')
        with self.assertRaisesRegex(ClarityError, "incomplete"):
            OpenAILLM("test", "test").generate("x", "y")

    @patch("video_clarity.core.time.sleep")
    @patch("video_clarity.core.urlopen")
    def test_transient_retries_bounded_and_secret_not_leaked(self, urlopen, sleep):
        urlopen.side_effect = HTTPError("https://api.openai.com", 429, "secret text", {}, None)
        with self.assertRaises(ClarityError) as caught:
            OpenAILLM("secret-key", "test").generate("x", "y")
        self.assertEqual(urlopen.call_count, 3)
        self.assertEqual(sleep.call_count, 2)
        self.assertNotIn("secret", str(caught.exception))

    def test_call_budget_checked_before_network(self):
        llm = OpenAILLM("test", "test", max_calls=1)
        llm.calls = 1
        with patch("video_clarity.core.urlopen") as network, self.assertRaisesRegex(ClarityError, "limit"):
            llm.generate("x", "y")
        network.assert_not_called()

    def test_offline_cli_exports(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "input.json"
            path.write_text(json.dumps([{"text": "A queue processes work in order.", "start": 1}]))
            with patch("sys.stdout", new_callable=io.StringIO), patch("sys.stderr", new_callable=io.StringIO):
                code = main([ID, "--transcript", str(path), "--output", str(root / "out")])
            self.assertEqual(code, 0)
            self.assertEqual(len(list((root / "out").iterdir())), 3)

    @patch("video_clarity.cli.fetch_transcript")
    def test_batch_continues_after_failure(self, fetch):
        fetch.side_effect = [ClarityError("Unavailable"), Transcript("abcdefghijk", "en", "test", [Segment("Hi", 0)])]
        with tempfile.TemporaryDirectory() as folder, patch("sys.stdout", new_callable=io.StringIO), patch("sys.stderr", new_callable=io.StringIO):
            code = main([ID, "abcdefghijk", "--output", folder])
            self.assertEqual(code, 1)
            self.assertTrue((Path(folder) / "abcdefghijk.summary.md").exists())


if __name__ == "__main__":
    unittest.main()
