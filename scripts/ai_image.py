#!/usr/bin/env python3
"""
AI 图像生成脚本 — AI 直接运行，无需写代码
=========================================

【AI 使用说明】
  当用户要求生图时，按以下步骤操作：
  1. 先确保 .env 中有 AIMAXHUG_API_KEY（没有就问用户要）
  2. 用 --list-models 给用户展示所有可选模型
  3. 根据用户选择，直接执行本脚本并传入参数
  4. 展示返回的图片 URL（可点击超链接）

  支持文生图（不传 --input-images）和图生图（传 --input-images）

用法示例:
  # 查看可用模型
  python scripts/ai_image.py --list-models

  # 文生图 - Nano Banana
  python scripts/ai_image.py --model nano-banana --prompt "一只橘猫" --proportion 16:9 --resolution 2k

  # 图生图 - Nano Banana Pro（自动上传本地图片）
  python scripts/ai_image.py --model nano-banana-pro --prompt "换成都市场景" --input-images photo.jpg --proportion 16:9 --resolution 4k

  # 文生图 - gpt-image-2（不支持手动选分辨率，会自动映射）
  python scripts/ai_image.py --model gpt-image-2 --prompt "赛博朋克城市" --proportion 16:9

  # 图生图 - 多张参考图
  python scripts/ai_image.py --model nano-banana --prompt "把两张图合成" --input-images photo1.jpg photo2.jpg --proportion 1:1 --resolution 4k
"""

import argparse
import json
import mimetypes
import os
import sys
import time
from pathlib import Path

import requests

# 项目根目录：由脚本位置自动定位，不受工作目录影响
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

# Windows GBK 兼容：强制使用 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# ============================================================
# 模型注册表 — 所有模型定义和参数约束集中在这里
# 新增模型只需在这里加一条记录
# ============================================================

MODELS = {
    "nano-banana": {
        "api_model": "gemini-3-pro-image-preview",
        "name": "Nano Banana",
        "desc": "标准图像生成，速度快、性价比高",
        "resolution_mode": "manual",           # manual=用户可自选分辨率
        "resolutions": ["1k", "2k", "4k"],     # 支持的分辨率选项
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
        "resolution_mode": "auto",             # auto=不支持手动选，按比例自动映射
        # ⚠️ gpt-image-2 分辨率映射规则：
        #    9:16 / 16:9 → 4k
        #    1:1         → 2k
        #    其他比例     → 1k
        "resolution_map": {"9:16": "4k", "16:9": "4k", "1:1": "2k"},
        "default_resolution": "1k",
    },
}

# 所有模型共同支持的比例
ALL_PROPORTIONS = [
    "1:1", "9:16", "16:9", "2:3", "3:2",
    "3:4", "4:3", "4:5", "5:4", "21:9",
]

BASE_URL = "https://base-api.aimaxhug.com"
ENDPOINT = f"{BASE_URL}/api/v1/imageToImage"
UPLOAD_URL = f"{BASE_URL}/api/v2/upload/file"


# ============================================================
# 工具函数
# ============================================================

def get_api_key():
    """从 .env 文件读取 API Key（自动定位项目根目录）"""
    key = os.getenv("AIMAXHUG_API_KEY")
    if key:
        return key
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").strip().splitlines():
            if line.startswith("AIMAXHUG_API_KEY="):
                return line.split("=", 1)[1].strip()
    print(f"❌ 未找到 API Key。文件不存在: {ENV_PATH}", file=sys.stderr)
    print("   请在项目根目录创建 .env 文件: echo AIMAXHUG_API_KEY=sk-xxx > .env", file=sys.stderr)
    print("   🔑 前往 https://aimaxhug.com 注册获取 API Key（点击跳转）", file=sys.stderr)
    sys.exit(1)


def upload_file(file_path):
    """上传本地文件，返回完整 data 对象 {tmp_url, name, type, size}"""
    path = Path(file_path)
    if not path.exists():
        print(f"❌ 文件不存在: {file_path}", file=sys.stderr)
        sys.exit(1)

    key = get_api_key()
    print(f"📤 正在上传: {path.name}...", file=sys.stderr)

    # 显式获取 MIME 类型，避免 requests 默认推断出错
    mime_type, _ = mimetypes.guess_type(path.name)
    if not mime_type:
        mime_type = "application/octet-stream"

    with open(path, "rb") as f:
        resp = requests.post(
            UPLOAD_URL,
            headers={"Authorization": f"Bearer {key}"},
            files={"file": (path.name, f, mime_type)},
            timeout=120,
        )

    data = resp.json()
    if resp.status_code != 200 or data.get("status") != 200:
        print(f"❌ 上传失败: {data.get('message', resp.text)}", file=sys.stderr)
        sys.exit(1)

    result = data["data"]
    print(f"   ✅ URL: [点击预览]({result['tmp_url']})", file=sys.stderr)
    return result


# ============================================================
# 假进度条 — 安慰用户，模拟生成过程
# ============================================================

def show_progress():
    """显示假进度条，让用户有等待反馈"""
    steps = [
        "🎨 分析提示词...",
        "🧠 加载模型权重...",
        "✨ 构思构图...",
        "🎨 渲染细节...",
        "🔍 优化画质...",
    ]
    for i in range(1, 11):
        bar = "█" * i + "░" * (10 - i)
        if i % 2 == 1 and i // 2 < len(steps):
            msg = steps[i // 2]
        else:
            msg = ""
        print(f"\r   [{bar}] {i*10}%  {msg}", end="", flush=True)
        time.sleep(0.3 + (i * 0.08))
    print()


# ============================================================
# 生图主函数
# ============================================================

def generate(model_key, prompt, proportion=None, resolution=None, input_images=None):
    """
    生成图片

    参数:
        model_key:   模型 key（nano-banana / nano-banana-pro / gpt-image-2）
        prompt:      提示词
        proportion:  比例，如 "16:9"
        resolution:  分辨率 "1k"/"2k"/"4k"（仅 manual 模型有效，auto 模型会自动映射）
        input_images: 上传的 data 列表 [{tmp_url, name, type, size}]，图生图时传入

    返回: {"success": bool, "image_url": str, ...}
    """
    # 校验模型
    model = MODELS.get(model_key)
    if not model:
        print(f"❌ 未知模型: {model_key}", file=sys.stderr)
        print(f"   可用模型: {', '.join(MODELS.keys())}", file=sys.stderr)
        sys.exit(1)

    # 构建请求体
    body = {
        "model": model["api_model"],
        "prompt": prompt.strip(),
    }

    # 图生图：传入完整 data 对象（所有 4 个字段都必须带）
    if input_images:
        body["original_image"] = input_images
        print(f"📎 参考图: {len(input_images)} 张", file=sys.stderr)

    # 比例
    if proportion:
        if proportion not in ALL_PROPORTIONS:
            print(f"❌ 不支持的比例: {proportion}", file=sys.stderr)
            print(f"   可选: {', '.join(ALL_PROPORTIONS)}", file=sys.stderr)
            sys.exit(1)
        body["proportion"] = proportion

    # 分辨率处理
    if model["resolution_mode"] == "manual":
        # Nano Banana 系列：用户可以选择 1k/2k/4k
        r = resolution or model["default_resolution"]
        if r not in model["resolutions"]:
            print(f"❌ 不支持的分辨率: {r}", file=sys.stderr)
            print(f"   可选: {', '.join(model['resolutions'])}", file=sys.stderr)
            sys.exit(1)
        body["resolution"] = r
    elif model["resolution_mode"] == "auto":
        # gpt-image-2：按比例自动映射，不支持用户选择
        rmap = model.get("resolution_map", {})
        if proportion and proportion in rmap:
            body["resolution"] = rmap[proportion]
        else:
            body["resolution"] = model["default_resolution"]

    # 假进度条
    print(f"🚀 正在使用 {model['name']} 生成...", file=sys.stderr)
    show_progress()

    # 真实请求
    try:
        resp = requests.post(
            ENDPOINT,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {get_api_key()}",
            },
            json=body,
            timeout=120,
        )
    except requests.exceptions.Timeout:
        return {"success": False, "error": "请求超时（>120秒）"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "网络连接失败，请检查网络"}

    # 解析响应
    try:
        data = resp.json()
    except json.JSONDecodeError:
        return {"success": False, "error": f"响应解析失败: {resp.text[:200]}"}

    if resp.status_code != 200:
        return {"success": False, "error": data.get("message", f"HTTP {resp.status_code}")}

    url = data.get("data", {}).get("imageUrl", "")
    if not url:
        return {"success": False, "error": "返回数据中没有 imageUrl"}

    return {
        "success": True,
        "image_url": url,
        "model": model["name"],
        "api_model": model["api_model"],
        "proportion": proportion,
        "resolution": body.get("resolution"),
        "prompt": prompt,
    }


# ============================================================
# 展示函数
# ============================================================

def print_result(result):
    """格式化输出结果，URL 为可点击超链接"""
    if not result["success"]:
        print(f"\n❌ 生成失败: {result['error']}")
        return

    print()
    print("✅ 生成成功！")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  📍 [点击查看生成的图片]({result['image_url']})")
    print(f"  🖼️  ![生成结果]({result['image_url']})")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  📐 比例: {result.get('proportion') or '默认'}")
    print(f"  🔍 分辨率: {result.get('resolution', 'N/A')}")
    print(f"  🤖 模型: {result['model']} ({result['api_model']})")


def print_models():
    """列出所有模型及详细参数 — 表格形式，供用户选择"""
    print()
    print("=" * 90)
    print("📷 可用生图模型 — 请选择并告诉我以下参数")
    print("=" * 90)

    # 表头
    header = f"{'模型名称':<20} {'模型Key':<22} {'分辨率':<24} {'支持比例'}"
    sep = "─" * 90
    print(f"\n{header}")
    print(sep)

    for key, m in MODELS.items():
        name = m["name"]

        if m["resolution_mode"] == "manual":
            res = f"✅ {' / '.join(m['resolutions'])}"
        else:
            rmap = m.get("resolution_map", {})
            rules = " | ".join(f"{k}→{v}" for k, v in rmap.items())
            res = f"❌ 自动映射: {rules}"

        props = " / ".join(ALL_PROPORTIONS[:5])
        props += " ..."

        print(f"{name:<20} {key:<22} {res:<24} {props}")

    print(sep)
    print(f"共 {len(MODELS)} 个模型，所有模型支持比例: {' / '.join(ALL_PROPORTIONS)}")
    print()

    # 详细说明
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


# ============================================================
# CLI 入口 — AI 只需在这里传入参数
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="AI 图像生成 — AI 直接运行，无需写代码",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
【AI 使用说明】
  1. 先确保 .env 中有 AIMAXHUG_API_KEY
  2. 用户选择模型后，直接用 --model 指定
  3. 文生图不传 --input-images，图生图传 --input-images
  4. gpt-image-2 不需要传 --resolution，会自动映射
  5. 所有 URL 会以超链接形式展示，可直接点击预览
        """,
    )

    parser.add_argument("--model", default="nano-banana",
                        choices=list(MODELS.keys()),
                        help="模型 key（默认: nano-banana）")
    parser.add_argument("--prompt",
                        help="提示词：描述你要生成的图片内容")
    parser.add_argument("--proportion", default=None,
                        help="比例，如 16:9、1:1、9:16 等")
    parser.add_argument("--resolution", default=None,
                        help="分辨率 1k/2k/4k（仅 nano-banana/pro 有效，gpt-image-2 勿传）")
    parser.add_argument("--input-images", nargs="+", default=None,
                        help="本地图片路径，支持多张。传了=图生图，不传=文生图")
    parser.add_argument("--list-models", action="store_true",
                        help="列出所有可用模型及参数")

    args = parser.parse_args()

    # 列出模型
    if args.list_models:
        print_models()
        return

    # 生图必须传 prompt
    if not args.prompt:
        parser.print_help()
        print("\n❌ 请指定 --prompt（描述你要生成的图片）", file=sys.stderr)
        sys.exit(1)

    # 上传本地图片（如果有）
    input_data = None
    if args.input_images:
        print(f"\n📤 准备上传 {len(args.input_images)} 个文件...", file=sys.stderr)
        input_data = []
        for path in args.input_images:
            data = upload_file(path)
            input_data.append(data)
        print(f"\n✅ 全部上传完成，共 {len(input_data)} 张参考图", file=sys.stderr)

    # 生图
    result = generate(
        model_key=args.model,
        prompt=args.prompt,
        proportion=args.proportion,
        resolution=args.resolution,
        input_images=input_data,
    )

    # 展示结果
    print_result(result)

    # 如果有参考图，也展示上传后的 URL
    if input_data:
        print(f"\n📎 参考图:")
        for i, img in enumerate(input_data):
            print(f"  [{i+1}] [点击预览]({img['tmp_url']})")


if __name__ == "__main__":
    main()
