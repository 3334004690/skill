#!/usr/bin/env python3
"""Upload local files to Aimaxhug and return temp URL + metadata.

## AGENT INSTRUCTIONS — READ FIRST
- Default flow: use `run` to upload one or more files.
- Do NOT ask the user to upload manually — handle it for them.
- The returned data object (tmp_url/name/type/size) is passed to
  ai_image.py's --input-images for image-to-image generation.

Subcommands:
    run           Upload file(s) and print result — DEFAULT

Usage:
    python upload.py run photo.jpg
    python upload.py run photo1.jpg photo2.png
    python upload.py run photo.jpg --json
"""

import argparse
import json as json_mod
import mimetypes
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared.client import AimaxhugClient, AimaxhugError
from shared.config import load_config

UPLOAD_ENDPOINT = "/api/v2/upload/file"


def add_upload_args(p):
    p.add_argument("files", nargs="+", help="本地文件路径（支持多个）")
    p.add_argument("--json", action="store_true", help="以 JSON 格式输出结果")
    return p


def cmd_run(args):
    """Upload file(s) and print result."""
    client = AimaxhugClient()

    results = []
    for file_path in args.files:
        path = Path(file_path)
        if not path.exists():
            print(f"Error: 文件不存在: {file_path}", file=sys.stderr)
            sys.exit(1)

        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(path.name)
        if not mime_type:
            mime_type = "application/octet-stream"

        print(f"📤 上传中: {path.name}...", file=sys.stderr)

        try:
            data = client.post_file(UPLOAD_ENDPOINT, str(path), mime_type)
        except AimaxhugError as e:
            print(f"Error: 上传失败: {e}", file=sys.stderr)
            sys.exit(1)

        results.append(data)
        print(f"   ✅ {data['tmp_url']}", file=sys.stderr)
        print(f"      ![]({data['tmp_url']})", file=sys.stderr)
        print(f"      类型: {data['type']}  大小: {data['size'] / 1024:.1f} KB", file=sys.stderr)

    if args.json:
        print(json_mod.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(f"\n✅ 上传完成，共 {len(results)} 个文件", file=sys.stderr)
        for i, data in enumerate(results):
            print(f"\n  [{i+1}] {data['name']}")
            print(f"      📍 {data['tmp_url']}")
            print(f"      ![]({data['tmp_url']})")
            print(f"      tmp_url: {data['tmp_url']}")
            print(f"      name: {data['name']}")
            print(f"      type: {data['type']}")
            print(f"      size: {data['size']}")
        print()

        print("---")
        print("将以下 data 对象传入 ai_image.py 的 --input-images 参数:")
        print(json_mod.dumps(results, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(
        description="文件上传 — 上传本地文件到 Aimaxhug",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="subcommand", required=False)

    # run
    p_run = sub.add_parser("run", help="上传文件（默认）")
    add_upload_args(p_run)

    args = parser.parse_args()

    if args.subcommand is None or args.subcommand == "run":
        # If no subcommand but files are provided, treat as run
        if hasattr(args, "files") and args.files:
            cmd_run(args)
        else:
            parser.print_help()
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
