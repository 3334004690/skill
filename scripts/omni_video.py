#!/usr/bin/env python3
"""Omni 视频生成专用 CLI，参数详情见 references/omni_video.md。

模型：omni-fast-v2v-no-water / omni-fast / omni-fast-no-water。
配置：环境变量 AIMAXHUG_API_KEY 或技能根目录已有的 .env（沿用 shared_client）。
提交 POST /v1/videos；查询 GET /v1/videos/{model}/{task_id}。
默认每 10 秒轮询一次、最多 1800 秒；HTTP 400 带任务 ID 时继续查询。

命令示例（在技能根目录执行）：
  python scripts/omni_video.py list-models --json
  python scripts/omni_video.py run --model omni-fast --prompt "清晨的海浪" --json
  python scripts/omni_video.py run --model omni-fast-no-water --prompt "镜头环绕" --image-url https://media.example.com/photo.jpg --seconds 10 --json
  python scripts/omni_video.py run --model omni-fast-v2v-no-water --prompt "参考动作" --videos https://media.example.com/a.mp4 https://media.example.com/b.mp4 --dry-run --json
  python scripts/omni_video.py status --model omni-fast --task-id TASK_ID --wait --json

run 必须提供 --model 和非空 --prompt，无本地提示词长度上限。
--ratio / --aspect-ratio：16:9 或 9:16，默认 16:9。
--seconds（字符串）或 --duration（整数）：二选一，默认提交 duration=10。
当前 Gemini 固定输出约 10 秒，请求时长不保证等于实际产物时长。
--image-url：公网 URL 或 data:image Base64；--first-image-url / --last-image-url：公网 URL。
--video / --video-url / --videos：源视频 URL，所有字段合计最多两个，
每个≤8MB、≤1920x1080。--images：最多五张，每张≤8MB，支持 URL 或图片 Base64。
不自动上传本地路径；远程素材大小/分辨率由调用方和接口确认。
--dry-run 不联网、不提交、不需要密钥；--json 的进度写标准错误，结果写标准输出。
"""

import argparse
import base64
import binascii
import ipaddress
import json
import sys
import time
from pathlib import Path
from urllib.parse import quote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shared_client import AimaxhugClient, AimaxhugError
from shared_markers import mark_url
from shared_menus import render_menu


VIDEO_ENDPOINT = "https://apis.aimaxhug.cloud/v1/videos"
MODELS = ("omni-fast-v2v-no-water", "omni-fast", "omni-fast-no-water")
RATIOS = ("16:9", "9:16")
POLL_INTERVAL = 10
MAX_MEDIA_BYTES = 8 * 1024 * 1024
REFERENCE_FIELDS = ("image_url", "first_image_url", "last_image_url", "video", "video_url", "images", "videos")
DONE = {"completed", "complete", "succeeded", "success", "done", "finished"}
FAILED = {"failed", "failure", "error", "cancelled", "canceled", "rejected"}
DURATION_NOTE = "当前 Gemini 固定输出约 10 秒；请求秒数不代表实测产物时长"


def log(message):
    print(message, file=sys.stderr, flush=True)


def positive_seconds(value):
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("须为正整数秒") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("须为正整数秒")
    return number


def reference(value, label, allow_data=False, max_bytes=None):
    if allow_data and value.startswith("data:image/"):
        try:
            metadata, encoded = value.split(",", 1)
            if not metadata.endswith(";base64"):
                raise ValueError("须使用 Base64")
            decoded = base64.b64decode(encoded, validate=True)
            if not decoded:
                raise ValueError("内容为空")
        except (ValueError, binascii.Error) as exc:
            raise ValueError(f"{label} 须为有效 data:image Base64") from exc
        if max_bytes is not None and len(decoded) > max_bytes:
            raise ValueError(f"{label} 每张不得超过 8MB")
        return value
    try:
        parts = urlparse(value)
        host = (parts.hostname or "").lower().rstrip(".")
        port = parts.port
        if (parts.scheme.lower() not in ("http", "https") or not host
                or parts.username is not None or parts.password is not None
                or any(char.isspace() for char in value) or "\\" in value or port == 0):
            raise ValueError("URL 无效")
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            if ("." not in host or host.endswith((".localhost", ".local", ".internal", ".home", ".lan"))
                    or all(char.isdigit() or char == "." for char in host)):
                raise ValueError("需要公网地址")
        else:
            if not address.is_global:
                raise ValueError("需要公网地址")
    except ValueError as exc:
        suffix = " 或 data:image Base64" if allow_data else ""
        raise ValueError(f"{label} 须为公网 HTTP(S) URL{suffix}，不接受本地文件") from exc
    return value


def build_body(args):
    if args.model not in MODELS:
        raise ValueError("未知 Omni 模型")
    if not args.prompt.strip():
        raise ValueError("prompt 不能为空")
    if args.ratio not in RATIOS:
        raise ValueError("aspect_ratio 仅支持 16:9 / 9:16")
    if args.seconds is not None and args.duration is not None:
        raise ValueError("seconds 与 duration 二选一")
    body = {"model": args.model, "prompt": args.prompt.strip(), "aspect_ratio": args.ratio}
    if args.seconds is not None:
        positive_seconds(args.seconds)
        body["seconds"] = args.seconds
    else:
        duration = args.duration if args.duration is not None else 10
        positive_seconds(str(duration))
        body["duration"] = duration
    if len(args.images or []) > 5:
        raise ValueError("images 最多 5 张，每张≤8MB")
    count = len(args.videos or []) + bool(args.video) + bool(args.video_url)
    if count > 2:
        raise ValueError("video / video_url / videos 合计最多 2 个源视频")
    for field in REFERENCE_FIELDS:
        value = getattr(args, field)
        if value is None:
            continue
        allow_data = field in ("image_url", "images")
        for item in value if isinstance(value, list) else [value]:
            reference(item, field, allow_data, MAX_MEDIA_BYTES if field == "images" else None)
        body[field] = value
    return body


def nested(response):
    return response["data"] if isinstance(response.get("data"), dict) else response


def task_id_of(response):
    for node in (nested(response), response):
        for key in ("task_id", "taskId", "id"):
            if isinstance(node.get(key), (str, int)) and not isinstance(node[key], bool):
                return str(node[key])
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
    blocked = ("reference", "input", "source", "request", "origin", "upload", "cover", "poster", "thumb", "preview", "image")
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
                score = 2 if urlparse(node).path.lower().endswith((".mp4", ".webm", ".mov", ".m4v", ".mkv", ".avi")) else 1
                if "video_url" in path or "videourl" in path:
                    score += 2
                candidates.append((score, node))

    visit(response)
    return max(candidates, key=lambda item: item[0])[1] if candidates else ""


def status_endpoint(model, task_id):
    return f"{VIDEO_ENDPOINT}/{quote(model, safe='')}/{quote(task_id, safe='')}"


def inspect(response, model, task_id, inputs=()):
    status = status_of(response)
    if status in FAILED or response.get("success") is False or nested(response).get("success") is False:
        raise AimaxhugError(f"任务失败，task_id={task_id}: {message_of(response)}")
    result = {"state": "processing", "task_id": task_id, "model": model, "api_status": status or "unknown"}
    progress = nested(response).get("progress", response.get("progress"))
    if progress is not None:
        result["progress"] = progress
    url = video_url_of(response, inputs)
    if status in DONE or (url and not status):
        if not url:
            raise AimaxhugError(f"任务完成但没有视频 URL，task_id={task_id}")
        result.update(state="completed", video_url=url, markedUrl=mark_url(url, "video"))
    return result


def query(client, model, task_id, inputs=(), timeout=120):
    code, response = client.get_with_status(status_endpoint(model, task_id), timeout=timeout)
    if not 200 <= code < 300:
        raise AimaxhugError(f"查询失败，task_id={task_id}: {message_of(response)}", code)
    return inspect(response, model, task_id, inputs)


def wait(client, model, task_id, timeout, inputs=()):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            remaining = max(0.1, deadline - time.monotonic())
            result = query(client, model, task_id, inputs, min(120, remaining))
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
    code, response = client.post_with_status(VIDEO_ENDPOINT, json=body, timeout=120)
    task_id = task_id_of(response)
    if task_id:
        log(f"TASK_ID: {task_id}")
    if not 200 <= code < 300:
        if not task_id:
            raise AimaxhugError(message_of(response), code)
        log(f"HTTP {code} 响应含任务 ID，继续查询原任务。")
    else:
        result = inspect(response, body["model"], task_id, inputs)
        if result["state"] == "completed":
            return result
    if not task_id:
        raise AimaxhugError("提交响应没有任务 ID；请核查服务端任务后再决定是否重试")
    return wait(client, body["model"], task_id, timeout, inputs)


def emit(result, as_json):
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    else:
        print(f"状态: {result['state']}")
        for field in ("model", "task_id", "video_url", "local_path", "duration_note", "message"):
            if result.get(field):
                print(f"{field}: {result[field]}")
        if result.get("local_path"):
            print(f"VIDEO_SAVED: {result['local_path']}")
        if result.get("request_preview"):
            print(json.dumps(result["request_preview"], ensure_ascii=False, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Omni 专用视频生成 CLI")
    sub = parser.add_subparsers(dest="command")
    models = sub.add_parser("list-models", help="中文创作菜单；--json 供 AI 核对技术参数")
    models.add_argument("--model", choices=MODELS, help="仅展示所选模型的创作设置")
    models.add_argument("--json", action="store_true")
    run = sub.add_parser("run", help="生成视频；--dry-run 仅离线预检")
    run.add_argument("--model", choices=MODELS, required=True)
    run.add_argument("--prompt", required=True, help="非空，无本地长度上限")
    run.add_argument("--ratio", "--aspect-ratio", dest="ratio", choices=RATIOS, default="16:9")
    timing = run.add_mutually_exclusive_group()
    timing.add_argument("--seconds", help="字符串秒数，实际输出仍约 10 秒")
    timing.add_argument("--duration", type=positive_seconds, help="整数秒数，默认 10")
    for field in REFERENCE_FIELDS:
        run.add_argument("--" + field.replace("_", "-"), nargs="+" if field in ("images", "videos") else None)
    run.add_argument("--dry-run", action="store_true", help="只校验和预览，不联网、不提交")
    status = sub.add_parser("status", help="查询已有任务")
    status.add_argument("--model", choices=MODELS, required=True)
    status.add_argument("--task-id", required=True)
    status.add_argument("--wait", action="store_true", help="持续查询直到完成或失败")
    for command in (run, status):
        command.add_argument("--poll-timeout", type=positive_seconds, default=1800)
        command.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "list-models":
        result = {"models": list(MODELS), "aspect_ratio": list(RATIOS), "default_duration": 10,
                  "duration_note": DURATION_NOTE, "max_images": 5, "max_videos_total": 2,
                  "max_media_bytes": MAX_MEDIA_BYTES, "max_video_resolution": "1920x1080",
                  "reference_fields": list(REFERENCE_FIELDS), "prompt_max_length": None}
        if args.json:
            if args.model:
                result["models"] = [args.model]
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        names = {"omni-fast": "Omni Fast · 标准版", "omni-fast-no-water": "Omni Fast · 无水印版",
                 "omni-fast-v2v-no-water": "Omni Fast · 视频参考无水印版"}
        if not args.model:
            print(render_menu("🎬 选一个 Omni 模型", [(f"{index} · {names[model]}", "可用图片或视频参考，目前成片约 10 秒")
                              for index, model in enumerate(MODELS, 1)],
                              "可以说版本名字或编号；有参考素材直接发给我。", ("创作模型", "可以怎么创作")))
            return 0
        rows = [("✍️ 画面内容", "描述想看到的场景、动作和镜头效果"),
                ("⏱️ 视频时长", "**目前成片约 10 秒**，填写其他秒数不保证改变成片时长"),
                ("🖼️ 画面比例", "**默认横屏 16:9**；也可选竖屏 9:16"),
                ("📎 参考图片", "可选：单张参考图、开头和结尾画面，或多张参考图（最多 5 张）"),
                ("🎞️ 参考视频", "可选：合计最多 2 段；每段不超过 8MB、画面不超过 1920×1080"),
                ("💡 图片大小", "每张参考图片不超过 8MB，素材处理由 AI 完成")]
        print(render_menu("🎬 视频创作 · " + (names[args.model] if args.model else "Omni"), rows,
                          "告诉我想拍什么、横屏还是竖屏；有参考素材直接发给我。"))
        return 0
    if not args.command:
        parser.print_help()
        return 0
    try:
        if args.command == "run":
            body = build_body(args)
            if args.dry_run:
                emit({"state": "validated", "submitted": False, "request_preview": body,
                      "duration_note": DURATION_NOTE}, args.json)
                return 0
            log(DURATION_NOTE)
            result = generate(AimaxhugClient(), body, args.poll_timeout)
            requested = body.get("duration", body.get("seconds"))
            result.update(requested_duration=requested, expected_duration=10, duration_note=DURATION_NOTE)
        else:
            task_id = args.task_id.strip()
            if not task_id:
                raise ValueError("task-id 不能为空")
            log(f"TASK_ID: {task_id}")
            client = AimaxhugClient()
            result = wait(client, args.model, task_id, args.poll_timeout) if args.wait else query(client, args.model, task_id)
        if result["state"] == "completed":
            from shared_download import download_to_local, env_save_dir
            save_dir = env_save_dir()
            if save_dir:
                result["local_path"] = download_to_local(result["video_url"], save_dir, 1, default_ext=".mp4", timeout=300) or ""
        emit(result, args.json)
        return 0
    except (ValueError, argparse.ArgumentTypeError, AimaxhugError, OSError) as exc:
        emit({"state": "failed", "message": str(exc)}, args.json)
        return 1
    except KeyboardInterrupt:
        log("已中断本地等待；服务端任务不会取消，请用已输出的 TASK_ID 继续查询。")
        return 130


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    sys.exit(main())
