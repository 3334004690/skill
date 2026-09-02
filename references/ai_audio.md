# AI Audio Module

文字生音频和声音克隆使用 `scripts/ai_audio.py`，通过 MiniMax Speech 2.8 接口生成 MP3 音频。

## Supported Models

| Model | Key | Use case |
|-------|-----|----------|
| MiniMax Speech 2.8 Turbo | `speech-2.8-turbo` | 默认模型，速度快 |
| MiniMax Speech 2.8 HD | `speech-2.8-hd` | 更高音质 |

## Endpoints

- 普通文本：`https://apis.aimaxhug.cloud/v1/minimax/audio`
- 万字长文本：`https://apis.aimaxhug.cloud/v1/minimax/audio/long`

请求使用项目的 `AIMAXHUG_API_KEY`，脚本自动发送 `Authorization: Bearer ...` 和 `Content-Type: application/json`。

## Examples

```bash
# AI 自动选择音色
python {baseDir}/scripts/ai_audio.py run \
  --model speech-2.8-turbo \
  --prompt "欢迎收听本期节目。"

# 用自然语言描述音色
python {baseDir}/scripts/ai_audio.py run \
  --model speech-2.8-hd \
  --prompt "今天我们来介绍三个实用技巧。" \
  --sys-prompt "温柔知性的女声，吐字清晰，适合播客解说"

# 长文本，调用 /audio/long
python {baseDir}/scripts/ai_audio.py run \
  --model speech-2.8-hd \
  --prompt "这里放入长篇朗读文本" \
  --long

# 声音克隆：只能上传一个本地样本；时长必须大于10秒且小于2分钟
python {baseDir}/scripts/ai_audio.py run \
  --model speech-2.8-turbo \
  --prompt "使用参考声音朗读这段话。" \
  --input-audio voice-sample.mp3
```

## Request Mapping

| CLI option | API field | Description |
|------------|-----------|-------------|
| `--model` | `model` | `speech-2.8-turbo` or `speech-2.8-hd` |
| `--prompt` | `prompt` | Required text to synthesize |
| `--sys-prompt` | `sysPrompt` | Optional natural-language voice description |
| `--input-audio` | `file` | One local audio file only; duration must be `>10s` and `<120s`. It is uploaded first and sent as a one-item URL array |
| `--long` | endpoint | Selects `/v1/minimax/audio/long`; also auto-selected above 5000 chars or whenever `--input-audio` voice cloning is used |

The API returns an object such as:

```json
{
  "url": "https://zhikecloud.oss-cn-shenzhen.aliyuncs.com/audio/example.mp3",
  "model": "speech-2.8-hd",
  "usage_characters": 58
}
```
