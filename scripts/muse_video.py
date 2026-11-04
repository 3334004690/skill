#!/usr/bin/env python3
"""Generate Muse Video Pro videos through the shared Aimaxhug video API.

POST /v1/videos, then GET /v1/videos/muse-video-pro/{task_id}.
Reference videos are probed before submission; JSON logs go to stderr.
"""

import argparse
import base64
import binascii
import json
import sys
import time
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared_client import AimaxhugClient, AimaxhugError
from shared_markers import mark_url
from video_duration import media_url, probe_video_duration, reference_timing, validate_reference_seconds


VIDEO_ENDPOINT = "https://apis.aimaxhug.cloud/v1/videos"
MODEL = "muse-video-pro"
RATIOS = ("16:9", "9:16", "1:1", "4:3", "3:4")
SECONDS = (5, 8, 10, 20, 30, 40, 50, 60)
CAMERA_MOTIONS = ("pan_left", "zoom_in", "orbit", "tracking_shot", "static")
POLL_INTERVAL = 10
DEFAULT_POLL_TIMEOUT = 1800
REFERENCE_FIELDS = ("input_reference", "last_frame", "images", "video_url")
DONE = {"completed", "complete", "succeeded", "success", "done", "finished"}
FAILED = {"failed", "failure", "error", "cancelled", "canceled", "rejected"}


def log(message):
    print(message, file=sys.stderr, flush=True)


def boolean(value):
    lowered = value.lower()
    if lowered not in ("true", "false"):
        raise argparse.ArgumentTypeError("须为 true 或 false")
    return lowered == "true"


def positive_seconds(value):
    try:
        seconds = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("须为正整数秒") from exc
    if seconds <= 0:
        raise argparse.ArgumentTypeError("须为正整数秒")
    return seconds


def image_reference(value):
    value = value.strip()
    if value.startswith(("http://", "https://")):
        return media_url(value, "images")
    try:
        encoded = value
        if value.startswith("data:"):
            metadata, encoded = value.split(",", 1)
            if not metadata.startswith("data:image/") or not metadata.endswith(";base64"):
                raise ValueError("须为图片 Base64")
        if not base64.b64decode(encoded, validate=True):
            raise ValueError("图片 Base64 为空")
    except (ValueError, binascii.Error) as exc:
        raise ValueError("images 每项必须为 HTTP(S) URL、图片 Base64 或 data:image Base64") from exc
    return value


def build_body(args):
    if not args.prompt.strip():
        raise ValueError("prompt 不能为空")
    if args.seconds not in SECONDS:
        raise ValueError("seconds 必须是: " + " / ".join(map(str, SECONDS)))
    if len(args.images or []) > 4:
        raise ValueError("images 最多 4 张")
    body = {"model": args.model, "prompt": args.prompt.strip(), "aspect_ratio": args.aspect_ratio,
            "seconds": args.seconds, "mute_voice": args.mute_voice}
    for field in ("camera_motion", "negative_prompt"):
        value = getattr(args, field)
        if value is not None:
            if field == "camera_motion" and not value.strip():
                raise ValueError(f"{field} 不能为空")
            body[field] = value.strip()
    for field in ("input_reference", "last_frame", "video_url"):
        value = getattr(args, field)
        if value is not None:
            body[field] = media_url(value, field)
    if args.images:
        body["images"] = [image_reference(value) for value in args.images]
    if args.video_url is not None:
        validate_reference_seconds(args.seconds)
    return body


def preflight(body, ffprobe="ffprobe"):
    warnings = []
    if body["seconds"] > 40:
        warnings.append("为稳定产出，推荐选择 5–40 秒；50 / 60 秒仍可提交。")
    result = {"warnings": warnings}
    if body.get("video_url"):
        duration = probe_video_duration(body["video_url"], ffprobe)
        result["reference_video"] = reference_timing(duration, body["seconds"])
        warnings.extend(result["reference_video"]["warnings"])
    return result


def nested(response):
    if not isinstance(response, dict):
        return {}
    return response["data"] if isinstance(response.get("data"), dict) else response


def task_id_of(response):
    for node in (nested(response), response):
        for key in ("task_id", "taskId", "id"):
            value = node.get(key)
            if isinstance(value, (str, int)) and not isinstance(value, bool) and str(value).strip():
                return str(value).strip()
    return ""


def status_of(response):
    for node in (nested(response), response):
        for key in ("task_status", "state", "status"):
            value = node.get(key)
            if isinstance(value, str) and value.strip() and not value.isdigit():
                return value.lower().strip()
    return ""


def message_of(response):
    for node in (nested(response), response):
        for key in ("message", "error", "detail", "msg"):
            if node.get(key):
                return str(node[key])
    return "接口未提供详细说明"


def video_url_of(response, inputs=()):
    """Skip input echoes (including Muse's video_url) and preview branches."""
    blocked = ("reference", "input", "source", "request", "origin", "upload",
               "cover", "poster", "thumb", "preview", "image", "last_frame")
    candidates = []

    def visit(node, path=(), depth=0):
        if depth > 10:
            return
        if isinstance(node, dict):
            for key, child in node.items():
                key = str(key).lower()
                if key in ("images", "videos", "audios") or any(token in key for token in blocked):
                    continue
                visit(child, path + (key,), depth + 1)
        elif isinstance(node, list):
            for child in node:
                visit(child, path, depth + 1)
        elif isinstance(node, str) and node.startswith(("http://", "https://")) and node not in inputs:
            if any(token in key for key in path for token in ("video", "output", "result", "download", "file", "url")):
                score = 2 if node.split("?", 1)[0].lower().endswith((".mp4", ".webm", ".mov", ".m4v", ".mkv", ".avi")) else 1
                if any(key in ("output", "outputs", "result", "results") for key in path):
                    score += 4
                candidates.append((score, node))

    visit(response)
    return max(candidates, key=lambda item: item[0])[1] if candidates else ""


def status_endpoint(task_id):
    return f"{VIDEO_ENDPOINT}/{MODEL}/{quote(task_id, safe='')}"


def inspect(response, task_id, inputs=()):
    if not isinstance(response, dict):
        raise AimaxhugError(f"响应格式无效，task_id={task_id}")
    status = status_of(response)
    if status in FAILED or response.get("success") is False or nested(response).get("success") is False:
        raise AimaxhugError(f"任务失败，task_id={task_id}: {message_of(response)}")
    result = {"state": "processing", "task_id": task_id, "model": MODEL, "api_status": status or "unknown"}
    progress = nested(response).get("progress", response.get("progress"))
    if progress is not None:
        result["progress"] = progress
    url = video_url_of(response, inputs)
    if status in DONE or (url and not status):
        if not url:
            raise AimaxhugError(f"任务完成但没有视频 URL，task_id={task_id}")
        result.update(state="completed", video_url=url, markedUrl=mark_url(url, "video"))
    return result


def query(client, task_id, inputs=(), timeout=120):
    code, response = client.get_with_status(status_endpoint(task_id), timeout=timeout)
    if not isinstance(response, dict):
        raise AimaxhugError(f"查询响应格式无效，task_id={task_id}", code)
    if not 200 <= code < 300:
        raise AimaxhugError(f"查询失败，task_id={task_id}: {message_of(response)}", code)
    return inspect(response, task_id, inputs)


def wait(client, task_id, timeout, inputs=()):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            remaining = max(0.1, deadline - time.monotonic())
            result = query(client, task_id, inputs, min(120, remaining))
        except AimaxhugError as exc:
            if exc.status_code in (401, 403) or "任务失败" in str(exc) or "任务完成" in str(exc):
                raise
            log(f"任务 {task_id} 暂时查询失败: {exc}")
        else:
            log(f"任务 {task_id}: {result['api_status']}" + (f"，进度 {result['progress']}" if "progress" in result else ""))
            if result["state"] == "completed":
                return result
        remaining = deadline - time.monotonic()
        if remaining > 0:
            time.sleep(min(POLL_INTERVAL, remaining))
    raise AimaxhugError(f"查询超时，任务可能仍在生成；使用 status 继续查询，task_id={task_id}")


def generate(client, body, timeout):
    inputs = set()
    for field in REFERENCE_FIELDS:
        value = body.get(field)
        inputs.update(value if isinstance(value, list) else ([value] if value else []))
    # The live Muse upstream requires seconds as a string on the wire.
    request_body = dict(body, seconds=str(body["seconds"]))
    code, response = client.post_with_status(VIDEO_ENDPOINT, json=request_body, timeout=120)
    if not isinstance(response, dict):
        raise AimaxhugError("提交响应格式无效；请核查服务端任务后再决定是否重试")
    task_id = task_id_of(response)
    if task_id:
        log(f"TASK_ID: {task_id}")
    if not 200 <= code < 300:
        if not task_id:
            raise AimaxhugError(message_of(response), code)
        log(f"HTTP {code} 响应含任务 ID，继续查询原任务。")
    else:
        result = inspect(response, task_id, inputs)
        if result["state"] == "completed":
            return result
    if not task_id:
        raise AimaxhugError("提交响应没有任务 ID；请核查服务端任务后再决定是否重试")
    return wait(client, task_id, timeout, inputs)


def emit(result, as_json):
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    else:
        print(f"状态: {result['state']}")
        for field in ("model", "task_id", "video_url", "message"):
            if result.get(field):
                print(f"{field}: {result[field]}")
        if result.get("local_path"):
            print(f"VIDEO_SAVED: {result['local_path']}")
        if result.get("request_preview"):
            print(json.dumps(result["request_preview"], ensure_ascii=False, indent=2))
        reference = result.get("preflight", {}).get("reference_video")
        if reference:
            print(f"参考视频实测: {reference['source_duration_seconds']:.6f} 秒；"
                  f"目标总时长: {reference['requested_seconds']} 秒；"
                  f"可续写余量: {reference['available_continuation_seconds']:.6f} 秒；"
                  f"建议源视频 ≤{reference['recommended_max_source_seconds']} 秒")


def user_menu():
    """A user-facing menu; API details remain in --json and run --help."""
    seconds = "、".join(map(str, SECONDS))
    return (
        "**🎬 Muse 视频创作**\n\n"
        "| 想设置什么 | 可以怎么选 |\n"
        "| :--- | :--- |\n"
        "| ✍️ 画面内容 | 描述场景、人物动作和台词，**这是必填项** |\n"
        f"| ⏱️ 视频时长 | **默认 5 秒**；可选 {seconds} 秒，推荐 5–40 秒 |\n"
        "| 🖼️ 画面比例 | **横屏 16:9**、竖屏 9:16、方形 1:1、横幅 4:3、竖幅 3:4 |\n"
        "| 🔊 人物声音 | **正常说话**，或只做口型、不出声；环境音和背景音乐保留 |\n"
        "| 🎥 镜头方式 | **由 AI 安排**，也可以选推进、环绕、跟拍、固定、向左移动 |\n"
        "| 📎 参考素材 | 可选：参考图片（最多 4 张）、开头画面、结尾画面，或用于续写的视频 |\n"
        "| 🚫 避免内容 | 可选：例如不要字幕、不要模糊、不要多余人物 |\n\n"
        "告诉我想拍什么、做多少秒；有参考图片或视频，直接发给我。其他设置可以交给我。"
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Muse Video Pro 视频生成 CLI")
    sub = parser.add_subparsers(dest="command")
    models = sub.add_parser("list-models", help="展示中文创作菜单；--json 供 AI 核对技术参数")
    models.add_argument("--json", action="store_true")
    run = sub.add_parser("run", help="生成视频；有 video_url 时先检测源视频时长")
    run.add_argument("--model", choices=(MODEL,), default=MODEL)
    run.add_argument("--prompt", required=True, help="必填，不截断提示词")
    run.add_argument("--aspect-ratio", "--aspect_ratio", "--ratio", dest="aspect_ratio", choices=RATIOS, default="16:9")
    run.add_argument("--seconds", type=int, choices=SECONDS, default=5, help="目标视频总秒数；续写时包含源视频时长；默认 5，推荐 5–40")
    run.add_argument("--camera-motion", "--camera_motion", help="运镜方式，例如 " + " / ".join(CAMERA_MOTIONS))
    run.add_argument("--negative-prompt", "--negative_prompt", help="负面提示词")
    run.add_argument("--input-reference", "--input_reference", help="首帧 URL 字符串")
    run.add_argument("--last-frame", "--last_frame", help="尾帧 URL 字符串")
    run.add_argument("--images", nargs="+", help="最多 4 张参考图 URL 或 Base64")
    run.add_argument("--video-url", "--video_url", help="续写源视频 URL；目标总时长至少 20 秒；源视频必须更短，建议 ≤目标总时长−2 秒")
    run.add_argument("--mute-voice", "--mute_voice", type=boolean, nargs="?", const=True, default=False,
                     help="默认 false；true 时人物保留口型但禁配音，保留 SFX/Foley/BGM；可只写 --mute-voice")
    run.add_argument("--ffprobe", default="ffprobe", help="参考视频检测用的 ffprobe 路径，默认从 PATH 查找")
    run.add_argument("--dry-run", action="store_true", help="校验并预览，不提交、不需要密钥；有 video_url 时会联网检测素材")
    status = sub.add_parser("status", help="查询已有任务")
    status.add_argument("--model", choices=(MODEL,), default=MODEL)
    status.add_argument("--task-id", required=True)
    status.add_argument("--wait", action="store_true")
    for command in (run, status):
        command.add_argument("--poll-timeout", type=positive_seconds, default=DEFAULT_POLL_TIMEOUT)
        command.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "list-models":
        result = {"model": MODEL, "aspect_ratio": list(RATIOS), "seconds": list(SECONDS),
                  "default_seconds": 5, "recommended_seconds": [5, 8, 10, 20, 30, 40],
                  "camera_motion_examples": list(CAMERA_MOTIONS), "max_images": 4,
                  "mute_voice_default": False, "reference_min_output_seconds": 20,
                  "reference_source_must_be_shorter_than_output": True,
                  "reference_seconds_meaning": "target_total_duration_after_continuation",
                  "recommended_source_headroom_seconds": 2}
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else user_menu())
        return 0
    if not args.command:
        parser.print_help()
        return 0
    try:
        if args.command == "run":
            body = build_body(args)
            checks = preflight(body, args.ffprobe)
            reference = checks.get("reference_video")
            if reference:
                log(f"参考视频实测 {reference['source_duration_seconds']:.6f} 秒，"
                    f"续写目标总时长 {reference['requested_seconds']} 秒，"
                    f"可续写余量 {reference['available_continuation_seconds']:.6f} 秒。")
            for warning in checks["warnings"]:
                log(f"提示: {warning}")
            if args.dry_run:
                emit({"state": "validated", "submitted": False, "request_preview": body,
                      "preflight": checks}, args.json)
                return 0
            result = generate(AimaxhugClient(), body, args.poll_timeout)
            result.update(seconds=body["seconds"], aspect_ratio=body["aspect_ratio"], preflight=checks)
        else:
            task_id = args.task_id.strip()
            if not task_id:
                raise ValueError("task-id 不能为空")
            log(f"TASK_ID: {task_id}")
            client = AimaxhugClient()
            result = wait(client, task_id, args.poll_timeout) if args.wait else query(client, task_id)
        if result["state"] == "completed":
            from shared_download import download_to_local, env_save_dir
            save_dir = env_save_dir()
            if save_dir:
                result["local_path"] = download_to_local(result["video_url"], save_dir, 1, default_ext=".mp4", timeout=300) or ""
        emit(result, args.json)
        return 0
    except (ValueError, AimaxhugError, OSError) as exc:
        emit({"state": "failed", "message": str(exc)}, args.json)
        return 1
    except KeyboardInterrupt:
        log("已中断本地等待；服务端任务不会取消，请用 TASK_ID 继续查询。")
        return 130


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    sys.exit(main())
