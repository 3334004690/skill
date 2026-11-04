#!/usr/bin/env python3
"""Probe local/HTTP(S) video duration and check Muse reference timing."""

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


MIN_REFERENCE_SECONDS = 20
REFERENCE_HEADROOM_SECONDS = 2


def media_url(value, label):
    """Validate a URL string without uploading or fetching it."""
    value = value.strip()
    try:
        parsed = urlparse(value)
        if (parsed.scheme not in ("http", "https") or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or parsed.port == 0 or "\\" in value
                or any(char.isspace() for char in value)):
            raise ValueError("URL 无效")
    except ValueError as exc:
        raise ValueError(f"{label} 必须为 HTTP(S) URL 字符串，不接受本地路径或 Base64") from exc
    return value


def positive_duration(value):
    try:
        duration = float(value)
    except (TypeError, ValueError):
        return None
    return duration if math.isfinite(duration) and duration > 0 else None


def probe_video_duration(source, ffprobe="ffprobe", timeout=60):
    """Read the video stream duration, falling back to container duration.

    ffprobe opens remote URLs directly; no API key or media upload is needed.
    Never treat an audio-only file, unknown duration, or failed probe as zero.
    """
    source = str(source).strip()
    if source.startswith(("http://", "https://")):
        source = media_url(source, "视频地址")
    else:
        path = Path(source)
        if not source or not path.is_file():
            raise ValueError("视频文件不存在，请提供本地文件或 HTTP(S) 视频直链")
        source = str(path.resolve())
    command = [
        ffprobe, "-v", "error", "-show_entries",
        "format=duration:stream=codec_type,duration:stream_disposition=attached_pic",
        "-of", "json", source,
    ]
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout, check=True,
        )
    except FileNotFoundError as exc:
        raise ValueError("未找到 ffprobe；请安装 FFmpeg 并将 ffprobe 加入 PATH，或用 --ffprobe 指定路径") from exc
    except subprocess.TimeoutExpired as exc:
        raise ValueError("视频时长检测超时，请检查视频直链或本地文件") from exc
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError("无法读取视频，请检查文件格式及 URL 是否为可访问的视频直链") from exc
    try:
        metadata = json.loads(completed.stdout)
        streams = [stream for stream in metadata.get("streams", [])
                   if stream.get("codec_type") == "video"
                   and not stream.get("disposition", {}).get("attached_pic")]
        if not streams:
            raise ValueError("素材中没有视频流")
        durations = [positive_duration(stream.get("duration")) for stream in streams]
        durations = [value for value in durations if value is not None]
        duration = max(durations) if durations else positive_duration(metadata.get("format", {}).get("duration"))
        if duration is None:
            raise ValueError("无法确定有效的视频时长")
        return duration
    except (TypeError, AttributeError, json.JSONDecodeError) as exc:
        raise ValueError("ffprobe 返回了无效的视频时长数据") from exc


def validate_reference_seconds(seconds):
    if seconds < MIN_REFERENCE_SECONDS:
        raise ValueError("使用 video_url 时，生成时长 seconds 必须大于等于 20 秒")


def reference_timing(duration, seconds):
    """Require a shorter source; recommend at least two seconds of headroom."""
    validate_reference_seconds(seconds)
    duration = positive_duration(duration)
    if duration is None:
        raise ValueError("参考视频时长必须为有效的正数")
    recommended_max = seconds - REFERENCE_HEADROOM_SECONDS
    if duration >= seconds:
        raise ValueError(
            f"参考视频实测 {duration:.6f} 秒，目标生成 {seconds} 秒："
            "源视频必须短于目标生成时长，不能使用等长或更长的源视频。"
            f"请改用 ≤{recommended_max} 秒的源视频；本次未提交生成任务。"
        )
    within_recommendation = duration <= recommended_max
    warnings = []
    if not within_recommendation:
        warnings.append(
            f"参考视频实测 {duration:.6f} 秒；生成 {seconds} 秒时建议源视频 ≤{recommended_max} 秒，预留至少 2 秒。"
            "当前源视频短于目标时长，允许提交；不会自动裁剪素材或修改生成时长。"
        )
    return {
        "source_duration_seconds": duration,
        "requested_seconds": seconds,
        "available_continuation_seconds": seconds - duration,
        "recommended_max_source_seconds": recommended_max,
        "within_recommendation": within_recommendation,
        "warnings": warnings,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="检测本地/URL 视频时长，可检查 Muse 参考视频时长建议")
    parser.add_argument("source", help="本地视频文件或 HTTP(S) 视频直链")
    parser.add_argument("--seconds", type=int, help="续写后的目标总秒数；参考视频模式至少 20 秒")
    parser.add_argument("--ffprobe", default="ffprobe", help="ffprobe 可执行文件路径，默认从 PATH 查找")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.seconds is not None:
            validate_reference_seconds(args.seconds)
        duration = probe_video_duration(args.source, args.ffprobe)
        result = {"source_duration_seconds": duration}
        if args.seconds is not None:
            result = reference_timing(duration, args.seconds)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"视频实测时长: {duration:.3f} 秒")
            if args.seconds is not None:
                print(f"续写目标总时长 {args.seconds} 秒，可续写余量 {result['available_continuation_seconds']:.6f} 秒；"
                      f"建议源视频 ≤{result['recommended_max_source_seconds']} 秒")
            for warning in result.get("warnings", []):
                print(f"提示: {warning}", file=sys.stderr)
        return 0
    except ValueError as exc:
        if args.json:
            print(json.dumps({"state": "failed", "message": str(exc)}, ensure_ascii=False))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    sys.exit(main())
