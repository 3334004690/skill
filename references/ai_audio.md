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

## 执行检查与来源

先按 [AUTH.md](../AUTH.md) 自检依赖与 Key。用户要求直接提交时，复用已有模型选择/代选授权；按下表检查实际输入，不能只检查样本时长。

| 检查项 | 当前 CLI 的规则 | 回复中说明 |
|--------|-----------------|------------|
| 实际文案 | 对 `prompt.strip()` 使用 Python `len()`，最多 10000 字符；内部标点、空格、换行均计数 | 实测字符数；仅有片段或口述字数时标为未核实，不保证全文可执行 |
| 接口选择 | 字符数 >5000，或有 `--long`，或声音克隆时走 `/v1/minimax/audio/long`；否则走 `/v1/minimax/audio` | 选定接口及触发原因；5000 字符是本地自动路由阈值 |
| 样本数量/路径 | 克隆只接受 1 个实际存在的本地音频文件，不接受远程 URL 作为 `--input-audio` | 实际数量、文件是否存在 |
| 样本时长 | 实测满足 `10 秒 < 时长 < 120 秒`，边界 10、120 秒均不接受 | 实测秒数，不把用户描述当成检测结果 |
| 上传与引用 | 先调用 `/api/v2/upload/file`，再把 `tmp_url` 放入单元素 `file` URL 数组，提交 `/audio/long` | 上传由脚本自动完成，不重复上传、不直接把本地路径放到 API 的 `file` 字段 |

复用用户已有的声音使用授权；用户明确要求克隆自己的声音即为本次授权，不额外索取证明或重复确认。必要授权缺失或不明时仅暂停克隆，明确缺失项；不要编造授权、文件、完整文案或生成结果。超长样本的裁剪、改文案、换声音应遵循已有授权，不得擅自改动。其他独立任务可继续。

以上本地限制可查 [ai_audio.py](../scripts/ai_audio.py) 的 `MAX_PROMPT_CHARS`、`AUTO_LONG_THRESHOLD`、`upload_audio` 与 `cmd_run`。**10000 字符是当前 CLI 上限，不是已证明的服务端上限**；当前公开 [OpenAPI](https://apis.aimaxhug.cloud/openapi.json) 将 `/v1/minimax/audio/long` 描述为“长文本声音克隆专用接口”，要求同时有 `file` 和 `prompt/text`，最多 20000 字符（2026-10-26 查阅）。该 20000 不能泛化到普通 TTS 或本地 CLI。现有 CLI 还会把无样本的长文本路由到 `/audio/long`，这与当前服务端描述有差异，能否执行以接口响应为准，不能保证成功；此处保留原路由逻辑。关于具体文件时长、授权或尚未提供的全文，该来源不能代替实际检查。

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
