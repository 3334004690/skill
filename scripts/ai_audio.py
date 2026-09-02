#!/usr/bin/env python3
"""Generate speech audio with MiniMax speech-2.8 models.

Short text uses /v1/minimax/audio; long text (up to about 10,000 Chinese
characters) uses /v1/minimax/audio/long. Local reference audio files are
uploaded through the shared upload endpoint before voice cloning.
"""

import argparse
import json as json_mod
import mimetypes
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared.client import AimaxhugClient, AimaxhugError

AUDIO_ENDPOINT = "https://apis.aimaxhug.cloud/v1/minimax/audio"
AUDIO_LONG_ENDPOINT = "https://apis.aimaxhug.cloud/v1/minimax/audio/long"
UPLOAD_ENDPOINT = "/api/v2/upload/file"
MAX_PROMPT_CHARS = 10_000
AUTO_LONG_THRESHOLD = 5_000
MIN_CLONE_SECONDS = 10
MAX_CLONE_SECONDS = 120

AUDIO_MODELS = {
    "speech-2.8-turbo": "MiniMax Speech 2.8 Turbo",
    "speech-2.8-hd": "MiniMax Speech 2.8 HD",
}


def upload_audio(client, file_path):
    """Upload a local reference audio file and return its temporary URL."""
    if file_path.startswith(("http://", "https://")):
        raise ValueError("声音克隆必须上传本地音频文件，以便校验时长")
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        raise ValueError(f"音频文件不存在: {file_path}")

    duration = audio_duration(path)
    if duration <= MIN_CLONE_SECONDS or duration >= MAX_CLONE_SECONDS:
        raise ValueError(
            f"声音样本时长必须大于 {MIN_CLONE_SECONDS} 秒且小于 {MAX_CLONE_SECONDS} 秒，"
            f"当前为 {duration:.2f} 秒"
        )

    mime_type, _ = mimetypes.guess_type(path.name)
    if not mime_type or not mime_type.startswith("audio/"):
        mime_type = "audio/mpeg"

    print(f"📤 上传声音样本: {path.name}...", file=sys.stderr)
    data = client.post_file(UPLOAD_ENDPOINT, str(path), mime_type)
    return data["tmp_url"]


def audio_duration(path):
    """Return audio duration in seconds; fail closed when metadata is unreadable."""
    try:
        if path.suffix.lower() == ".wav":
            with wave.open(str(path), "rb") as wav_file:
                frame_rate = wav_file.getframerate()
                if not frame_rate:
                    raise ValueError("WAV 文件采样率无效")
                return wav_file.getnframes() / float(frame_rate)

        from mutagen import File as mutagen_file
        audio = mutagen_file(str(path))
        duration = getattr(getattr(audio, "info", None), "length", None)
        if duration is not None:
            return float(duration)
    except ImportError:
        raise ValueError("无法读取音频时长，请先安装 mutagen 依赖")
    except (OSError, TypeError, ValueError) as exc:
        raise ValueError(f"无法读取音频时长: {exc}")

    raise ValueError("无法读取音频时长，请使用常见音频格式（MP3/WAV/M4A/OGG）")


def _extract_result(data):
    """Normalize the documented flat response and common wrapped responses."""
    if not isinstance(data, dict):
        raise AimaxhugError("响应格式无效")
    payload = data.get("data") if isinstance(data.get("data"), dict) else data
    url = payload.get("url") or payload.get("audioUrl") or payload.get("audio_url")
    if not url:
        raise AimaxhugError("响应数据中没有音频 URL")
    return {
        "url": url,
        "model": payload.get("model", ""),
        "usage_characters": payload.get("usage_characters", payload.get("usageCharacters", 0)),
    }


def cmd_list_models(_args):
    print("可用音频模型：")
    for key, name in AUDIO_MODELS.items():
        print(f"  [{key}] {name}")
    print("\n模式：默认短文本；使用 --long、文本超过 5000 字或声音克隆时调用万字接口。")
    print("声音克隆：使用 --input-audio 传入一个本地音频文件，时长必须 >10 秒且 <120 秒。")


def add_generate_args(parser):
    parser.add_argument("--model", choices=list(AUDIO_MODELS), default="speech-2.8-turbo",
                        help="模型 key（默认: speech-2.8-turbo）")
    parser.add_argument("--prompt", required=True, help="要朗读合成的文本内容")
    parser.add_argument("--sys-prompt", dest="sys_prompt", default=None,
                        help="音色描述，例如：温柔知性的女声，吐字清晰，适合播客解说")
    parser.add_argument("--input-audio", nargs="+", default=None,
                        help="声音克隆样本，只能传一个本地音频文件（时长 >10 秒且 <120 秒）")
    parser.add_argument("--long", action="store_true",
                        help="使用万字长文本接口；文本超过 5000 字时自动启用")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出结果")


def cmd_run(args):
    prompt = args.prompt.strip()
    if not prompt:
        print("Error: prompt 不能为空", file=sys.stderr)
        sys.exit(1)
    if len(prompt) > MAX_PROMPT_CHARS:
        print(f"Error: 文本最多 {MAX_PROMPT_CHARS} 字，当前 {len(prompt)} 字", file=sys.stderr)
        sys.exit(1)

    client = AimaxhugClient()
    file_urls = []
    if args.input_audio:
        if len(args.input_audio) != 1:
            print("Error: 声音克隆只能上传一个音频文件", file=sys.stderr)
            sys.exit(1)
        try:
            file_urls = [upload_audio(client, args.input_audio[0])]
        except (ValueError, AimaxhugError) as exc:
            print(f"Error: 声音样本上传失败: {exc}", file=sys.stderr)
            sys.exit(1)

    body = {
        "model": args.model,
        "prompt": prompt,
    }
    if args.sys_prompt:
        body["sysPrompt"] = args.sys_prompt.strip()
    if file_urls:
        body["file"] = file_urls

    # Voice cloning uses the long endpoint so the uploaded file array is
    # handled consistently and prompts up to about 10,000 chars are allowed.
    use_long = args.long or len(prompt) > AUTO_LONG_THRESHOLD or bool(file_urls)
    endpoint = AUDIO_LONG_ENDPOINT if use_long else AUDIO_ENDPOINT
    if use_long:
        print(f"🎙️ 正在使用 {args.model} 生成长文本音频...", file=sys.stderr)
    else:
        print(f"🎙️ 正在使用 {args.model} 生成音频...", file=sys.stderr)

    try:
        result = _extract_result(client.post(endpoint, json=body, timeout=900))
    except AimaxhugError as exc:
        print(f"Error: 音频生成失败: {exc}", file=sys.stderr)
        sys.exit(1)

    result["model"] = result["model"] or args.model
    result["endpoint"] = endpoint
    result["usage_characters"] = result["usage_characters"] or len(prompt)
    if args.json:
        print(json_mod.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("\n✅ 音频生成成功！")
        print(f"📍 {result['url']}")
        print(f"🔊 [点击播放]({result['url']})")
        print(f"🤖 模型: {result['model']}")
        print(f"📝 字符数: {result['usage_characters']}")


def main():
    parser = argparse.ArgumentParser(description="文字生音频 / 声音克隆（MiniMax Speech 2.8）")
    sub = parser.add_subparsers(dest="subcommand")
    sub.add_parser("list-models", help="列出可用音频模型")
    run_parser = sub.add_parser("run", help="生成音频（默认）")
    add_generate_args(run_parser)
    args = parser.parse_args()

    if args.subcommand == "list-models":
        cmd_list_models(args)
    elif args.subcommand in (None, "run"):
        if not hasattr(args, "prompt"):
            parser.print_help()
            sys.exit(1)
        cmd_run(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
