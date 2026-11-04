"""Offline upload checks with real image/video encoding and mocked HTTP."""

import base64
import hashlib
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from PIL import Image
import requests

from shared_client import AimaxhugClient, AimaxhugError
import shared_media as media
from video_duration import probe_video_duration
import minimax_video


class MediaUploadTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.folder = Path(self.temporary.name)
        self.source = self.folder / "original.png"
        with Image.effect_noise((2400, 1600), 90) as noise, noise.convert("RGB") as image:
            image.save(self.source)

    def tearDown(self):
        self.temporary.cleanup()

    def test_real_image_keeps_dimensions_and_original_unchanged(self):
        original = self.source.read_bytes()
        with media.prepare_upload(self.source, "image/png") as prepared:
            compressed = prepared.path
            self.assertNotEqual(compressed, self.source)
            # This image remains >1MB at quality 40 and must still be accepted.
            self.assertGreater(compressed.stat().st_size, 1_000_000)
            self.assertLess(compressed.stat().st_size, len(original))
            self.assertEqual(prepared.mime_type, "image/jpeg")
            self.assertEqual(prepared.name, "original.jpg")
            with Image.open(compressed) as image:
                image.load()
                self.assertEqual(image.size, (2400, 1600))
        self.assertFalse(compressed.exists())
        self.assertEqual(self.source.read_bytes(), original)

    def test_alpha_and_animation_are_preserved(self):
        alpha = self.folder / "alpha.png"
        with Image.new("RGBA", (400, 300), (255, 0, 0, 80)) as image:
            image.save(alpha)
        with media.prepare_upload(alpha, "image/png") as prepared, Image.open(prepared.path) as image:
            self.assertEqual(prepared.mime_type, "image/webp")
            self.assertEqual(image.getpixel((50, 50))[3], 80)
        animation = self.folder / "animation.gif"
        with Image.new("RGB", (160, 120), "red") as first, Image.new("RGB", (160, 120), "blue") as second:
            first.save(animation, save_all=True, append_images=[second], duration=[100, 200], loop=2)
        with media.prepare_upload(animation, "image/gif") as prepared, Image.open(prepared.path) as image:
            self.assertTrue(image.is_animated)
            self.assertEqual(image.n_frames, 2)
            self.assertEqual(image.info["loop"], 2)

    def client(self, post):
        client = AimaxhugClient(api_key="offline-test-only")
        client._requests = SimpleNamespace(post=post, exceptions=requests.exceptions)
        return client

    def test_http_receives_compressed_bytes_and_server_link_is_returned(self):
        uploaded_paths = []
        def post(url, **kwargs):
            name, handle, mime_type = kwargs["files"]["file"]
            uploaded_paths.append(Path(handle.name))
            data = handle.read()
            self.assertGreater(len(data), 1_000_000)
            self.assertEqual(name, "original.jpg")
            self.assertEqual(mime_type, "image/jpeg")
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
            response = {"status": 200, "data": {"tmp_url": "https://media.example.com/compressed.jpg",
                        "name": name, "type": mime_type, "size": len(data)}}
            return SimpleNamespace(status_code=200, json=lambda: response)
        client = self.client(Mock(side_effect=post))
        result = client.post_file("/api/v2/upload/file", str(self.source), "image/png")
        self.assertEqual(result["tmp_url"], "https://media.example.com/compressed.jpg")
        self.assertEqual(result["type"], "image/jpeg")
        self.assertGreater(result["size"], 1_000_000)
        self.assertTrue(all(not path.exists() for path in uploaded_paths))
        client._requests.post.assert_called_once()

    def test_failed_upload_cleans_up_and_keeps_original(self):
        uploaded_paths = []
        original = self.source.read_bytes()
        def post(url, **kwargs):
            uploaded_paths.append(Path(kwargs["files"]["file"][1].name))
            raise requests.exceptions.ConnectionError()
        with self.assertRaises(AimaxhugError):
            self.client(post).post_file("/api/v2/upload/file", str(self.source), "image/png")
        self.assertTrue(all(not path.exists() for path in uploaded_paths))
        self.assertEqual(self.source.read_bytes(), original)

    def test_invalid_image_never_uploads_uncompressed_original(self):
        self.source.write_bytes(b"not an image")
        client = self.client(Mock())
        with self.assertRaises(AimaxhugError):
            client.post_file("/api/v2/upload/file", str(self.source), "image/png")
        client._requests.post.assert_not_called()

    def test_nonvisual_files_and_explicit_final_artifact_bypass_are_unchanged(self):
        for mime_type, compress in (("audio/mpeg", True), ("text/html", True), ("image/png", False)):
            with self.subTest(mime_type=mime_type), media.prepare_upload(self.source, mime_type, compress=compress) as prepared:
                self.assertEqual(prepared.path, self.source)
                self.assertEqual(prepared.mime_type, mime_type)

    def test_exif_orientation_is_applied_before_upload(self):
        source = self.folder / "rotated.jpg"
        with Image.new("RGB", (200, 100), "red") as image:
            exif = image.getexif()
            exif[274] = 6
            image.save(source, exif=exif)
        with media.prepare_upload(source, "image/jpeg") as prepared, Image.open(prepared.path) as image:
            self.assertEqual(image.size, (100, 200))
            self.assertNotIn(274, image.getexif())

    def test_minimax_inline_reference_also_uses_compressed_bytes(self):
        reference = minimax_video._media_value(str(self.source))
        metadata, encoded = reference.split(",", 1)
        self.assertEqual(metadata, "data:image/jpeg;base64")
        content = base64.b64decode(encoded, validate=True)
        self.assertGreater(len(content), 1_000_000)
        with Image.open(io.BytesIO(content)) as image:
            image.verify()
        self.assertEqual(minimax_video._media_value("https://media.example.com/image.png"),
                         "https://media.example.com/image.png")

    def test_real_video_keeps_resolution_duration_fps_and_audio_without_size_limit(self):
        source = self.folder / "video.mp4"
        media._run_ffmpeg(["-y", "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=24",
                          "-f", "lavfi", "-i", "sine=frequency=600:sample_rate=44100", "-t", "20",
                          "-c:v", "libx264", "-preset", "ultrafast", "-crf", "15", "-c:a", "aac", str(source)])
        original_hash = hashlib.sha256(source.read_bytes()).digest()
        with media.prepare_upload(source, "video/mp4") as prepared:
            temporary_path = prepared.path
            self.assertEqual(prepared.mime_type, "video/mp4")
            self.assertGreater(prepared.path.stat().st_size, 1_000_000)
            metadata = media.ffmpeg_video_metadata(prepared.path)
            self.assertAlmostEqual(metadata["duration"], 20, delta=0.15)
            self.assertEqual(metadata["audio_streams"], 1)
            self.assertEqual(metadata["fps"], 24)
            frame = self.folder / "frame.png"
            media._run_ffmpeg(["-y", "-i", str(prepared.path), "-frames:v", "1", str(frame)])
            with Image.open(frame) as image:
                self.assertEqual(image.size, (1280, 720))
            self.assertAlmostEqual(probe_video_duration(prepared.path), 20, delta=0.15)
            media._run_ffmpeg(["-v", "error", "-i", str(prepared.path), "-f", "null", "-"])
        self.assertFalse(temporary_path.exists())
        self.assertEqual(hashlib.sha256(source.read_bytes()).digest(), original_hash)


if __name__ == "__main__":
    unittest.main()
