import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_clarity.cli import main
from video_clarity.core import ClarityError, OpenAILLM, Segment, Transcript, save_summary
from video_clarity.vision import analyze_video, extract_frames, reduce_visual_notes, sample_times

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None


class FakeVisionLLM:
    model = "fake-vision-model"

    def __init__(self):
        self.image_batches = []
        self.text_inputs = []

    def generate_images(self, instructions, material, images):
        self.image_batches.append((instructions, material, images))
        return "[0:00] Visual evidence: Client -> Queue -> Worker. Code: print('hello')."

    def generate(self, instructions, material):
        self.text_inputs.append((instructions, material))
        return "Combined learning notes with visual evidence."


class VisionTests(unittest.TestCase):
    def test_frame_budget_covers_whole_long_video(self):
        times = sample_times(7200, 15, 10)
        self.assertEqual(len(times), 10)
        self.assertEqual(times[0], 0)
        self.assertGreater(times[-1], 7199)
        self.assertEqual(times, sorted(set(times)))

    def test_invalid_sampling_configuration(self):
        for duration, interval, limit in [(0, 15, 40), (float("nan"), 15, 40), (10, 0, 40), (10, float("inf"), 40), (10, 15, 1)]:
            with self.subTest(values=(duration, interval, limit)), self.assertRaises(ClarityError):
                sample_times(duration, interval, limit)

    @patch("video_clarity.core.urlopen")
    def test_vision_api_sends_frame_bytes_with_timestamp_and_high_detail(self, request):
        response = {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": "Diagram"}]}]}
        request.return_value.__enter__.return_value = io.StringIO(json.dumps(response))
        with tempfile.TemporaryDirectory() as folder:
            frame = Path(folder) / "frame.jpg"
            frame.write_bytes(b"jpeg-test-bytes")
            llm = OpenAILLM("test", "vision-test")
            self.assertEqual(llm.generate_images("inspect", "frame", [(65.2, frame)]), "Diagram")
        payload = json.loads(request.call_args.args[0].data)
        content = payload["input"][0]["content"]
        self.assertIn("1:05", content[1]["text"])
        self.assertEqual(content[2]["type"], "input_image")
        self.assertEqual(content[2]["detail"], "high")
        self.assertEqual(content[2]["image_url"], "data:image/jpeg;base64,anBlZy10ZXN0LWJ5dGVz")
        self.assertFalse(payload["store"])
        self.assertEqual(llm.calls, 1)

    def test_batches_all_frames_and_combines_both_sources(self):
        frames = [{"timestamp": index * 15, "file": f"frame-{index}.jpg"} for index in range(9)]
        manifest = {"frames": frames, "sampling_notice": "Samples may miss brief visuals.", "skipped_timestamps": []}
        transcript = Transcript("abcdefghijk", "en", "fixture", [Segment("This is a queue.", 0)])
        llm = FakeVisionLLM()
        with tempfile.TemporaryDirectory() as folder:
            summary, metadata = analyze_video(transcript, manifest, Path(folder), llm)
            report = json.loads((Path(folder) / "abcdefghijk.visual-notes.json").read_text())
        self.assertEqual([len(batch[2]) for batch in llm.image_batches], [4, 4, 1])
        self.assertEqual(report["status"], "visual_observations_complete")
        self.assertEqual(metadata["frame_count"], 9)
        self.assertTrue(metadata["captions_available"])
        self.assertIn("?t=120", summary)
        self.assertIn("[View frame](frame-8.jpg)", summary)
        material = json.loads(llm.text_inputs[-1][1])
        self.assertIn("Client -> Queue -> Worker", material["visual_observations"])
        self.assertIn("caption_notes", material)
        self.assertIn("untrusted", llm.image_batches[0][0])
        self.assertIn("[unreadable]", llm.image_batches[0][0])

    def test_visual_only_does_not_invent_spoken_input(self):
        manifest = {"frames": [{"timestamp": 0, "file": "frame.jpg"}], "sampling_notice": "Sampled.", "skipped_timestamps": []}
        llm = FakeVisionLLM()
        with tempfile.TemporaryDirectory() as folder:
            _, metadata = analyze_video(Transcript("abcdefghijk", "none", "none", []), manifest, Path(folder), llm)
        self.assertFalse(metadata["captions_available"])
        self.assertEqual(len(llm.text_inputs), 1)
        self.assertIn("No captions available", llm.text_inputs[0][1])

    def test_partial_observations_survive_api_failure(self):
        class FailingLLM(FakeVisionLLM):
            def generate_images(self, *args):
                if self.image_batches:
                    raise ClarityError("API unavailable")
                return super().generate_images(*args)
        manifest = {"frames": [{"timestamp": i, "file": f"{i}.jpg"} for i in range(5)]}
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ClarityError, "API unavailable"):
                analyze_video(Transcript("abcdefghijk", "none", "none", []), manifest, Path(folder), FailingLLM())
            report = json.loads((Path(folder) / "abcdefghijk.visual-notes.json").read_text())
        self.assertEqual(len(report["batches"]), 1)
        self.assertEqual(report["status"], "in_progress")

    def test_visual_reduction_preserves_tail_and_bounds_requests(self):
        llm = FakeVisionLLM()
        result = reduce_visual_notes(["A" * 25000, "TAIL OBSERVATION"], llm)
        self.assertTrue(all(len(material) <= 12002 for _, material in llm.text_inputs))
        self.assertIn("TAIL OBSERVATION", llm.text_inputs[-1][1])
        self.assertLess(len(result), 20000)

    def test_vision_export_reports_actual_sources(self):
        transcript = Transcript("abcdefghijk", "none", "Captions unavailable", [])
        with tempfile.TemporaryDirectory() as folder:
            path = save_summary(transcript, "Visual notes", "vision", Path(folder), "vision-test", {"frame_count": 2})
            text = path.read_text()
            data = json.loads((Path(folder) / "abcdefghijk.summary.json").read_text())
        self.assertIn("sampled video frames", text)
        self.assertNotIn("Visual-only information is not included", text)
        self.assertEqual(data["visual_analysis"]["frame_count"], 2)

    def test_cli_rejects_incompatible_options(self):
        for options in [["--extract-only"], ["--mode", "vision", "--no-captions", "--transcript", "x.json"],
                        ["--mode", "vision", "--extract-only", "--frame-interval", "nan"]]:
            with self.subTest(options=options), patch("sys.stderr", new_callable=io.StringIO), self.assertRaises(SystemExit) as caught:
                main(["abcdefghijk"] + options)
            self.assertEqual(caught.exception.code, 2)


@unittest.skipIf(cv2 is None, "Install .[vision] to run real video extraction tests")
class VideoExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.clip = self.root / "diagram-and-code.avi"
        writer = cv2.VideoWriter(str(self.clip), cv2.VideoWriter_fourcc(*"MJPG"), 5, (640, 360))
        self.assertTrue(writer.isOpened())
        try:
            for index in range(30):
                image = np.zeros((360, 640, 3), dtype=np.uint8)
                image[:] = (245, 245, 245)
                if index < 15:
                    cv2.putText(image, "Client -> Queue -> Worker", (30, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
                else:
                    cv2.putText(image, "print('hello')", (30, 120), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2)
                writer.write(image)
        finally:
            writer.release()

    def tearDown(self):
        self.temp.cleanup()

    def test_real_decoder_extracts_distinct_beginning_and_end(self):
        manifest, path = extract_frames(self.clip, self.root / "out", "abcdefghijk", 1, 4)
        self.assertEqual(len(manifest["frames"]), 4)
        self.assertGreater(manifest["frames"][-1]["timestamp"], 5)
        images = [cv2.imdecode(np.frombuffer((path.parent / frame["file"]).read_bytes(), np.uint8), cv2.IMREAD_COLOR) for frame in manifest["frames"]]
        self.assertTrue(all(image.shape == (360, 640, 3) for image in images))
        self.assertGreater(np.mean(cv2.absdiff(images[0], images[-1])), 1)
        self.assertEqual(manifest["skipped_timestamps"], [])

    def test_extract_only_cli_works_without_key_or_captions(self):
        output = self.root / "cli"
        with patch.dict("os.environ", {}, clear=True), patch("sys.stdout", new_callable=io.StringIO), patch("sys.stderr", new_callable=io.StringIO), patch("video_clarity.cli.fetch_transcript") as fetch:
            code = main(["abcdefghijk", "--mode", "vision", "--extract-only", "--no-captions",
                         "--video-file", str(self.clip), "--output", str(output), "--max-frames", "3"])
        self.assertEqual(code, 0)
        fetch.assert_not_called()
        self.assertTrue((output / "abcdefghijk.frames.json").exists())
        self.assertFalse((output / "abcdefghijk.summary.md").exists())

    def test_relative_output_directory(self):
        output = Path(os.path.relpath(self.root / "relative-output", Path.cwd()))
        manifest, path = extract_frames(self.clip, output, "abcdefghijk", 2, 3)
        self.assertTrue(path.is_file())
        self.assertTrue(all((output / frame["file"]).is_file() for frame in manifest["frames"]))

    def test_rejects_invalid_video(self):
        path = self.root / "invalid.mp4"
        path.write_bytes(b"not a video")
        with self.assertRaisesRegex(ClarityError, "could not open"):
            extract_frames(path, self.root / "out", "abcdefghijk")


if __name__ == "__main__":
    unittest.main()
