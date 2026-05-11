#!/usr/bin/env python3
"""
文件上传脚本 — AI 直接运行，无需写代码
======================================

【AI 使用说明】
  当用户提供了本地文件需要上传时，直接执行本脚本。
  上传后返回的 data 对象完整传给生图接口的 original_image 参数。

用法:
  # 上传单个文件
  python scripts/upload.py photo.jpg

  # 上传多个文件
  python scripts/upload.py photo1.jpg photo2.png

  # 输出 JSON 格式（供其他脚本调用）
  python scripts/upload.py photo.jpg --json
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests


BASE_URL = "https://base-api.aimaxhug.com"
UPLOAD_URL = f"{BASE_URL}/api/v2/upload/file"


def get_api_key():
    """从 .env 文件读取 API Key"""
    key = os.getenv("AIMAXHUG_API_KEY")
    if key:
        return key
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text().strip().splitlines():
            if line.startswith("AIMAXHUG_API_KEY="):
                return line.split("=", 1)[1].strip()
    print("❌ 未找到 API Key。请在 .env 文件中设置 AIMAXHUG_API_KEY=sk-xxx", file=sys.stderr)
    sys.exit(1)


def upload_file(file_path):
    """
    上传单个文件，返回完整 data 对象

    返回: {"tmp_url": str, "name": str, "type": str, "size": int}
    """
    path = Path(file_path)
    if not path.exists():
        print(f"❌ 文件不存在: {file_path}", file=sys.stderr)
        sys.exit(1)

    key = get_api_key()

    with open(path, "rb") as f:
        resp = requests.post(
            UPLOAD_URL,
            headers={"Authorization": f"Bearer {key}"},
            files={"file": f},
            timeout=120,
        )

    data = resp.json()
    if resp.status_code != 200 or data.get("status") != 200:
        print(f"❌ 上传失败: {data.get('message', resp.text)}", file=sys.stderr)
        sys.exit(1)

    return data["data"]  # {tmp_url, name, type, size}


def main():
    parser = argparse.ArgumentParser(
        description="文件上传 — AI 直接运行，无需写代码",
        epilog="""
【AI 使用说明】
  1. 用户提供本地文件路径时，直接执行本脚本
  2. 上传返回的 data 对象（含 tmp_url/name/type/size）传给生图接口
  3. 多个文件用空格分隔
        """,
    )
    parser.add_argument("files", nargs="+", help="要上传的文件路径（支持多个）")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出结果（供脚本调用）")

    args = parser.parse_args()

    results = []
    for file_path in args.files:
        path = Path(file_path)
        print(f"📤 上传中: {path.name}...", file=sys.stderr)
        data = upload_file(file_path)
        results.append(data)
        print(f"   ✅ [点击预览]({data['tmp_url']})", file=sys.stderr)
        print(f"      类型: {data['type']}  大小: {data['size'] / 1024:.1f} KB", file=sys.stderr)

    if args.json:
        # JSON 格式输出，供其他脚本程序化调用
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(f"\n✅ 上传完成，共 {len(results)} 个文件", file=sys.stderr)
        for i, data in enumerate(results):
            print(f"\n  [{i+1}] {data['name']}")
            print(f"      📍 [点击预览]({data['tmp_url']})")
            print(f"      tmp_url: {data['tmp_url']}")
            print(f"      name: {data['name']}")
            print(f"      type: {data['type']}")
            print(f"      size: {data['size']}")
        print()

        # 最后一行为 JSON 数组，方便管道传递
        print("---")
        print("将以下 data 对象传入生图接口的 original_image 参数（数组格式）:")
        print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
