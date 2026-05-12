#!/usr/bin/env python3
"""Generate videos using Aimaxhug API (Kling / Vidu).

三种模式：
  文生视频      — 仅传 --prompt（不传 --input-images）
  图生视频      — 传 --prompt + --input-images（图片文件）
  视频生视频    — 传 --prompt + --input-images（视频文件，消耗巨大，谨慎使用）

## AGENT INSTRUCTIONS — READ FIRST
- Default flow: ALWAYS use `run` (generate + show result).
- Before generating, show `list-models` so user can choose model/params.
- Do NOT pick a model for the user — show the table and let them choose.
- Multi-video (--count > 1): tasks run in parallel automatically.
  Do NOT run multi-video tasks sequentially — use --count and let the script parallelize.
- 视频生视频消耗巨大，务必提前告知用户并确认。
  ️检测到输入文件中有视频时自动弹出警告，不要自行决定。

Subcommands:
    run           Generate videos — DEFAULT
    list-models   Show supported models and parameter constraints

Usage:
    # 文生视频
    python ai_video.py run --model kling --prompt "..." --proportion 16:9 --resolution 720p

    # 图生视频
    python ai_video.py run --model vidu --prompt "..." --input-images photo.jpg --proportion 9:16

    # 视频生视频（消耗巨大）
    python ai_video.py run --model kling --prompt "..." --input-images video.mp4 --proportion 16:9

    # Multi-video parallel
    python ai_video.py run --model kling --prompt "..." --count 3 --proportion 16:9

    # List models
    python ai_video.py list-models
"""

import argparse
import json as json_mod
import mimetypes
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared.client import AimaxhugClient, AimaxhugError

VIDEO_ENDPOINT = "/api/v2/video-tencentcloud/vidu-kling-seedance"
UPLOAD_ENDPOINT = "/api/v2/upload/file"

AUTO_PROMPTS = [
    " cinematic quality",
    " dramatic lighting",
    " close-up shot",
    " wide angle view",
    " slow motion effect",
]

# ---------------------------------------------------------------------------
# Model registry
# ---------------------------------------------------------------------------

VIDEO_MODELS = {
    "kling": {
        "api_model": "kling",
        "name": "可灵 (Kling)",
        "desc": "快手可灵 AI 视频生成，支持 1080p/4k 分辨率",
        "proportions": ["16:9", "9:16", "1:1"],
        "durations": ["5", "10", "15"],
        "resolutions": ["720p", "1080p", "4k"],
        "default_duration": "5",
        "default_resolution": "720p",
    },
    "vidu": {
        "api_model": "vidu",
        "name": "Vidu",
        "desc": "Vidu AI 视频生成，支持首尾帧控制",
        "proportions": ["16:9", "9:16", "1:1"],
        "durations": ["5", "10", "15"],
        "resolutions": ["720p", "1080p"],
        "default_duration": "5",
        "default_resolution": "720p",
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def upload_file(client, file_path):
    """Upload a single file and return data dict {tmp_url, name, type, size}."""
    path = Path(file_path)
    if not path.exists():
        print(f"Error: 文件不存在: {file_path}", file=sys.stderr)
        sys.exit(1)

    mime_type, _ = mimetypes.guess_type(path.name)
    if not mime_type:
        mime_type = "application/octet-stream"

    print(f"📤 上传中: {path.name}...", file=sys.stderr)
    data = client.post_file(UPLOAD_ENDPOINT, str(path), mime_type)
    print(f"   ✅ URL: [点击预览]({data['tmp_url']})", file=sys.stderr)
    return data


def build_body(model, prompt, proportion, duration, resolution, input_data):
    """Build request body for video generation."""
    body = {
        "prompt": prompt.strip(),
        "model": model["api_model"],
    }

    if input_data:
        body["images"] = input_data

    body["duration"] = duration or model["default_duration"]
    body["aspect_ratio"] = proportion or "16:9"
    body["resolution"] = resolution or model["default_resolution"]

    return body


def generate_one(client, model, body, index, total):
    """Generate a single video. Returns dict with success/video_url/prompt."""
    try:
        data = client.post(VIDEO_ENDPOINT, json=body)
    except AimaxhugError as e:
        return {"success": False, "error": str(e), "index": index}

    biz_code = data.get("code") or data.get("status")
    if biz_code and biz_code != 200:
        return {
            "success": False,
            "error": data.get("message", f"后端返回错误码 {biz_code}"),
            "index": index,
        }

    video_url = data.get("data", {}).get("url") or data.get("data", {}).get("videoUrl", "")
    if not video_url:
        return {"success": False, "error": "返回数据中没有视频地址", "index": index}

    print(f"  ✅ [{index}/{total}] 生成完成", file=sys.stderr)

    return {
        "success": True,
        "video_url": video_url,
        "prompt": body.get("prompt", ""),
        "index": index,
    }


# ---------------------------------------------------------------------------
# Subcommand: list-models
# ---------------------------------------------------------------------------


def cmd_list_models(args):
    """Print video model table with all parameters."""
    print()
    print("=" * 100)
    print("🎬 可用视频生成模型 — 请选择并告诉我以下参数")
    print("=" * 100)

    header = f"{'模型名称':<20} {'模型Key':<10} {'分辨率':<24} {'时长':<16} {'支持比例'}"
    sep = "─" * 100
    print(f"\n{header}")
    print(sep)

    for key, m in VIDEO_MODELS.items():
        res = " / ".join(m["resolutions"])
        dur = " / ".join(f"{d}秒" for d in m["durations"])
        props = " / ".join(m["proportions"])
        print(f"{m['name']:<20} {key:<10} {res:<24} {dur:<16} {props}")

    print(sep)
    print()

    for key, m in VIDEO_MODELS.items():
        print(f"  [{key}] {m['name']} — {m['desc']}")
        print(f"      支持比例: {' / '.join(m['proportions'])}")
        print(f"      时长: {' / '.join(f'{d}秒' for d in m['durations'])}（默认 {m['default_duration']}秒）")
        print(f"      分辨率: {' / '.join(m['resolutions'])}（默认 {m['default_resolution']}）")
        if m["api_model"] == "vidu":
            print(f"      ⚠️  4k 分辨率仅可灵支持，Vidu 不支持")
        print(f"      ⚠️  传入参考素材（图生视频）时不支持 15 秒，仅 5-10 秒")
        print()

    print("支持三种模式:")
    print("  文生视频   — 仅传提示词（默认）")
    print("  图生视频   — 传提示词 + 参考图片")
    print("  视频生视频 — 传提示词 + 参考视频（⚠️ 消耗巨大，谨慎使用）")
    print()
    print("请选择模型并告诉我：提示词、模式、比例、时长、分辨率（如适用）")
    print("=" * 100)
    print()


# ---------------------------------------------------------------------------
# Subcommand: run (generate)
# ---------------------------------------------------------------------------


def add_generate_args(p):
    p.add_argument("--model", default="kling",
                   choices=list(VIDEO_MODELS.keys()),
                   help="模型 key（默认: kling）")
    p.add_argument("--prompt", required=True,
                   help="提示词：描述你要生成的视频内容")
    p.add_argument("--proportion", default=None,
                   help="画面比例，如 16:9、9:16、1:1 等")
    p.add_argument("--duration", default=None,
                   help="视频时长: 5、10、15（秒）")
    p.add_argument("--resolution", default=None,
                   help="分辨率: 720p/1080p/4k")
    p.add_argument("--input-images", nargs="+", default=None,
                   help="参考素材路径（传图=图生视频，传视频=视频生视频，不传=文生视频）")
    p.add_argument("--count", type=int, default=1,
                   help="生成数量（默认 1，>1 时自动并行）")
    p.add_argument("--json", action="store_true",
                   help="以 JSON 格式输出结果")
    return p


def cmd_run(args):
    """Generate video(s) and print result. Multi-video runs in parallel."""
    model = VIDEO_MODELS.get(args.model)
    if not model:
        print(f"Error: 未知模型: {args.model}", file=sys.stderr)
        sys.exit(1)

    proportion = args.proportion
    duration = args.duration
    resolution = args.resolution
    count = args.count or 1

    MAX_COUNT = 5
    if count > MAX_COUNT:
        print(f"Error: 最多一次性生成 {MAX_COUNT} 个视频，当前设置 {count}", file=sys.stderr)
        sys.exit(1)

    model_props = model.get("proportions")
    if proportion and proportion not in model_props:
        print(f"Error: {model['name']} 不支持比例 {proportion}", file=sys.stderr)
        print(f"   该模型支持: {' / '.join(model_props)}", file=sys.stderr)
        sys.exit(1)

    if duration and duration not in model["durations"]:
        print(f"Error: {model['name']} 不支持的时长: {duration}秒", file=sys.stderr)
        print(f"   可选: {' / '.join(f'{d}秒' for d in model['durations'])}", file=sys.stderr)
        sys.exit(1)

    if resolution and resolution not in model["resolutions"]:
        print(f"Error: {model['name']} 不支持的分辨率: {resolution}", file=sys.stderr)
        print(f"   可选: {' / '.join(model['resolutions'])}", file=sys.stderr)
        sys.exit(1)

    # --- Compatibility warnings (not blocking, but inform user) ---
    has_input_images = bool(args.input_images)
    if has_input_images and duration == "15":
        print(f"⚠️ 提示: {model['name']} 传入参考素材时不支持 15 秒时长，仅支持 5-10 秒。", file=sys.stderr)
        print(f"   当前仍按 15 秒请求，如失败请换用 5 秒或 10 秒。", file=sys.stderr)
    if model["api_model"] == "vidu" and resolution == "4k":
        print(f"⚠️ 提示: Vidu 不支持 4k 分辨率，仅支持 720p / 1080p。", file=sys.stderr)
        print(f"   当前仍按 4k 请求，如失败请换用 720p 或 1080p。", file=sys.stderr)

    input_data = None
    has_video_ref = False
    if args.input_images:
        input_data = []
        for path in args.input_images:
            data = upload_file(AimaxhugClient(), path)
            input_data.append(data)
            if data.get("type", "").startswith("video/"):
                has_video_ref = True

    # --- 视频生视频警告 ---
    if has_video_ref:
        print(file=sys.stderr)
        print("⚠️ ⚠️ ⚠️  警告：视频生视频模式  ⚠️ ⚠️ ⚠️", file=sys.stderr)
        print("   检测到输入文件中包含视频，将使用「视频生视频」模式。", file=sys.stderr)
        print("   此模式消耗巨大，生成时间可能显著延长。", file=sys.stderr)
        print("   请确认是否继续。", file=sys.stderr)
        print(file=sys.stderr)

    if count == 1:
        prompts = [args.prompt]
    else:
        prompts = [args.prompt]
        for i in range(1, count):
            s = AUTO_PROMPTS[(i - 1) % len(AUTO_PROMPTS)]
            prompts.append(f"{args.prompt}{s}")

    client = AimaxhugClient()
    bodies = []
    for prompt in prompts:
        body = build_body(model, prompt, proportion, duration, resolution, input_data)
        bodies.append(body)

    if count == 1:
        mode_label = "文生视频" if not input_data else ("视频生视频" if has_video_ref else "图生视频")
        print(f"🎬 正在使用 {model['name']} 进行{mode_label}（通常需要 1-3 分钟）", file=sys.stderr)
        result = generate_one(client, model, bodies[0], 1, 1)
        _display_results([(0, result)], model, proportion, duration, resolution, input_data, args.json)
    else:
        mode_label = "文生视频" if not input_data else ("视频生视频" if has_video_ref else "图生视频")
        print(f"🎬 正在使用 {model['name']} 并行生成 {count} 个{mode_label}...", file=sys.stderr)
        results = []
        with ThreadPoolExecutor(max_workers=min(count, 5)) as pool:
            futures = {
                pool.submit(generate_one, client, model, body, i + 1, count): i
                for i, body in enumerate(bodies)
            }
            for future in as_completed(futures):
                idx = futures[future]
                r = future.result()
                results.append((idx, r))
                if r["success"]:
                    print(f"  ✅ [{idx + 1}/{count}] 完成", file=sys.stderr)
                else:
                    print(f"  ❌ [{idx + 1}/{count}] 失败: {r.get('error')}", file=sys.stderr)

        results.sort(key=lambda x: x[0])
        _display_results(results, model, proportion, duration, resolution, input_data, args.json)


def _display_results(results, model, proportion, duration, resolution, input_data, json_output):
    """Display generation results."""
    successes = [r for _, r in results if r["success"]]
    failures = [r for _, r in results if not r["success"]]
    total = len(results)

    if json_output:
        output = []
        for _, r in results:
            output.append({
                "success": r["success"],
                "video_url": r.get("video_url", ""),
                "error": r.get("error", ""),
                "prompt": r.get("prompt", ""),
                "model": model["name"],
                "api_model": model["api_model"],
                "proportion": proportion,
                "duration": duration or model["default_duration"],
                "resolution": resolution or model["default_resolution"],
            })
        print(json_mod.dumps(output, indent=2, ensure_ascii=False))
        return

    # Text output
    print()
    mode_label = "文生视频"
    if input_data:
        mode_label = "视频生视频" if any(d.get("type", "").startswith("video/") for d in input_data) else "图生视频"

    if total == 1 and successes:
        r = successes[0]
        print("✅ 生成成功！")
        print("━" * 40)
        print(f"  📍 {r['video_url']}")
        print(f"  🎬  ![]({r['video_url']})")
        print("━" * 40)
        print(f"  📐 比例: {proportion or '16:9'}")
        print(f"  ⏱  时长: {duration or model['default_duration']}秒")
        print(f"  🔍 分辨率: {resolution or model['default_resolution']}")
        print(f"  🤖 模型: {model['name']}")
        print(f"  📋 模式: {mode_label}")
    elif successes:
        print(f"✅ 全部生成完成！（共 {total} 个视频）")
        print(f"🤖 模型: {model['name']}")
        print(f"📐 比例: {proportion or '16:9'}")
        print(f"⏱  时长: {duration or model['default_duration']}秒")
        print(f"🔍 分辨率: {resolution or model['default_resolution']}")
        print(f"📋 模式: {mode_label}")
        print()
        for i, r in enumerate(successes):
            print(f"━━━ [{i + 1}/{total}] ━━━")
            print(f"  📍 {r['video_url']}")
            print(f"  🎬  ![]({r['video_url']})")
            print()

    if failures:
        print(f"\n⚠️ {len(failures)} 个视频生成失败:")
        for r in failures:
            print(f"  [{r['index']}] {r.get('error', '未知错误')}")

    if input_data:
        print(f"\n📎 参考图:")
        for i, img in enumerate(input_data):
            print(f"  [{i + 1}] {img['tmp_url']}")
            print(f"      ![]({img['tmp_url']})")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="AI 视频生成 — 文生视频 / 图生视频（可灵 / Vidu）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="subcommand")

    sub.add_parser("list-models", help="列出所有可用视频模型及参数")

    p_run = sub.add_parser("run", help="生成视频（默认）")
    add_generate_args(p_run)

    args = parser.parse_args()

    if args.subcommand == "list-models":
        cmd_list_models(args)
    elif args.subcommand is None or args.subcommand == "run":
        cmd_run(args) if hasattr(args, "prompt") else parser.print_help()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
