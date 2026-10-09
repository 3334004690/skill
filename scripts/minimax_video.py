#!/usr/bin/env python3
"""Generate videos with the Aimaxhug video API.

Two model families are exposed behind a single CLI:

* **即梦 Seedance** — ``seedance2-0-pro-2`` / ``seedance2-5-pro-2``.
  Text-to-video and reference-driven video. Reference images / videos / audios
  are uploaded first and referenced by URL; the aspect ratio is sent as
  ``aspect_ratio`` and the output size as ``resolution``.

* **MiniMax H3** — ``minimax-h3-*``.
  Text-to-video, image-to-video, first/last-frame and reference-video driven.
  Reference media may be public URLs, data URIs, or local files (encoded as
  data URIs by this script); the aspect ratio is sent as ``ratio``.

The API is asynchronous: submit a JSON request to /v1/videos, then poll the
family-specific status endpoint until a playable URL is available.
"""

import argparse
import base64
import os
import json as json_mod
import mimetypes
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared.client import AimaxhugClient, AimaxhugError
from shared.download import download_to_local, env_save_dir
from shared.markers import mark_url
from ai_audio import audio_duration

VIDEO_ENDPOINT = "https://apis.aimaxhug.cloud/v1/videos"
UPLOAD_ENDPOINT = "/api/v2/upload/file"
POLL_INTERVAL = 10
DEFAULT_POLL_TIMEOUT = 30 * 60
MAX_PROMPT_CHARS = 7_000
MAX_REFERENCE_IMAGES = 5
MAX_REFERENCE_AUDIOS = 3
MAX_REFERENCE_VIDEOS = 1
MAX_DURATION_PROBE_BYTES = 100 * 1024 * 1024

# 即梦 Seedance 与 MiniMax H3 使用不同的画幅集合：Seedance 没有 adaptive。
SEEDANCE_RATIOS = ("16:9", "9:16", "1:1", "21:9", "4:3", "3:4")
MINIMAX_RATIOS = ("16:9", "9:16", "1:1", "21:9", "4:3", "3:4", "adaptive")

# 模型注册表。`family` 决定提交字段、参考素材处理方式和轮询路径。
VIDEO_MODELS = {
    # ---------------- 即梦 Seedance ----------------
    "seedance2-0-pro-2": {
        "name": "即梦 Seedance 2.0 Pro",
        "family": "seedance",
        "duration": {"type": "range", "min": 4, "max": 15, "default": 5},
        "ratios": SEEDANCE_RATIOS,
        "resolutions": ("480p", "720p"),
        "default_resolution": "480p",
        "assets": ("image", "video", "audio"),
        "limits": {"image": 9, "video": 3, "audio": 3},
    },
    "seedance2-5-pro-2": {
        "name": "即梦 Seedance 2.5 Pro",
        "family": "seedance",
        "duration": {"type": "choice", "options": (15, 30), "default": 15},
        "ratios": SEEDANCE_RATIOS,
        "resolutions": ("480p", "720p"),
        "default_resolution": "480p",
        "assets": ("image",),
        "limits": {"image": 9, "video": 0, "audio": 0},
    },
    # ---------------- MiniMax H3 ----------------
    "minimax-h3-768p": {
        "name": "MiniMax H3 768p",
        "family": "minimax",
        "tier": "standard",
        "duration": {"type": "range", "min": 4, "max": 15, "default": 5},
        "ratios": MINIMAX_RATIOS,
    },
    "minimax-h3-2k": {
        "name": "MiniMax H3 2K",
        "family": "minimax",
        "tier": "standard",
        "duration": {"type": "range", "min": 4, "max": 15, "default": 5},
        "ratios": MINIMAX_RATIOS,
    },
    "minimax-h3-pro-768p": {
        "name": "MiniMax H3 Pro 768p",
        "family": "minimax",
        "tier": "pro",
        "duration": {"type": "range", "min": 4, "max": 15, "default": 5},
        "ratios": MINIMAX_RATIOS,
    },
    "minimax-h3-pro-2k": {
        "name": "MiniMax H3 Pro 2K",
        "family": "minimax",
        "tier": "pro",
        "duration": {"type": "range", "min": 4, "max": 15, "default": 5},
        "ratios": MINIMAX_RATIOS,
    },
}

VIDEO_EXTENSIONS = (".mp4", ".webm", ".mov", ".m4v", ".mkv", ".avi")
_RATIO_LABEL = "ratio"


# ---------------------------------------------------------------------------
# MiniMax reference media (data URI encoding)
# ---------------------------------------------------------------------------
def _media_value(value):
    """Return a public URL/data URI unchanged, or encode a local file."""
    value = value.strip()
    if value.startswith(("http://", "https://", "data:")):
        return value

    path = Path(value)
    if not path.exists() or not path.is_file():
        raise ValueError(f"参考素材不存在: {value}")
    mime_type, _ = mimetypes.guess_type(path.name)
    mime_type = mime_type or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _media_values(values, label):
    if not values:
        return []
    try:
        return [_media_value(value) for value in values]
    except (OSError, ValueError) as exc:
        raise ValueError(f"{label}无效: {exc}") from exc


def _duration_from_bytes(content, suffix):
    """Read media duration from bytes through the shared local-file reader."""
    with tempfile.NamedTemporaryFile(suffix=suffix or ".bin", delete=False) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    try:
        return audio_duration(temp_path)
    finally:
        if temp_path.exists():
            os.unlink(temp_path)


def _duration_from_source(value, label):
    """Read duration for a local file, direct URL, or base64 data URI."""
    value = value.strip()
    if not value.startswith(("http://", "https://", "data:")):
        return _local_media_duration(Path(value), label)

    try:
        if value.startswith("data:"):
            metadata, encoded = value.split(",", 1)
            if ";base64" not in metadata:
                raise ValueError("data URI 必须使用 base64 编码")
            mime_type = metadata[5:].split(";", 1)[0]
            content = base64.b64decode(encoded, validate=True)
            suffix = mimetypes.guess_extension(mime_type) or ".bin"
            return _local_media_duration_from_bytes(content, suffix, label)

        response = requests.get(value, stream=True, timeout=60)
        response.raise_for_status()
        content_type = (response.headers.get("Content-Type") or "").split(";", 1)[0]
        suffix = Path(urlparse(value).path).suffix or mimetypes.guess_extension(content_type) or ".bin"
        chunks = []
        total = 0
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if not chunk:
                continue
            total += len(chunk)
            if total > MAX_DURATION_PROBE_BYTES:
                raise ValueError("参考素材超过 100MB，无法预检时长")
            chunks.append(chunk)
        return _local_media_duration_from_bytes(b"".join(chunks), suffix, label)
    except (OSError, ValueError, requests.RequestException) as exc:
        raise ValueError(f"无法读取{label}时长: {exc}") from exc


def _local_media_duration(path, label):
    """Probe audio/video duration without creating user-visible files."""
    if path.suffix.lower() in {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi"}:
        try:
            completed = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                capture_output=True, text=True, timeout=30, check=True,
            )
            return float(completed.stdout.strip())
        except (FileNotFoundError, subprocess.SubprocessError, ValueError) as exc:
            raise ValueError(f"无法读取{label}时长，请安装 ffprobe 后重试") from exc
    return audio_duration(path)


def _local_media_duration_from_bytes(content, suffix, label):
    """Probe an internal temporary file and remove it immediately."""
    with tempfile.NamedTemporaryFile(suffix=suffix or ".bin", delete=False) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    try:
        return _local_media_duration(temp_path, label)
    finally:
        if temp_path.exists():
            os.unlink(temp_path)


def _validate_duration_constraints(args):
    audio_durations = [
        _duration_from_source(value, "参考音频")
        for value in (args.reference_audios or [])
    ]
    if sum(audio_durations) > 15:
        raise ValueError(f"参考音频总时长不能超过 15 秒，当前为 {sum(audio_durations):.2f} 秒")

    for value in args.reference_videos or []:
        duration = _duration_from_source(value, "参考视频")
        if not 2 <= duration <= 5:
            raise ValueError(f"参考视频时长必须为 2-5 秒，当前为 {duration:.2f} 秒")


# ---------------------------------------------------------------------------
# 即梦 Seedance reference media (upload first, then reference by URL)
# ---------------------------------------------------------------------------
def _upload_reference(client, value, label):
    """Return a public URL unchanged, or upload a local file and return its URL."""
    value = value.strip()
    if value.startswith(("http://", "https://")):
        return value

    path = Path(value)
    if not path.exists() or not path.is_file():
        raise ValueError(f"{label}不存在: {value}")
    mime_type, _ = mimetypes.guess_type(path.name)
    if not mime_type:
        raise ValueError(f"无法识别{label}类型: {path.name}")

    print(f"📤 上传{label}: {path.name}...", file=sys.stderr)
    data = client.post_file(UPLOAD_ENDPOINT, str(path), mime_type)
    url = data.get("tmp_url") or data.get("url")
    if not url:
        raise ValueError(f"{label}上传后未返回地址: {path.name}")
    return url


def _seedance_references(client, values, label):
    if not values:
        return []
    return [_upload_reference(client, value, label) for value in values]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def _resolve_duration(args, model):
    spec = model["duration"]
    if args.duration is None:
        return spec["default"]
    if spec["type"] == "range":
        if not spec["min"] <= args.duration <= spec["max"]:
            raise ValueError(
                f"{model['name']} 的 duration 必须为 {spec['min']}-{spec['max']} 秒"
            )
    elif args.duration not in spec["options"]:
        raise ValueError(
            f"{model['name']} 的 duration 必须是: "
            + " / ".join(str(option) for option in spec["options"])
            + " 秒"
        )
    return args.duration


def _validate_seedance_args(args, model):
    limits = model["limits"]
    assets = model["assets"]
    labels = {"image": "图片", "video": "视频", "audio": "音频"}
    counts = {
        "image": len(args.images or []),
        "video": len(args.videos or []),
        "audio": len(args.audios or []),
    }
    for kind, count in counts.items():
        if count and kind not in assets:
            raise ValueError(f"{model['name']} 不支持{labels[kind]}参考素材")
        if count > limits[kind]:
            raise ValueError(f"{labels[kind]}参考素材最多 {limits[kind]} 个")

    if args.reference_images or args.reference_audios or args.reference_videos \
            or args.first_image or args.last_image:
        raise ValueError(
            "即梦模型不支持 --reference-images/--reference-audios/--reference-videos/"
            "--first-image/--last-image，请使用 --images/--videos/--audios"
        )


def _validate_minimax_args(args, model):
    if args.images or args.videos or args.audios:
        raise ValueError(
            "MiniMax 模型不支持 --images/--videos/--audios，"
            "请使用 --reference-images/--reference-videos/--reference-audios"
        )
    if args.resolution:
        raise ValueError("MiniMax 模型不支持 --resolution（清晰度已包含在模型名中）")

    image_count = len(args.reference_images or [])
    audio_count = len(args.reference_audios or [])
    video_count = len(args.reference_videos or [])
    if image_count > MAX_REFERENCE_IMAGES:
        raise ValueError("referenceImages 最多 5 个")
    if audio_count > MAX_REFERENCE_AUDIOS:
        raise ValueError("referenceAudios 最多 3 个")
    if video_count > MAX_REFERENCE_VIDEOS:
        raise ValueError("referenceVideos 只能传 1 段")
    if audio_count and not image_count:
        raise ValueError("referenceAudios 必须同时提供 referenceImages")
    if video_count and model.get("tier") != "pro":
        raise ValueError("referenceVideos 仅 Pro 模型支持")
    if (args.first_image or args.last_image) and args.reference_images:
        raise ValueError("first_image/last_image 不能与 referenceImages 同时使用")
    if args.last_image and not args.first_image:
        raise ValueError("使用 last_image 时必须同时提供 first_image")
    if not image_count and not args.first_image and args.ratio == "adaptive":
        raise ValueError("文生视频不支持 ratio=adaptive")
    _validate_duration_constraints(args)


def _validate_args(args):
    model = VIDEO_MODELS[args.model]
    prompt = args.prompt.strip()
    if not prompt:
        raise ValueError("prompt 不能为空")

    if args.ratio and args.ratio not in model["ratios"]:
        raise ValueError(f"{_RATIO_LABEL} 必须是: {' / '.join(model['ratios'])}")

    if model["family"] == "seedance":
        if args.resolution and args.resolution not in model["resolutions"]:
            raise ValueError(f"resolution 必须是: {' / '.join(model['resolutions'])}")
        _validate_seedance_args(args, model)
    else:
        _validate_minimax_args(args, model)

    return _resolve_duration(args, model)


# ---------------------------------------------------------------------------
# Request body
# ---------------------------------------------------------------------------
def _build_seedance_body(client, args, model, duration):
    body = {
        "model": args.model,
        "prompt": args.prompt.strip(),
        "duration": duration,
        "aspect_ratio": args.ratio or model["ratios"][0],
        "resolution": args.resolution or model["default_resolution"],
    }
    images = _seedance_references(client, args.images, "参考图")
    videos = _seedance_references(client, args.videos, "参考视频")
    audios = _seedance_references(client, args.audios, "参考音频")
    if images:
        body["images"] = images
    if videos:
        body["videos"] = videos
    if audios:
        body["audios"] = audios
    return body


def _build_minimax_body(args, duration):
    """Build the MiniMax request body and omit optional values when absent."""
    # The API silently truncates prompts beyond 7000 characters; mirror that
    # behavior before submission so the request payload is deterministic.
    body = {"model": args.model, "prompt": args.prompt.strip()[:MAX_PROMPT_CHARS]}
    if duration is not None:
        body["duration"] = duration
    if args.ratio:
        body["ratio"] = args.ratio
    reference_images = _media_values(args.reference_images, "参考图")
    reference_audios = _media_values(args.reference_audios, "参考音频")
    reference_videos = _media_values(args.reference_videos, "参考视频")
    if reference_images:
        body["referenceImages"] = reference_images
    if reference_audios:
        body["referenceAudios"] = reference_audios
    if reference_videos:
        body["referenceVideos"] = reference_videos
    if args.first_image:
        body["first_image"] = _media_value(args.first_image)
    if args.last_image:
        body["last_image"] = _media_value(args.last_image)
    return body


def build_body(model, prompt, duration=None, ratio=None, reference_images=None,
               reference_audios=None, reference_videos=None, first_image=None,
               last_image=None):
    """Build a MiniMax request body (kept for programmatic callers)."""
    body = {"model": model, "prompt": prompt.strip()[:MAX_PROMPT_CHARS]}
    if duration is not None:
        body["duration"] = duration
    if ratio:
        body["ratio"] = ratio
    if reference_images:
        body["referenceImages"] = reference_images
    if reference_audios:
        body["referenceAudios"] = reference_audios
    if reference_videos:
        body["referenceVideos"] = reference_videos
    if first_image:
        body["first_image"] = first_image
    if last_image:
        body["last_image"] = last_image
    return body


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------
def _nested_data(response):
    if not isinstance(response, dict):
        return {}
    data = response.get("data")
    return data if isinstance(data, dict) else response


def _task_id(response):
    data = _nested_data(response)
    return (
        response.get("task_id") or response.get("taskId") or response.get("id")
        or data.get("task_id") or data.get("taskId") or data.get("id")
    )


def _iter_media(node, key="", depth=0):
    """Yield ``(key, value)`` pairs for every string in a response tree."""
    if depth > 8:
        return
    if isinstance(node, str):
        yield key, node
    elif isinstance(node, dict):
        for child_key, value in node.items():
            yield from _iter_media(value, str(child_key), depth + 1)
    elif isinstance(node, (list, tuple)):
        for value in node:
            yield from _iter_media(value, key, depth + 1)


# Keys whose URL values are request echoes or previews, never the generated video.
_INPUT_ECHO_KEYS = (
    "reference", "input", "source", "request", "origin", "originals", "upload",
    "cover", "poster", "thumb", "thumbnail", "avatar", "preview", "image",
)
# Exact request field names: a response echoing the submitted body repeats these.
_REQUEST_FIELDS = {"images", "videos", "audios"}


def _looks_like_video_url(value):
    if not isinstance(value, str) or not value.startswith(("http://", "https://")):
        return False
    return value.lower().split("?", 1)[0].split("#", 1)[0].endswith(VIDEO_EXTENSIONS)


def _find_video_url(response):
    """Find the first generated video URL in a response tree.

    Only URLs under output-ish keys (``video`` / ``output`` / ``result`` /
    ``download`` / ``file`` / ``url``) are considered, so a response that echoes
    the request (for example ``data.referenceVideos`` or ``data.videos``) can
    never be mistaken for the generated result. A URL whose path ends in a video
    extension wins outright; otherwise the first output-keyed URL is returned as
    a fallback, because the gateway sometimes serves results without an
    extension.
    """
    fallback = ""
    for key, value in _iter_media(response):
        if not isinstance(value, str) or not value.startswith(("http://", "https://")):
            continue
        lowered = key.lower()
        if lowered in _REQUEST_FIELDS:
            continue
        if any(token in lowered for token in _INPUT_ECHO_KEYS):
            continue
        if not any(token in lowered for token in ("video", "output", "result", "download", "file", "url")):
            continue
        if _looks_like_video_url(value):
            return value
        if not fallback:
            fallback = value
    return fallback


def _video_url(response):
    data = _nested_data(response)
    result = data.get("result") if isinstance(data.get("result"), dict) else {}
    explicit = (
        response.get("video_url") or response.get("videoUrl") or response.get("url")
        or data.get("video_url") or data.get("videoUrl") or data.get("url")
        or result.get("video_url") or result.get("videoUrl") or result.get("url")
    )
    return explicit or _find_video_url(response)


def _status(response):
    data = _nested_data(response)
    return str(
        response.get("status") or response.get("task_status") or response.get("state")
        or data.get("status") or data.get("task_status") or data.get("state") or ""
    ).lower()


def _error_message(response):
    data = _nested_data(response)
    return response.get("message") or data.get("message") or response.get("error") or data.get("error") or "未知错误"


def _poll_endpoint(model, task_id):
    """Both families submit to /v1/videos but poll under different paths."""
    if VIDEO_MODELS.get(model, {}).get("family") == "seedance":
        return f"{VIDEO_ENDPOINT}/{model}/{task_id}"
    return f"{VIDEO_ENDPOINT}/minimax-h3/{task_id}"


# ---------------------------------------------------------------------------
# Submission + polling
# ---------------------------------------------------------------------------
def _submit_and_wait(client, body, poll_timeout):
    print(
        f"📨 POST {VIDEO_ENDPOINT} | model={body.get('model')} | "
        f"duration={body.get('duration')} | "
        f"ratio={body.get('ratio') or body.get('aspect_ratio') or '未指定'} | "
        f"resolution={body.get('resolution', '未指定')} | "
        f"referenceImages={len(body.get('referenceImages', body.get('images', [])))}",
        file=sys.stderr,
    )
    http_status, response = client.post_with_status(VIDEO_ENDPOINT, json=body, timeout=120)
    task_id = _task_id(response)
    # The gateway may return HTTP 400 together with a valid task ID. Keep the
    # ID and query it instead of discarding the task at submission time.
    if http_status < 200 or http_status >= 300:
        if not task_id:
            raise AimaxhugError(_error_message(response), http_status)
        print(f"⚠️ 提交接口返回 HTTP {http_status}，但已生成任务 ID；继续查询任务。", file=sys.stderr)
    if response.get("success") is False and not task_id:
        raise AimaxhugError(_error_message(response), http_status)
    if _status(response) in {"failed", "failure", "error"} and not task_id:
        raise AimaxhugError(_error_message(response), http_status)
    direct_url = _video_url(response)
    if direct_url:
        if task_id:
            print(f"✅ 任务已提交，任务 ID: {task_id}", file=sys.stderr)
        return response, direct_url, task_id
    if not task_id:
        raise AimaxhugError(f"提交成功但响应中没有 task_id: {_error_message(response)}")

    status_endpoint = _poll_endpoint(body.get("model"), task_id)
    started = time.monotonic()
    poll_count = 0
    print(f"✅ 任务已提交，任务 ID: {task_id}", file=sys.stderr)
    while time.monotonic() - started < poll_timeout:
        poll_count += 1
        try:
            poll_http_status, status_response = client.get_with_status(status_endpoint, timeout=120)
        except AimaxhugError as exc:
            elapsed = int(time.monotonic() - started)
            print(f"⚠️ 任务 {task_id} 第 {poll_count} 次查询暂时失败：{exc}；继续查询（已等待 {elapsed} 秒）", file=sys.stderr)
            time.sleep(POLL_INTERVAL)
            continue
        status = _status(status_response)
        direct_url = _video_url(status_response)
        nested = _nested_data(status_response)
        progress = nested.get("progress") if "progress" in nested else status_response.get("progress")
        progress_text = f"，进度 {progress}%" if progress is not None else ""
        elapsed = int(time.monotonic() - started)
        http_text = f"，HTTP {poll_http_status}" if poll_http_status < 200 or poll_http_status >= 300 else ""
        print(f"⏳ 任务 {task_id}：第 {poll_count} 次轮询，状态 {status or 'processing'}{progress_text}{http_text}（已等待 {elapsed} 秒）", file=sys.stderr)
        if direct_url or status in {"completed", "complete", "succeeded", "success", "done", "finished"}:
            if not direct_url:
                raise AimaxhugError("任务已完成但响应中没有视频 URL")
            return status_response, direct_url, task_id
        if status in {"failed", "failure", "error", "cancelled", "canceled"}:
            raise AimaxhugError(_error_message(status_response))
        time.sleep(POLL_INTERVAL)

    raise AimaxhugError(f"视频生成超时，已等待 {poll_timeout} 秒，task_id={task_id}")


# ---------------------------------------------------------------------------
# Modes (for display)
# ---------------------------------------------------------------------------
def _mode_for(model, args):
    if model["family"] == "seedance":
        return "参考素材生视频" if (args.images or args.videos or args.audios) else "文生视频"
    if args.reference_videos:
        return "参考视频驱动"
    if args.first_image or args.last_image:
        return "首尾帧"
    if args.reference_images or args.reference_audios:
        return "图生视频"
    return "文生视频"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def cmd_list_models(_args):
    print("可用视频模型：")
    print("\n  即梦 Seedance：")
    for key, model in VIDEO_MODELS.items():
        if model["family"] != "seedance":
            continue
        spec = model["duration"]
        duration = (
            f"{spec['min']}-{spec['max']} 秒"
            if spec["type"] == "range"
            else " / ".join(str(option) for option in spec["options"]) + " 秒"
        )
        assets = " / ".join(
            {"image": "图片", "video": "视频", "audio": "音频"}[kind] for kind in model["assets"]
        )
        print(f"    [{key}] {model['name']}")
        print(f"        时长: {duration}（默认 {spec['default']} 秒）")
        print(f"        画幅: {' / '.join(model['ratios'])}")
        print(f"        分辨率: {' / '.join(model['resolutions'])}（默认 {model['default_resolution']}）")
        print(f"        参考素材: {assets}")

    print("\n  MiniMax H3：")
    for key, model in VIDEO_MODELS.items():
        if model["family"] != "minimax":
            continue
        pro_note = "（Pro，支持参考视频）" if model["tier"] == "pro" else ""
        print(f"    [{key}] {model['name']} {pro_note}")
    print("        时长: 4-15 秒；画幅: " + " / ".join(MINIMAX_RATIOS))
    print("        参考图最多 5 张，参考音频最多 3 个（须配图），参考视频仅 Pro 且只能 1 段。")

    print("\n即梦模型使用 --images / --videos / --audios / --resolution；"
          "MiniMax 模型使用 --reference-images / --reference-audios / --reference-videos。")


def add_generate_args(parser):
    parser.add_argument("--model", choices=list(VIDEO_MODELS), default="seedance2-0-pro-2",
                        help="视频模型 key（默认: seedance2-0-pro-2）")
    parser.add_argument("--prompt", required=True, help="视频提示词，最多 7000 字符")
    parser.add_argument("--duration", type=int, default=None,
                        help="视频时长（秒）；即梦 2.0 与 MiniMax 为 4-15，即梦 2.5 为 15/30")
    parser.add_argument("--ratio", default=None,
                        help="画幅比例；即梦按 aspect_ratio 提交，MiniMax 按 ratio 提交")
    parser.add_argument("--resolution", default=None,
                        help="即梦专用分辨率：480p / 720p")
    parser.add_argument("--images", nargs="+", default=None,
                        help="即梦参考图，URL 或本地文件，最多 9 张")
    parser.add_argument("--videos", nargs="+", default=None,
                        help="即梦参考视频（仅 2.0），URL 或本地文件，最多 3 段")
    parser.add_argument("--audios", nargs="+", default=None,
                        help="即梦参考音频（仅 2.0），URL 或本地文件，最多 3 个")
    parser.add_argument("--reference-images", nargs="+", default=None,
                        help="MiniMax 参考图 URL、data URI 或本地文件，最多 5 个")
    parser.add_argument("--reference-audios", nargs="+", default=None,
                        help="MiniMax 参考音频 URL、data URI 或本地文件，最多 3 个且须配参考图")
    parser.add_argument("--reference-videos", nargs="+", default=None,
                        help="MiniMax Pro 专用参考视频 URL、data URI 或本地文件，只能 1 个")
    parser.add_argument("--first-image", default=None, help="MiniMax 首帧图 URL、data URI 或本地文件")
    parser.add_argument("--last-image", default=None, help="MiniMax 尾帧图 URL、data URI 或本地文件")
    parser.add_argument("--poll-timeout", type=int, default=DEFAULT_POLL_TIMEOUT,
                        help="最长轮询等待秒数（默认 1800，即 30 分钟）")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出结果")


def cmd_run(args):
    model = VIDEO_MODELS[args.model]
    try:
        duration = _validate_args(args)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    client = AimaxhugClient()
    try:
        if model["family"] == "seedance":
            body = _build_seedance_body(client, args, model, duration)
        else:
            body = _build_minimax_body(args, duration)
    except (ValueError, AimaxhugError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    mode = _mode_for(model, args)
    print(
        f"🎬 正在使用 {model['name']} 进行{mode}，提交配置：duration={body['duration']} 秒"
        f"，ratio={body.get('ratio') or body.get('aspect_ratio', '默认')}"
        f"，resolution={body.get('resolution', '默认')}；提交任务并等待完成...",
        file=sys.stderr,
    )

    try:
        response, video_url, task_id = _submit_and_wait(client, body, args.poll_timeout)
    except AimaxhugError as exc:
        print(f"Error: 视频生成失败: {exc}", file=sys.stderr)
        sys.exit(1)

    result = {
        "success": True,
        "video_url": video_url,
        "markedUrl": mark_url(video_url, "video"),
        "task_id": task_id or _task_id(response),
        "model": args.model,
        "model_name": model["name"],
        "prompt": body["prompt"],
        "duration": body["duration"],
        "ratio": body.get("ratio") or body.get("aspect_ratio"),
        "resolution": body.get("resolution"),
        "mode": mode,
    }
    # 宿主注入 SKILL_OUTPUT_DIR 时下载到该目录（agent 直接引用本地路径，无需自行下载）
    save_dir = env_save_dir()
    if save_dir:
        result["local_path"] = download_to_local(
            video_url, save_dir, 1, default_ext=".mp4", timeout=300
        ) or ""
    if args.json:
        print(json_mod.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("\n✅ 视频生成成功！")
        if result.get("local_path"):
            print(f"💾 已保存: {result['local_path']}")
            print(f"VIDEO_SAVED: {result['local_path']}")
        print(f"📍 {video_url}")
        print(f"  IMAGE_MARKED: {result['markedUrl']}")
        print(f"🎬 [点击播放]({video_url})")
        print(f"🤖 模型: {model['name']}")
        print(f"📋 模式: {mode}")
        print(f"⏱ 时长: {body['duration']} 秒")
        if result["ratio"]:
            print(f"📐 比例: {result['ratio']}")
        if result["resolution"]:
            print(f"🔍 分辨率: {result['resolution']}")
        if result["task_id"]:
            print(f"任务 ID: {result['task_id']}")


def main():
    parser = argparse.ArgumentParser(description="即梦 Seedance / MiniMax H3 视频生成")
    sub = parser.add_subparsers(dest="subcommand")
    sub.add_parser("list-models", help="列出视频模型和参数")
    run_parser = sub.add_parser("run", help="生成视频（默认）")
    add_generate_args(run_parser)
    args = parser.parse_args()

    if args.subcommand == "list-models":
        cmd_list_models(args)
    elif args.subcommand == "run":
        cmd_run(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
