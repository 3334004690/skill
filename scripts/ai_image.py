#!/usr/bin/env python3
"""Generate images from text or edit existing images using Aimaxhug API.

## AGENT INSTRUCTIONS — READ FIRST
- Default flow: ALWAYS use `run` (generate + show result).
- Before generating, show `list-models` so user can choose model/params.
- Do NOT pick a model for the user — show the table and let them choose.
- gpt-image-2 does NOT support --resolution (auto-mapped from proportion).
- Multi-image (--count > 1): tasks run in parallel automatically.
  If user specifies --styles, use those; otherwise auto-generate different styles.
  Do NOT run multi-image tasks sequentially — use --count and let the script parallelize.

Subcommands:
    run           Generate images — DEFAULT
    list-models   Show supported models and parameter constraints

Usage:
    # Single image
    python ai_image.py run --model nano-banana --prompt "..." --proportion 16:9 --resolution 2k

    # Multi-image with auto styles (runs in parallel)
    python ai_image.py run --model nano-banana --prompt "一只猫" --count 4 --proportion 16:9 --resolution 2k

    # Multi-image with explicit styles
    python ai_image.py run --model nano-banana --prompt "一只猫" --count 3 --proportion 16:9 --styles 写实 卡通 赛博朋克

    # Image-to-image
    python ai_image.py run --model nano-banana-pro --prompt "..." --input-images photo.jpg --proportion 16:9

    # gpt-image-2 (no --resolution)
    python ai_image.py run --model gpt-image-2 --prompt "..." --proportion 9:16

    # List models
    python ai_image.py list-models
"""

import argparse
import json as json_mod
import mimetypes
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared.client import AimaxhugClient, AimaxhugError

GENERATE_ENDPOINT = "/api/v1/imageToImage"
UPLOAD_ENDPOINT = "/api/v2/upload/file"

ALL_PROPORTIONS = [
    "1:1", "9:16", "16:9", "2:3", "3:2",
    "3:4", "4:3", "4:5", "5:4", "21:9",
]

# Auto-generated styles for multi-image when user doesn't specify styles
AUTO_STYLES = [
    "写实风格",
    "卡通风格",
    "油画风格",
    "赛博朋克风格",
    "水彩画风格",
    "素描风格",
    "3D渲染风格",
    "浮世绘风格",
    "蒸汽波风格",
    "极简主义风格",
    "复古胶片风格",
    "未来主义风格",
]

# ---------------------------------------------------------------------------
# Model registry
# Each model has its OWN proportions and resolution config — fully independent.
# resolution_mode:
#   "manual" — user picks from resolutions list
#   "auto"   — auto-mapped from proportion, --resolution not accepted
# ---------------------------------------------------------------------------

MODELS = {
    "nano-banana": {
        "api_model": "gemini-3.1-flash-image-preview",
        "name": "Nano Banana",
        "desc": "标准图像生成，速度快、性价比高",
        "proportions": ["1:1", "9:16", "16:9", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "21:9"],
        "resolution_mode": "manual",
        "resolutions": ["1k", "2k", "4k"],
        "default_resolution": "1k",
    },
    "nano-banana-pro": {
        "api_model": "gemini-3-pro-image-preview",
        "name": "Nano Banana Pro",
        "desc": "高质量图像生成，Nano Banana 上位替代",
        "proportions": ["1:1", "9:16", "16:9", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "21:9"],
        "resolution_mode": "manual",
        "resolutions": ["1k", "2k", "4k"],
        "default_resolution": "1k",
    },
    "doubao-seedream-5-0-260128": {
        "api_model": "doubao-seedream-5-0-260128",
        "name": "Seedream 5.0",
        "desc": "高品质图像生成，细节丰富、色彩鲜艳",
        "proportions": ["1:1", "9:16", "16:9", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "21:9"],
        "resolution_mode": "manual",
        "resolutions": ["1k", "2k", "4k"],
        "default_resolution": "1k",
    },
    "gpt-image-2": {
        "api_model": "gpt-image-2",
        "name": "gpt-image-2",
        "desc": "照片级写实、精准构图、艺术风格",
        "proportions": ["1:1", "9:16", "16:9", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "21:9"],
        "resolution_mode": "auto",
        # ⚠️ gpt-image-2 分辨率由比例自动决定：
        #    1:1 → 4k    9:16 → 4k    16:9 → 4k
        "resolution_map": {"1:1": "4k", "9:16": "4k", "16:9": "4k"},
        "default_resolution": "4k",
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


def show_progress_single():
    """Fake progress bar for single image generation."""
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


def build_body(model, prompt, proportion, resolution, input_data):
    """Build request body with all parameter handling."""
    body = {
        "model": model["api_model"],
        "prompt": prompt.strip(),
    }

    if input_data:
        body["original_image"] = input_data

    if proportion:
        body["proportion"] = proportion

    # Resolution
    if model["resolution_mode"] == "manual":
        r = resolution or model["default_resolution"]
        body["resolution"] = r
    elif model["resolution_mode"] == "auto":
        rmap = model.get("resolution_map", {})
        if proportion and proportion in rmap:
            body["resolution"] = rmap[proportion]
        else:
            body["resolution"] = model["default_resolution"]

    return body


def generate_one(client, model, body, index, total):
    """Generate a single image. Returns dict with success/image_url/prompt."""
    try:
        data = client.post(GENERATE_ENDPOINT, json=body)
    except AimaxhugError as e:
        return {"success": False, "error": str(e), "index": index}

    url = data.get("data", {}).get("imageUrl", "")
    if not url:
        return {"success": False, "error": "返回数据中没有 imageUrl", "index": index}

    # Extract a short style label for display
    prompt_text = body.get("prompt", "")
    style_label = ""
    for s in AUTO_STYLES:
        if prompt_text.endswith(s):
            style_label = s
            break

    return {
        "success": True,
        "image_url": url,
        "prompt": prompt_text,
        "style_label": style_label,
        "index": index,
    }


# ---------------------------------------------------------------------------
# Subcommand: list-models
# ---------------------------------------------------------------------------

def cmd_list_models(args):
    """Print model table with all parameters — per-model proportions."""
    print()
    print("=" * 100)
    print("📷 可用生图模型 — 请选择并告诉我以下参数")
    print("=" * 100)

    header = f"{'模型名称':<18} {'模型Key':<20} {'分辨率':<28} {'支持比例'}"
    sep = "─" * 100
    print(f"\n{header}")
    print(sep)

    for key, m in MODELS.items():
        if m["resolution_mode"] == "manual":
            res = f"✅ 手动: {' / '.join(m['resolutions'])}"
        else:
            rmap = m.get("resolution_map", {})
            rules = "  ".join(f"{k}→{v}" for k, v in rmap.items())
            res = f"⚠️ 自动: {rules}"

        props = " / ".join(m["proportions"])
        print(f"{m['name']:<18} {key:<20} {res:<28} {props}")

    print(sep)
    print()

    for key, m in MODELS.items():
        print(f"  [{key}] {m['name']} — {m['desc']}")
        print(f"      支持比例 ({len(m['proportions'])}种): {' / '.join(m['proportions'])}")
        if m["resolution_mode"] == "manual":
            print(f"      分辨率: {' / '.join(m['resolutions'])}（手动选择，默认 {m['default_resolution']}）")
        else:
            rmap = m.get("resolution_map", {})
            rules = "  ".join(f"{k}→{v}" for k, v in rmap.items())
            print(f"      分辨率: 不支持手动选择，由比例自动决定")
            print(f"      映射规则: {rules}")
        print()

    print("请选择模型并告诉我：提示词、比例、分辨率（如适用）")
    print("=" * 100)
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
    p.add_argument("--count", type=int, default=1,
                   help="生成数量（默认 1，>1 时自动并行 + 不同风格）")
    p.add_argument("--styles", nargs="+", default=None,
                   help="自定义风格列表（空格分隔），如: 写实 卡通 油画")
    p.add_argument("--json", action="store_true",
                   help="以 JSON 格式输出结果")
    return p


def cmd_run(args):
    """Generate image(s) and print result. Multi-image runs in parallel."""
    # Validate model
    model = MODELS.get(args.model)
    if not model:
        print(f"Error: 未知模型: {args.model}", file=sys.stderr)
        sys.exit(1)

    model_props = model.get("proportions", ALL_PROPORTIONS)
    proportion = args.proportion
    count = args.count or 1

    # Cap count at 14
    MAX_COUNT = 14
    if count > MAX_COUNT:
        print(f"Error: 最多一次性生成 {MAX_COUNT} 张，当前设置 {count}", file=sys.stderr)
        sys.exit(1)

    # Validate proportion
    if proportion and proportion not in model_props:
        print(f"Error: {model['name']} 不支持比例 {proportion}", file=sys.stderr)
        print(f"   该模型支持: {' / '.join(model_props)}", file=sys.stderr)
        sys.exit(1)

    # Validate resolution for manual models
    if model["resolution_mode"] == "manual":
        r = args.resolution or model["default_resolution"]
        if r not in model["resolutions"]:
            print(f"Error: 不支持的分辨率: {r}", file=sys.stderr)
            print(f"   可选: {', '.join(model['resolutions'])}", file=sys.stderr)
            sys.exit(1)
    elif args.resolution:
        print(f"Warning: {model['name']} 不支持手动选择分辨率，忽略 --resolution", file=sys.stderr)

    # Upload input images once (shared across all parallel tasks)
    input_data = None
    if args.input_images:
        input_data = []
        for path in args.input_images:
            data = upload_file(AimaxhugClient(), path)
            input_data.append(data)

    # --- Build prompts for each image ---
    styles = args.styles
    if count == 1:
        # Single image — use original prompt
        prompts = [args.prompt]
    elif styles:
        # User-specified styles — replace prompt for each
        prompts = []
        for i in range(count):
            s = styles[i % len(styles)]
            prompts.append(f"{args.prompt}，{s}")
    else:
        # Auto-generate different styles
        prompts = [args.prompt]
        for i in range(1, count):
            s = AUTO_STYLES[(i - 1) % len(AUTO_STYLES)]
            prompts.append(f"{args.prompt}，{s}")

    # --- Build request bodies ---
    client = AimaxhugClient()
    bodies = []
    for prompt in prompts:
        body = build_body(model, prompt, proportion, args.resolution, input_data)
        bodies.append(body)

    # --- Execute ---
    if count == 1:
        # Single: show fake progress bar, generate, display
        print(f"🚀 正在使用 {model['name']} 生成...", file=sys.stderr)
        show_progress_single()
        result = generate_one(client, model, bodies[0], 1, 1)
        _display_results([(0, result)], model, proportion, input_data, args.json)
    else:
        # Multi: parallel execution
        print(f"🚀 正在使用 {model['name']} 并行生成 {count} 张不同风格图片...", file=sys.stderr)
        results = []
        with ThreadPoolExecutor(max_workers=min(count, 10)) as pool:
            futures = {
                pool.submit(generate_one, client, model, body, i + 1, count): i
                for i, body in enumerate(bodies)
            }
            for future in as_completed(futures):
                idx = futures[future]
                r = future.result()
                results.append((idx, r))
                if r["success"]:
                    label = r.get("style_label") or f"图{idx + 1}"
                    print(f"  ✅ [{idx + 1}/{count}] {label} 完成", file=sys.stderr)
                else:
                    print(f"  ❌ [{idx + 1}/{count}] 失败: {r.get('error')}", file=sys.stderr)

        results.sort(key=lambda x: x[0])
        _display_results(results, model, proportion, input_data, args.json)


def _display_results(results, model, proportion, input_data, json_output):
    """Display generation results — single or multi-image."""
    successes = [r for _, r in results if r["success"]]
    failures = [r for _, r in results if not r["success"]]
    total = len(results)

    if json_output:
        # JSON output: list of all results
        output = []
        for _, r in results:
            output.append({
                "success": r["success"],
                "image_url": r.get("image_url", ""),
                "error": r.get("error", ""),
                "prompt": r.get("prompt", ""),
                "style_label": r.get("style_label", ""),
                "model": model["name"],
                "api_model": model["api_model"],
                "proportion": proportion,
                "resolution": model.get("default_resolution", ""),
            })
        print(json_mod.dumps(output, indent=2, ensure_ascii=False))
        return

    # Text output
    print()
    if total == 1 and successes:
        r = successes[0]
        print("✅ 生成成功！")
        print("━" * 40)
        print(f"  📍 {r['image_url']}")
        print(f"  🖼️  ![](r['image_url'])")
        print("━" * 40)
        print(f"  📐 比例: {proportion or '默认'}")
        print(f"  🤖 模型: {model['name']} ({model['api_model']})")
    elif successes:
        print(f"✅ 全部生成完成！（共 {total} 张）")
        for i, r in enumerate(successes):
            style_label = r.get("style_label") or f"图{i + 1}"
            print(f"━━━ [{i + 1}/{total}] {style_label} ━━━")
            print(f"  📍 {r['image_url']}")
            print(f"  🖼️  ![](r['image_url'])")
            print()
        print(f"🤖 模型: {model['name']} ({model['api_model']})")
        print(f"📐 比例: {proportion or '默认'}")

    if failures:
        print(f"\n⚠️ {len(failures)} 张生成失败:")
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
        description="AI 图像生成 — 文生图 / 图生图",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="subcommand")

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
