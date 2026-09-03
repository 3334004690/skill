#!/usr/bin/env python3
"""Generate videos with the MiniMax H3 video API.

The API is asynchronous: submit a JSON request to /v1/videos, then poll
/v1/videos/{model}/{task_id} until a playable URL is available.
Reference media may be public URLs, data URIs, or local files (encoded as
data URIs by this script).
"""

import argparse
import base64
import os
import json as json_mod
import mimetypes
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared.client import AimaxhugClient, AimaxhugError
from ai_audio import audio_duration

VIDEO_ENDPOINT = "https://apis.aimaxhug.cloud/v1/videos"
POLL_INTERVAL_FAST = 4
POLL_INTERVAL_SLOW = 12
MAX_PROMPT_CHARS = 7_000
MAX_REFERENCE_IMAGES = 5
MAX_REFERENCE_AUDIOS = 3
MAX_REFERENCE_VIDEOS = 1
MAX_DURATION_PROBE_BYTES = 100 * 1024 * 1024

VIDEO_MODELS = {
    "minimax-h3-768p": {"name": "MiniMax H3 768p", "tier": "standard"},
    "minimax-h3-2k": {"name": "MiniMax H3 2K", "tier": "standard"},
    "minimax-h3-pro-768p": {"name": "MiniMax H3 Pro 768p", "tier": "pro"},
    "minimax-h3-pro-2k": {"name": "MiniMax H3 Pro 2K", "tier": "pro"},
}

RATIOS = ("16:9", "9:16", "1:1", "21:9", "4:3", "3:4", "adaptive")


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
        return audio_duration(Path(value))

    try:
        if value.startswith("data:"):
            metadata, encoded = value.split(",", 1)
            if ";base64" not in metadata:
                raise ValueError("data URI 必须使用 base64 编码")
            mime_type = metadata[5:].split(";", 1)[0]
            content = base64.b64decode(encoded, validate=True)
            suffix = mimetypes.guess_extension(mime_type) or ".bin"
            return _duration_from_bytes(content, suffix)

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
        return _duration_from_bytes(b"".join(chunks), suffix)
    except (OSError, ValueError, requests.RequestException) as exc:
        raise ValueError(f"无法读取{label}时长: {exc}") from exc


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


def build_body(model, prompt, duration=None, ratio=None, reference_images=None,
               reference_audios=None, reference_videos=None, first_image=None,
               last_image=None):
    """Build the MiniMax request body and omit optional values when absent."""
    body = {"model": model, "prompt": prompt.strip()}
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


def _nested_data(response):
    if not isinstance(response, dict):
        return {}
    data = response.get("data")
    return data if isinstance(data, dict) else response


def _task_id(response):
    data = _nested_data(response)
    return response.get("task_id") or response.get("taskId") or data.get("task_id") or data.get("taskId")


def _video_url(response):
    data = _nested_data(response)
    return (
        response.get("video_url") or response.get("videoUrl") or response.get("url")
        or data.get("video_url") or data.get("videoUrl") or data.get("url") or ""
    )


def _status(response):
    data = _nested_data(response)
    return str(response.get("status") or data.get("status") or "").lower()


def _error_message(response):
    data = _nested_data(response)
    return response.get("message") or data.get("message") or response.get("error") or data.get("error") or "未知错误"


def _validate_args(args):
    model = VIDEO_MODELS[args.model]
    prompt = args.prompt.strip()
    if not prompt:
        raise ValueError("prompt 不能为空")
    if len(prompt) > MAX_PROMPT_CHARS:
        raise ValueError(f"prompt 最多 {MAX_PROMPT_CHARS} 个字符，当前 {len(prompt)} 个；超出部分不会生效")
    if args.duration is not None and not 4 <= args.duration <= 15:
        raise ValueError("duration 必须为 4-15 秒")
    if args.ratio and args.ratio not in RATIOS:
        raise ValueError(f"ratio 必须是: {' / '.join(RATIOS)}")

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
    if video_count and model["tier"] != "pro":
        raise ValueError("referenceVideos 仅 Pro 模型支持")
    if (args.first_image or args.last_image) and args.reference_images:
        raise ValueError("first_image/last_image 不能与 referenceImages 同时使用")
    if args.last_image and not args.first_image:
        raise ValueError("使用 last_image 时必须同时提供 first_image")
    if not image_count and not args.first_image and args.ratio == "adaptive":
        raise ValueError("文生视频不支持 ratio=adaptive")
    _validate_duration_constraints(args)


def cmd_list_models(_args):
    print("可用 MiniMax 视频模型：")
    for key, model in VIDEO_MODELS.items():
        pro_note = "（Pro，支持参考视频）" if model["tier"] == "pro" else ""
        print(f"  [{key}] {model['name']} {pro_note}")
    print("\n通用参数：duration 4-15 秒；ratio: 16:9 / 9:16 / 1:1 / 21:9 / 4:3 / 3:4 / adaptive")
    print("参考图最多 5 张，参考音频最多 3 个（须配图），参考视频仅 Pro 且只能 1 段。")


def add_generate_args(parser):
    parser.add_argument("--model", choices=list(VIDEO_MODELS), default="minimax-h3-768p",
                        help="MiniMax 模型 key（默认: minimax-h3-768p）")
    parser.add_argument("--prompt", required=True, help="视频提示词，最多 7000 字符")
    parser.add_argument("--duration", type=int, default=None, help="视频时长，4-15 秒")
    parser.add_argument("--ratio", choices=RATIOS, default=None, help="画幅比例")
    parser.add_argument("--reference-images", nargs="+", default=None,
                        help="参考图 URL、data URI 或本地文件，最多 5 个")
    parser.add_argument("--reference-audios", nargs="+", default=None,
                        help="参考音频 URL、data URI 或本地文件，最多 3 个且须配参考图")
    parser.add_argument("--reference-videos", nargs="+", default=None,
                        help="Pro 专用参考视频 URL、data URI 或本地文件，只能 1 个")
    parser.add_argument("--first-image", default=None, help="首帧图 URL、data URI 或本地文件")
    parser.add_argument("--last-image", default=None, help="尾帧图 URL、data URI 或本地文件")
    parser.add_argument("--poll-timeout", type=int, default=900, help="最长等待秒数（默认 900）")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出结果")


def _submit_and_wait(client, body, poll_timeout):
    response = client.post(VIDEO_ENDPOINT, json=body, timeout=120)
    direct_url = _video_url(response)
    task_id = _task_id(response)
    if direct_url:
        return response, direct_url, task_id
    if not task_id:
        raise AimaxhugError(f"提交成功但响应中没有 task_id: {_error_message(response)}")

    status_endpoint = f"{VIDEO_ENDPOINT}/{body['model']}/{task_id}"
    started = time.monotonic()
    while time.monotonic() - started < poll_timeout:
        status_response = client.get(status_endpoint, timeout=120)
        status = _status(status_response)
        direct_url = _video_url(status_response)
        if direct_url or status in {"completed", "complete", "succeeded", "success", "done"}:
            if not direct_url:
                raise AimaxhugError("任务已完成但响应中没有视频 URL")
            return status_response, direct_url, task_id
        if status in {"failed", "failure", "error", "cancelled", "canceled"}:
            raise AimaxhugError(_error_message(status_response))
        elapsed = time.monotonic() - started
        time.sleep(POLL_INTERVAL_FAST if elapsed < 60 else POLL_INTERVAL_SLOW)

    raise AimaxhugError(f"视频生成超时，已等待 {poll_timeout} 秒，task_id={task_id}")


def cmd_run(args):
    try:
        _validate_args(args)
        reference_images = _media_values(args.reference_images, "参考图")
        reference_audios = _media_values(args.reference_audios, "参考音频")
        reference_videos = _media_values(args.reference_videos, "参考视频")
        first_image = _media_value(args.first_image) if args.first_image else None
        last_image = _media_value(args.last_image) if args.last_image else None
        body = build_body(args.model, args.prompt, args.duration, args.ratio, reference_images,
                          reference_audios, reference_videos, first_image, last_image)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    client = AimaxhugClient()
    has_references = bool(reference_images or reference_audios or reference_videos or first_image or last_image)
    mode = "文生视频"
    if reference_videos:
        mode = "参考视频驱动"
    elif first_image or last_image:
        mode = "首尾帧"
    elif has_references:
        mode = "图生视频"
    print(f"🎬 正在使用 {args.model} 进行{mode}，提交任务并等待完成...", file=sys.stderr)

    try:
        response, video_url, task_id = _submit_and_wait(client, body, args.poll_timeout)
    except AimaxhugError as exc:
        print(f"Error: 视频生成失败: {exc}", file=sys.stderr)
        sys.exit(1)

    result = {
        "success": True,
        "video_url": video_url,
        "task_id": task_id or _task_id(response),
        "model": args.model,
        "prompt": args.prompt,
        "duration": args.duration,
        "ratio": args.ratio,
        "mode": mode,
    }
    if args.json:
        print(json_mod.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("\n✅ 视频生成成功！")
        print(f"📍 {video_url}")
        print(f"🎬 [点击播放]({video_url})")
        print(f"🤖 模型: {args.model}")
        print(f"📋 模式: {mode}")
        if args.duration is not None:
            print(f"⏱ 时长: {args.duration} 秒")
        if args.ratio:
            print(f"📐 比例: {args.ratio}")
        if result["task_id"]:
            print(f"任务 ID: {result['task_id']}")


def main():
    parser = argparse.ArgumentParser(description="MiniMax H3 视频生成")
    sub = parser.add_subparsers(dest="subcommand")
    sub.add_parser("list-models", help="列出 MiniMax 视频模型和参数")
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
