"""产物落盘：宿主注入 SKILL_OUTPUT_DIR 时把远端产物下载到本地。"""

import mimetypes
import os
import sys
import time
from pathlib import Path

import requests


def env_save_dir():
    """读取宿主注入的 SKILL_OUTPUT_DIR（未设置或为空返回 None）。"""
    return os.environ.get("SKILL_OUTPUT_DIR", "").strip() or None


def download_to_local(url, save_dir, index, default_ext=".bin", timeout=120):
    """Download a remote artifact into save_dir and return the absolute path.

    Returns None on failure (caller keeps the remote URL so the result is not lost).
    """
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        ct = (resp.headers.get("Content-Type") or "").split(";")[0].strip()
        ext = mimetypes.guess_extension(ct) or default_ext
        if ext == ".jpe":
            ext = ".jpg"

        out_dir = Path(save_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        out_path = out_dir / f"file_{stamp}_{index}{ext}"
        out_path.write_bytes(resp.content)
        return str(out_path.resolve())
    except Exception as e:
        print(f"  ⚠️ 本地保存失败（保留远端地址）: {e}", file=sys.stderr)
        return None
