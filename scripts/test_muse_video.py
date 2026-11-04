#!/usr/bin/env python3
"""Offline regression checks: python -m unittest discover -s scripts -p test_muse_video.py."""

import base64
import contextlib
import io
import itertools
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import muse_video as muse
import video_duration as duration
from shared_client import AimaxhugError


SOURCE = "https://media.example.com/source.mp4"
OUTPUT = "https://media.example.com/generated.mp4"
IMAGE = "https://media.example.com/image.jpg"


class MuseTests(unittest.TestCase):
    def cli(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = muse.main(list(args))
        return code, json.loads(stdout.getvalue()), stderr.getvalue()

    def body(self, **overrides):
        values = dict(model=muse.MODEL, prompt="提示词", aspect_ratio="16:9", seconds=5,
                      mute_voice=False, camera_motion=None, negative_prompt=None,
                      input_reference=None, last_frame=None, images=None, video_url=None)
        values.update(overrides)
        return muse.build_body(SimpleNamespace(**values))

    def test_default_request_is_offline_and_bool_is_not_string(self):
        with patch.object(muse, "AimaxhugClient") as client, patch.object(muse, "probe_video_duration") as probe:
            code, result, _ = self.cli("run", "--prompt", "提示词", "--dry-run", "--json")
        self.assertEqual(code, 0)
        self.assertFalse(result["submitted"])
        self.assertEqual(result["request_preview"], {"model": "muse-video-pro", "prompt": "提示词",
                         "aspect_ratio": "16:9", "seconds": 5, "mute_voice": False})
        client.assert_not_called()
        probe.assert_not_called()

    def test_all_parameters_keep_api_types_and_names(self):
        raw = base64.b64encode(b"example image bytes").decode("ascii")
        code, result, _ = self.cli("run", "--prompt", "人物说话", "--seconds", "10",
            "--aspect_ratio", "3:4", "--camera_motion", "tracking_shot", "--negative_prompt", "模糊",
            "--input_reference", IMAGE, "--last_frame", IMAGE,
            "--images", IMAGE, raw, "data:image/png;base64," + raw, IMAGE,
            "--mute_voice", "true", "--dry-run", "--json")
        self.assertEqual(code, 0)
        body = result["request_preview"]
        self.assertEqual(body["aspect_ratio"], "3:4")
        self.assertEqual(body["camera_motion"], "tracking_shot")
        self.assertEqual(body["negative_prompt"], "模糊")
        self.assertIsInstance(body["input_reference"], str)
        self.assertIsInstance(body["last_frame"], str)
        self.assertEqual(len(body["images"]), 4)
        self.assertIs(body["mute_voice"], True)
        self.assertEqual(body["seconds"], 10)
        self.assertNotIn("duration", body)
        self.assertNotIn("ratio", body)

    def test_boolean_cli_forms(self):
        for flags, expected in (([], False), (["--mute-voice"], True),
                                (["--mute-voice", "true"], True), (["--mute-voice", "false"], False)):
            with self.subTest(flags=flags):
                code, result, _ = self.cli("run", "--prompt", "口型表演", *flags, "--dry-run", "--json")
                self.assertEqual(code, 0)
                self.assertIs(result["request_preview"]["mute_voice"], expected)

    def test_all_seconds_and_ratios_without_reference(self):
        for seconds in muse.SECONDS:
            for ratio in muse.RATIOS:
                with self.subTest(seconds=seconds, ratio=ratio):
                    body = self.body(seconds=seconds, aspect_ratio=ratio)
                    self.assertEqual(body["seconds"], seconds)
                    self.assertEqual(body["aspect_ratio"], ratio)
                    checks = muse.preflight(body)
                    self.assertEqual(bool(checks["warnings"]), seconds > 40)

    def test_invalid_prompt_image_count_and_media(self):
        invalid = ({"prompt": "  "}, {"images": [IMAGE] * 5}, {"input_reference": "local.png"},
                   {"last_frame": "data:image/png;base64,YQ=="}, {"images": ["a file.png"]},
                   {"images": ["data:text/plain;base64,YQ=="]}, {"video_url": "local.mp4"},
                   {"seconds": 15})
        for values in invalid:
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.body(**values)

    def test_short_generation_with_reference_rejected_before_probe_or_client(self):
        for seconds in (5, 8, 10):
            with self.subTest(seconds=seconds), patch.object(muse, "probe_video_duration") as probe, \
                    patch.object(muse, "AimaxhugClient") as client:
                code, result, _ = self.cli("run", "--prompt", "参考视频", "--seconds", str(seconds),
                    "--video-url", SOURCE, "--json")
                self.assertEqual(code, 1)
                self.assertIn("20", result["message"])
                probe.assert_not_called()
                client.assert_not_called()

    def test_reference_headroom_advice_uses_full_precision(self):
        for seconds in (20, 30, 40, 50, 60):
            limit = seconds - 2
            for source_seconds, expected in ((1, True), (limit, True), (limit + 0.0001, False), (seconds - 0.0001, False)):
                with self.subTest(seconds=seconds, source_seconds=source_seconds):
                    result = duration.reference_timing(source_seconds, seconds)
                    self.assertEqual(result["within_recommendation"], expected)
                    self.assertEqual(result["recommended_max_source_seconds"], limit)
                    self.assertAlmostEqual(result["available_continuation_seconds"], seconds - source_seconds)
                    self.assertEqual(bool(result["warnings"]), not expected)

    def test_equal_or_longer_reference_is_rejected_for_every_target(self):
        for seconds in (20, 30, 40, 50, 60):
            for source_seconds in (seconds, seconds + 0.0001, seconds + 10):
                with self.subTest(seconds=seconds, source_seconds=source_seconds), \
                        self.assertRaisesRegex(ValueError, "源视频必须短于目标生成时长"):
                    duration.reference_timing(source_seconds, seconds)

    def test_equal_or_longer_reference_never_creates_api_client(self):
        for seconds in (20, 30, 40, 50, 60):
            for source_seconds in (seconds, seconds + 5):
                for dry_run in ([], ["--dry-run"]):
                    with self.subTest(seconds=seconds, source_seconds=source_seconds, dry_run=dry_run), \
                            patch.object(muse, "probe_video_duration", return_value=source_seconds) as probe, \
                            patch.object(muse, "AimaxhugClient") as client:
                        code, result, _ = self.cli("run", "--prompt", "参考视频", "--seconds", str(seconds),
                            "--video-url", SOURCE, *dry_run, "--json")
                        self.assertEqual(code, 1)
                        self.assertEqual(result["state"], "failed")
                        self.assertIn(f"目标生成 {seconds} 秒", result["message"])
                        self.assertIn(f"≤{seconds - 2} 秒", result["message"])
                        probe.assert_called_once_with(SOURCE, "ffprobe")
                        client.assert_not_called()

    def test_reference_probe_failure_prevents_api_submission(self):
        with patch.object(muse, "probe_video_duration", side_effect=ValueError("检测失败")), \
                patch.object(muse, "AimaxhugClient") as client:
            code, result, _ = self.cli("run", "--prompt", "参考视频", "--seconds", "20", "--video-url", SOURCE, "--json")
        self.assertEqual(code, 1)
        self.assertEqual(result["message"], "检测失败")
        client.assert_not_called()

    def test_reference_dry_run_probes_but_never_submits(self):
        with patch.object(muse, "probe_video_duration", return_value=18.001) as probe, \
                patch.object(muse, "AimaxhugClient") as client:
            code, result, stderr = self.cli("run", "--prompt", "参考视频", "--seconds", "20",
                                          "--video-url", SOURCE, "--dry-run", "--json")
        self.assertEqual(code, 0)
        self.assertFalse(result["submitted"])
        self.assertEqual(result["request_preview"]["video_url"], SOURCE)
        self.assertFalse(result["preflight"]["reference_video"]["within_recommendation"])
        self.assertAlmostEqual(result["preflight"]["reference_video"]["available_continuation_seconds"], 1.999)
        self.assertIn("18.001", stderr)
        probe.assert_called_once_with(SOURCE, "ffprobe")
        client.assert_not_called()

    def test_over_recommendation_still_submits_with_exact_input(self):
        client = Mock()
        client.post_with_status.return_value = (200, {"task_id": "task-1", "status": "completed", "video_url": OUTPUT})
        with patch.object(muse, "probe_video_duration", return_value=19), \
                patch.object(muse, "AimaxhugClient", return_value=client), \
                patch("shared_download.env_save_dir", return_value=None):
            code, result, _ = self.cli("run", "--prompt", "参考视频", "--seconds", "20", "--video-url", SOURCE, "--json")
        self.assertEqual(code, 0)
        self.assertEqual(result["state"], "completed")
        body = client.post_with_status.call_args.kwargs["json"]
        self.assertEqual(body["video_url"], SOURCE)
        # The upstream expects a string on the wire; CLI timing stays numeric.
        self.assertEqual(body["seconds"], "20")

    def test_http_400_task_id_queries_existing_task_without_resubmit(self):
        client = Mock()
        client.post_with_status.return_value = (400, {"success": False, "data": {"task_id": "task-1"}})
        client.get_with_status.return_value = (200, {"data": {"status": "completed", "video_url": OUTPUT}})
        with contextlib.redirect_stderr(io.StringIO()):
            result = muse.generate(client, self.body(), 30)
        self.assertEqual(result["video_url"], OUTPUT)
        self.assertEqual(result["task_id"], "task-1")
        client.post_with_status.assert_called_once()
        self.assertEqual(client.post_with_status.call_args.args[0], muse.VIDEO_ENDPOINT)
        self.assertEqual(client.get_with_status.call_args.args[0], muse.VIDEO_ENDPOINT + "/muse-video-pro/task-1")

    def test_input_echo_is_not_returned_as_generated_video(self):
        response = {"status": "completed", "video_url": SOURCE, "request": {"url": SOURCE},
                    "data": {"result": {"url": OUTPUT}}}
        self.assertEqual(muse.inspect(response, "task-1", (SOURCE,))["video_url"], OUTPUT)
        self.assertEqual(muse.inspect(response, "task-1")["video_url"], OUTPUT)
        with self.assertRaises(AimaxhugError):
            muse.inspect({"status": "completed", "video_url": SOURCE}, "task-1", (SOURCE,))

    def test_processing_echo_does_not_complete_task(self):
        response = {"status": "processing", "video_url": SOURCE, "progress": 25}
        result = muse.inspect(response, "task-1", (SOURCE,))
        self.assertEqual(result["state"], "processing")
        self.assertEqual(result["progress"], 25)

    def test_failure_wins_over_url(self):
        with self.assertRaises(AimaxhugError):
            muse.inspect({"status": "failed", "video_url": OUTPUT}, "task-1")

    def test_missing_id_or_failed_submit_is_not_retried(self):
        for response in ((200, {"status": "processing"}), (400, {"message": "bad request"})):
            client = Mock()
            client.post_with_status.return_value = response
            with self.subTest(response=response), self.assertRaises(AimaxhugError):
                muse.generate(client, self.body(), 30)
            client.post_with_status.assert_called_once()
            client.get_with_status.assert_not_called()

    def test_status_command_and_encoded_task_id(self):
        client = Mock()
        client.get_with_status.return_value = (200, {"data": {"status": "processing", "progress": 60}})
        with patch.object(muse, "AimaxhugClient", return_value=client):
            code, result, _ = self.cli("status", "--task-id", "task/1", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(result["progress"], 60)
        self.assertTrue(client.get_with_status.call_args.args[0].endswith("/muse-video-pro/task%2F1"))

    def test_timeout_preserves_task_id(self):
        with self.assertRaisesRegex(AimaxhugError, "task-1"):
            muse.wait(Mock(), "task-1", 0)

    def test_transient_query_failure_and_processing_keep_polling_same_task(self):
        client = Mock()
        client.get_with_status.side_effect = [AimaxhugError("temporary", 503),
            (200, {"status": "processing", "progress": 50}),
            (200, {"status": "completed", "video_url": OUTPUT})]
        with patch.object(muse.time, "monotonic", side_effect=itertools.count()), \
                patch.object(muse.time, "sleep") as sleep, contextlib.redirect_stderr(io.StringIO()):
            result = muse.wait(client, "task-1", 60)
        self.assertEqual(result["video_url"], OUTPUT)
        self.assertEqual(client.get_with_status.call_count, 3)
        self.assertEqual(sleep.call_count, 2)
        self.assertTrue(all(call.args[0].endswith("/muse-video-pro/task-1")
                            for call in client.get_with_status.call_args_list))
        client.post_with_status.assert_not_called()

    def test_auth_failure_stops_polling(self):
        client = Mock()
        client.get_with_status.side_effect = AimaxhugError("unauthorized", 401)
        with patch.object(muse.time, "sleep") as sleep, self.assertRaises(AimaxhugError):
            muse.wait(client, "task-1", 60)
        client.get_with_status.assert_called_once()
        sleep.assert_not_called()


class DurationTests(unittest.TestCase):
    def probe(self, metadata):
        completed = SimpleNamespace(stdout=json.dumps(metadata))
        with patch.object(duration.subprocess, "run", return_value=completed) as run:
            value = duration.probe_video_duration(SOURCE, ffprobe="custom ffprobe.exe")
        self.assertEqual(run.call_args.args[0][0], "custom ffprobe.exe")
        self.assertEqual(run.call_args.args[0][-1], SOURCE)
        self.assertNotIn("shell", run.call_args.kwargs)
        return value

    def test_video_stream_duration_preferred_over_audio_container(self):
        self.assertEqual(self.probe({"streams": [{"codec_type": "video", "duration": "17.999"},
            {"codec_type": "audio", "duration": "30"}], "format": {"duration": "30"}}), 17.999)

    def test_container_fallback_with_valid_video_stream(self):
        self.assertEqual(self.probe({"streams": [{"codec_type": "video", "duration": "N/A"}],
                                    "format": {"duration": "28.01"}}), 28.01)

    def test_audio_only_cover_art_and_unknown_duration_are_rejected(self):
        for metadata in ({"streams": [{"codec_type": "audio"}], "format": {"duration": "10"}},
                         {"streams": [{"codec_type": "video", "disposition": {"attached_pic": 1}}],
                          "format": {"duration": "10"}},
                         {"streams": [{"codec_type": "video"}]},
                         {"streams": [{"codec_type": "video", "duration": "nan"}], "format": {"duration": "inf"}}):
            with self.subTest(metadata=metadata), self.assertRaises(ValueError):
                self.probe(metadata)

    def test_probe_errors_have_actionable_messages(self):
        errors = (FileNotFoundError(), subprocess.TimeoutExpired("ffprobe", 60),
                  subprocess.CalledProcessError(1, "ffprobe"))
        for error in errors:
            with self.subTest(error=error), patch.object(duration.subprocess, "run", side_effect=error), \
                    self.assertRaises(ValueError):
                duration.probe_video_duration(SOURCE)

    def test_local_paths_and_missing_files(self):
        with tempfile.TemporaryDirectory() as folder:
            video = Path(folder) / "a video.mp4"
            video.write_bytes(b"fixture")
            metadata = {"streams": [{"codec_type": "video"}], "format": {"duration": "18"}}
            with patch.object(duration.subprocess, "run", return_value=SimpleNamespace(stdout=json.dumps(metadata))) as run:
                self.assertEqual(duration.probe_video_duration(video), 18)
                self.assertEqual(run.call_args.args[0][-1], str(video.resolve()))
            with self.assertRaises(ValueError):
                duration.probe_video_duration(Path(folder) / "missing.mp4")

    def test_independent_cli_outputs_measured_duration_and_advice(self):
        stdout = io.StringIO()
        with patch.object(duration, "probe_video_duration", return_value=28.001), contextlib.redirect_stdout(stdout):
            code = duration.main([SOURCE, "--seconds", "30", "--json"])
        result = json.loads(stdout.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(result["source_duration_seconds"], 28.001)
        self.assertAlmostEqual(result["available_continuation_seconds"], 1.999)
        self.assertFalse(result["within_recommendation"])

    def test_independent_cli_rejects_equal_reference(self):
        stdout = io.StringIO()
        with patch.object(duration, "probe_video_duration", return_value=20), contextlib.redirect_stdout(stdout):
            code = duration.main([SOURCE, "--seconds", "20", "--json"])
        result = json.loads(stdout.getvalue())
        self.assertEqual(code, 1)
        self.assertEqual(result["state"], "failed")
        self.assertIn("20.000000 秒", result["message"])


if __name__ == "__main__":
    unittest.main()
