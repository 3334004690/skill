"""Compress reference uploads into temporary files without touching originals."""

from contextlib import contextmanager
from dataclasses import dataclass
import math
import mimetypes
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


IMAGE_QUALITY = 40
VIDEO_CRF = 40


@dataclass
class UploadMedia:
    path: Path
    name: str
    mime_type: str


def ffmpeg_executable():
    executable = shutil.which("ffmpeg")
    if executable:
        return executable
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except (ImportError, RuntimeError, OSError) as exc:
        raise ValueError("缺少视频处理组件，请使用当前 Python 执行 scripts/preflight.py --install-deps") from exc


def _run_ffmpeg(arguments, timeout=300, check=True):
    try:
        return subprocess.run(
            [ffmpeg_executable(), "-hide_banner", "-nostdin", *arguments],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout, check=check,
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError("视频处理超时，本次未上传；请检查素材或稍后重试") from exc
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError("视频处理失败，本次未上传；请检查素材是否为可读取的视频") from exc


def ffmpeg_video_metadata(source, timeout=60):
    """Read FFmpeg's input report when a standalone ffprobe is unavailable."""
    completed = _run_ffmpeg(["-i", str(source)], timeout=timeout, check=False)
    report = completed.stderr
    duration = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", report)
    video_lines = [line for line in report.splitlines() if re.search(r"Stream .*Video:", line)
                   and "(attached pic)" not in line]
    if not duration or not video_lines:
        raise ValueError("无法读取有效的视频时长或视频流，本次未上传")
    hours, minutes, seconds = map(float, duration.groups())
    seconds += hours * 3600 + minutes * 60
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("视频时长无效，本次未上传")
    fps_match = re.search(r"([\d.]+) fps", video_lines[0])
    fps = float(fps_match.group(1)) if fps_match else 24.0
    if not math.isfinite(fps) or fps <= 0:
        fps = 24.0
    return {"duration": seconds, "fps": fps,
            "audio_streams": len(re.findall(r"Stream .*Audio:", report))}


def _compress_image(source, folder):
    try:
        from PIL import Image, ImageOps, ImageSequence
    except ImportError as exc:
        raise ValueError("缺少图片处理组件，请使用当前 Python 执行 scripts/preflight.py --install-deps") from exc
    frames = []
    durations = []
    try:
        with Image.open(source) as image:
            animated = bool(getattr(image, "is_animated", False))
            loop = image.info.get("loop", 0)
            for frame in ImageSequence.Iterator(image):
                durations.append(frame.info.get("duration", 100))
                oriented = ImageOps.exif_transpose(frame)
                has_alpha = "A" in oriented.getbands() or "transparency" in oriented.info
                frames.append(oriented.convert("RGBA" if has_alpha or animated else "RGB"))
                if not animated:
                    break
        transparent = any("A" in frame.getbands() for frame in frames)
        output = folder / ("reference.webp" if transparent or animated else "reference.jpg")
        options = {"quality": IMAGE_QUALITY}
        if output.suffix == ".webp":
            options["method"] = 6
            if animated:
                options.update(save_all=True, append_images=frames[1:], duration=durations, loop=loop)
        else:
            options.update(optimize=True, progressive=True)
        frames[0].save(output, **options)
        return output
    except (OSError, EOFError) as exc:
        raise ValueError("图片无法读取或压缩，本次未上传") from exc
    finally:
        for frame in frames:
            frame.close()


def _compress_video(source, folder):
    metadata = ffmpeg_video_metadata(source)
    output = folder / "reference.mp4"
    fps = metadata["fps"]

    def verified_output():
        encoded = ffmpeg_video_metadata(output)
        if abs(encoded["duration"] - metadata["duration"]) > max(0.15, 2 / fps):
            raise ValueError("压缩后视频时长发生异常变化，本次未上传")
        if encoded["audio_streams"] != metadata["audio_streams"]:
            raise ValueError("压缩后声音轨道不完整，本次未上传")
        return output

    # Keep resolution and timing. Pad at most one pixel for H.264's even size.
    _run_ffmpeg(["-y", "-i", str(source), "-map", "0:v:0", "-map", "0:a?", "-map_metadata", "-1",
                 "-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p", "-crf", str(VIDEO_CRF),
                 "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-fps_mode", "passthrough",
                 "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(output)])
    return verified_output()


@contextmanager
def prepare_upload(file_path, mime_type, compress=True):
    """Yield the actual multipart file; cleanup covers success and failure."""
    source = Path(file_path)
    if not source.is_file():
        raise ValueError(f"上传文件不存在: {source.name}")
    if not compress or not mime_type.startswith(("image/", "video/")):
        yield UploadMedia(source, source.name, mime_type)
        return
    with tempfile.TemporaryDirectory(prefix="aimaxhug-media-") as temporary:
        folder = Path(temporary)
        output = (_compress_image(source, folder) if mime_type.startswith("image/")
                  else _compress_video(source, folder))
        actual_type = mimetypes.guess_type(output.name)[0]
        if not actual_type or output.stat().st_size <= 0:
            raise ValueError("素材压缩结果无效，本次未上传")
        print(f"素材已压缩: {source.stat().st_size / 1000:.1f}KB → {output.stat().st_size / 1000:.1f}KB",
              file=sys.stderr, flush=True)
        yield UploadMedia(output, source.with_suffix(output.suffix).name, actual_type)
