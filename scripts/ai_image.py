#!/usr/bin/env python3
"""Generate images from text or edit existing images using Aimaxhug API.

## AGENT INSTRUCTIONS — READ FIRST
- Default flow: ALWAYS use `run` (generate + show result).
- Before generating, show `list-models` so user can choose model/params.
- Do NOT pick a model for the user — show the table and let them choose.
- gpt-image-2 does NOT support --resolution (auto-mapped from proportion).

Subcommands:
    run           Generate images — DEFAULT
    list-models   Show supported models and parameter constraints

Usage:
    python ai_image.py run --model nano-banana --prompt "..." --proportion 16:9 --resolution 2k
    python ai_image.py run --model nano-banana-pro --prompt "..." --input-images photo.jpg --proportion 16:9
    python ai_image.py run --model gpt-image-2 --prompt "..." --proportion 9:16
    python ai_image.py list-models
"""

import argparse
import json as json_mod
import mimetypes
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared.client import AimaxhugClient, AimaxhugError

GENERATE_ENDPOINT = "/api/v1/imageToImage"
UPLOAD_ENDPOINT = "/api/v2/upload/file"

ALL_PROPORTIONS = [
    "1:1", "9:16", "16:9", "2:3", "3:2",
    "3:4", "4:3", "4:5", "5:4", "21:9",
]

# ---------------------------------------------------------------------------
# Model registry
# resolution_mode:
#   "manual" — user can pick from resolutions list
#   "auto"   — auto-mapped from proportion, --resolution not accepted
# ---------------------------------------------------------------------------

MODELS = {
    "nano-banana": {
        "api_model": "gemini-3-pro-image-preview",
        "name": "Nano Banana",
        "desc": "标准图像生成，速度快、性价比高",
        "resolution_mode": "manual",
        "resolutions": ["1k", "2k", "4k"],
        "default_resolution": "1k",
    },
    "nano-banana-pro": {
        "api_model": "gemini-3.1-flash-image-preview",
        "name": "Nano Banana Pro",
        "desc": "高质量图像生成，Nano Banana 上位替代",
        "resolution_mode": "manual",
        "resolutions": ["1k", "2k", "4k"],
        "default_resolution": "1k",
    },
    "gpt-image-2": {
        "api_model": "gpt-image-2",
        "name": "gpt-image-2",
        "desc": "照片级写实、精准构图、艺术风格",
        "resolution_mode": "auto",
        "resolution_map": {"9:16": "4k", "16:9": "4k", "1:1": "2k"},
        "default_resolution": "1k",
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


def show_progress():
    """Fake progress bar to reassure user during generation."""
    steps = [
        "🎨 分析提示词...",
        "🧠 加载模型权重...",
        "✨ 构思构图...",
        "🎨 渲染细节...",
        "🔍 优化画质...",
    ]
    for i in range(1, 11):
        bar = "█" * i + "░" * (10 - i)
        msg = steps[i // 2] if (i % 2 == 1 and i // 2 < len(steps)) else ""
        print(f"\r   [{bar}] {i*10}%  {msg}", end="", flush=True)
        time.sleep(0.3 + (i * 0.08))
    print()


# ---------------------------------------------------------------------------
# Subcommand: list-models
# ---------------------------------------------------------------------------

def cmd_list_models(args):
    """Print model table with all parameters."""
    print()
    print("=" * 90)
    print("📷 可用生图模型 — 请选择并告诉我以下参数")
    print("=" * 90)

    header = f"{'模型名称':<20} {'模型Key':<22} {'分辨率':<24} {'支持比例'}"
    sep = "─" * 90
    print(f"\n{header}")
    print(sep)

    for key, m in MODELS.items():
        if m["resolution_mode"] == "manual":
            res = f"✅ {' / '.join(m['resolutions'])}"
        else:
            rmap = m.get("resolution_map", {})
            rules = " | ".join(f"{k}→{v}" for k, v in rmap.items())
            res = f"❌ 自动映射: {rules}"

        props = " / ".join(ALL_PROPORTIONS[:5]) + " ..."
        print(f"{m['name']:<20} {key:<22} {res:<24} {props}")

    print(sep)
    print(f"共 {len(MODELS)} 个模型，所有模型支持比例: {' / '.join(ALL_PROPORTIONS)}")
    print()

    for key, m in MODELS.items():
        print(f"  [{key}] {m['name']} — {m['desc']}")
        if m["resolution_mode"] == "manual":
            print(f"      分辨率: {' / '.join(m['resolutions'])}（手动选择）")
        else:
            rmap = m.get("resolution_map", {})
            rules = "  ".join(f"{k}→{v}" for k, v in rmap.items())
            print(f"      分辨率: 不支持手动选，自动映射: {rules}，默认 {m['default_resolution']}")
        print()

    print("请选择模型并告诉我：提示词、比例、分辨率（如适用）")
    print("=" * 90)
    print()


# ---------------------------------------------------------------------------
# Subcommand: run (generate)
# ---------------------------------------------------------------------------

def add_generate_args(p):
    p.add_argument("--model", default="nano-banana",
                   choices=list(MODELS.keys()),
                   help="模型 key（默认: nano-banana）")
    p.add_argument("--prompt", required=True,
                   help="提示词：描述你要生成的图片内容")
    p.add_argument("--proportion", default=None,
                   help="比例，如 16:9、1:1、9:16 等")
    p.add_argument("--resolution", default=None,
                   help="分辨率 1k/2k/4k（仅 nano-banana/pro 有效，gpt-image-2 勿传）")
    p.add_argument("--input-images", nargs="+", default=None,
                   help="本地图片路径，传了=图生图，不传=文生图")
    p.add_argument("--json", action="store_true",
                   help="以 JSON 格式输出结果")
    return p


def cmd_run(args):
    """Generate image(s) and print result."""
    model = MODELS.get(args.model)
    if not model:
        print(f"Error: 未知模型: {args.model}", file=sys.stderr)
        sys.exit(1)

    client = AimaxhugClient()
    proportion = args.proportion

    # Validate proportion
    if proportion and proportion not in ALL_PROPORTIONS:
        print(f"Error: 不支持的比例: {proportion}", file=sys.stderr)
        print(f"   可选: {', '.join(ALL_PROPORTIONS)}", file=sys.stderr)
        sys.exit(1)

    # Upload input images (if any)
    input_data = None
    if args.input_images:
        input_data = []
        for path in args.input_images:
            data = upload_file(client, path)
            input_data.append(data)

    # Build request body
    body = {
        "model": model["api_model"],
        "prompt": args.prompt.strip(),
    }

    if input_data:
        body["original_image"] = input_data
        print(f"📎 参考图: {len(input_data)} 张", file=sys.stderr)

    if proportion:
        body["proportion"] = proportion

    # Resolution
    if model["resolution_mode"] == "manual":
        r = args.resolution or model["default_resolution"]
        if r not in model["resolutions"]:
            print(f"Error: 不支持的分辨率: {r}", file=sys.stderr)
            print(f"   可选: {', '.join(model['resolutions'])}", file=sys.stderr)
            sys.exit(1)
        body["resolution"] = r
    elif model["resolution_mode"] == "auto":
        rmap = model.get("resolution_map", {})
        if proportion and proportion in rmap:
            body["resolution"] = rmap[proportion]
        else:
            body["resolution"] = model["default_resolution"]

    # Progress
    print(f"🚀 正在使用 {model['name']} 生成...", file=sys.stderr)
    show_progress()

    # Generate
    try:
        data = client.post(GENERATE_ENDPOINT, json=body)
    except AimaxhugError as e:
        print(f"\n❌ 生成失败: {e}", file=sys.stderr)
        sys.exit(1)

    url = data.get("data", {}).get("imageUrl", "")
    if not url:
        print(f"\n❌ 生成失败: 返回数据中没有 imageUrl", file=sys.stderr)
        sys.exit(1)

    result = {
        "success": True,
        "image_url": url,
        "model": model["name"],
        "api_model": model["api_model"],
        "proportion": proportion,
        "resolution": body.get("resolution"),
        "prompt": args.prompt,
    }

    if args.json:
        print(json_mod.dumps(result, indent=2, ensure_ascii=False))
    else:
        print()
        print("✅ 生成成功！")
        print("━" * 40)
        print(f"  📍 [点击查看生成的图片]({url})")
        print(f"  🖼️  ![生成结果]({url})")
        print("━" * 40)
        print(f"  📐 比例: {proportion or '默认'}")
        print(f"  🔍 分辨率: {result.get('resolution', 'N/A')}")
        print(f"  🤖 模型: {model['name']} ({model['api_model']})")

        if input_data:
            print(f"\n📎 参考图:")
            for i, img in enumerate(input_data):
                print(f"  [{i+1}] [点击预览]({img['tmp_url']})")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="AI 图像生成 — 文生图 / 图生图",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = sub = parser.add_subparsers(dest="subcommand")

    # list-models
    sub.add_parser("list-models", help="列出所有可用模型及参数")

    # run
    p_run = sub.add_parser("run", help="生成图片（默认）")
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
