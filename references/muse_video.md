# Muse Video Pro 视频生成

使用 `scripts/muse_video.py`，默认模型为 `muse-video-pro`。参数依据用户于 2026-11-04 提供的说明；未通过付费生成请求核实服务端效果。提交、鉴权、轮询及产物下载沿用项目现有视频 CLI 的方式。

## 参数

| API 字段 | 类型 | CLI 参数与规则 |
|----------|------|----------------|
| `model` | string | `--model`，默认且仅支持 `muse-video-pro` |
| `prompt` | string | `--prompt`，必填且非空，不截断 |
| `aspect_ratio` | string | `--aspect-ratio` / `--ratio`，支持 `16:9`、`9:16`、`1:1`、`4:3`、`3:4`，本地默认 `16:9` |
| `seconds` | integer | `--seconds`，目标视频总时长；续写时包含源视频已有时长。支持 `5`、`8`、`10`、`20`、`30`、`40`、`50`、`60`；本地默认 `5`，推荐 **5–40 秒**稳定产出 |
| `camera_motion` | string | `--camera-motion`，例如 `pan_left`、`zoom_in`、`orbit`、`tracking_shot`、`static`；这些是示例，不是本地硬性枚举 |
| `negative_prompt` | string | `--negative-prompt`，负面提示词 |
| `input_reference` | string | `--input-reference`，首帧 HTTP(S) URL，单个字符串 |
| `last_frame` | string | `--last-frame`，尾帧 HTTP(S) URL，单个字符串 |
| `images` | string[] | `--images URL1 URL2`，最多 4 张，支持 HTTP(S) URL、原始 Base64 或 `data:image/...;base64,...` |
| `video_url` | string | `--video-url`，参考视频 HTTP(S) 直链；提交前自动实测源视频时长 |
| `mute_voice` | boolean | `--mute-voice true/false`，默认 `false`；单写 `--mute-voice` 等同 `true` |

API 中含下划线的字段也支持同名 CLI 别名，如 `--input_reference`、`--mute_voice`。`--poll-timeout` 默认 1800 秒；`--json` 将结果写入 stdout，任务 ID、进度与提示写入 stderr。未提供的选填字段不进入请求体；本地默认的比例、秒数及 `mute_voice: false` 会明确提交。

首尾帧和 `video_url` 仅接受 URL，不自动上传本地文件。需要本地素材时先使用项目的上传脚本取得可访问直链。没有额外规定首尾帧与 `images` 互斥，也不要求尾帧必须搭配首帧。本地校验 URL/Base64 的格式，不代表已核实图片实际内容或远程素材可达性。

`seconds` 包含 `50`，已由用户确认。参考视频须在提交前实测时长，避免使用等于或超过目标生成时长的素材。

## 参考视频时长逻辑

参考视频一般用于**视频续写**。`seconds` 是续写完成后的目标总时长，可续写余量 = `seconds - 源视频实测时长`。例如源视频 18 秒、目标 20 秒，余量为 2 秒；源视频已经 20 秒、目标仍为 20 秒，没有续写空间，必须拦截。CLI 在提交前报告实测时长、目标总时长和余量，JSON 中的 `available_continuation_seconds` 是计算出的可续写空间，不是已生成或实测的成片时长。

传入 `video_url` 时：

1. **生成时长 `seconds` 必须 ≥20 秒**，否则在读取素材、创建 API 客户端或提交任务之前报错。这里的 20 秒限制应用于生成时长，源视频没有 20 秒下限。
2. 调用 `scripts/video_duration.py` 中的公共检测函数，使用 **ffprobe** 实测源视频时长。检测失败、没有视频流或时长未知时不提交，不以零秒或手填值绕过检测。
3. **源视频时长必须 < `seconds`**。实测值等于或超过目标生成时长时直接报错，指出源视频秒数、目标秒数和建议值，不创建 API 客户端、不提交任务。生成 20 秒时，20 秒源视频会被拦截；生成 30 秒时，30 秒或更长的源视频同样会被拦截。
4. 在源视频短于目标时长的前提下，建议源视频时长 **≤ `seconds - 2` 秒**，预留至少 2 秒。比如生成 20 秒：≤18 秒符合建议，19 秒会提示余量不足但允许提交，≥20 秒禁止提交。提示写入 stderr 和 JSON 的 `preflight.warnings`；不会擅自裁剪素材或改写生成秒数。

| 生成时长 | 建议源视频时长 |
|----------|----------------|
| 20 秒 | ≤18 秒 |
| 30 秒 | ≤28 秒 |
| 40 秒 | ≤38 秒 |
| 50 秒 | ≤48 秒（生成时长超过稳定推荐范围） |
| 60 秒 | ≤58 秒（生成时长超过稳定推荐范围） |

不传 `video_url` 时无需 ffprobe，也不执行参考视频的 20 秒限制。选择 50/60 秒只提示稳定性建议，不禁止使用。

需要参考视频时安装 FFmpeg，将其中的 `ffprobe` 加入 PATH，或通过 `--ffprobe "绝对路径/ffprobe.exe"` 指定可执行文件。该依赖仅用于素材检测，不替代 `AIMAXHUG_API_KEY`；检测本身不需要 API Key。

独立检测脚本支持本地文件和 HTTP(S) 视频直链，不上传文件、不调用生成 API。它优先读取视频流时长，无有效流时长时读取容器时长；结果 `source_duration_seconds` 为检测值，未经四舍五入的值参与建议比较。

本地参考视频先用独立脚本检查目标秒数与源视频时长，符合规则后再使用项目上传脚本取得 URL。对已经上传的 `video_url`，生成脚本在提交前自动重新检测；普通生成和 `--dry-run` 都不能绕过时长规则。

```bash
python scripts/video_duration.py source.mp4 --json
python scripts/video_duration.py source.mp4 --seconds 20 --json
python scripts/video_duration.py https://media.example.com/source.mp4 --seconds 30 --json
```

## 人物静音与音效

- `mute_voice=false`：默认人物按提示词或剧本台词正常开口发音、配音。
- `mute_voice=true`：人物仍按台词和情绪张嘴、完成口型表演，但音频轨中人物静音；完整保留环境音效（SFX）、动作拟音（Foley）与背景氛围音乐（BGM），方便后期贴配音。

这是模型参数的预期语义。CLI 将布尔值透传给 API，不进行成片后期消音，也未实测音轨效果。

## 接口与任务查询

```text
POST https://apis.aimaxhug.cloud/v1/videos
GET  https://apis.aimaxhug.cloud/v1/videos/muse-video-pro/{task_id}
Authorization: Bearer <AIMAXHUG_API_KEY>
```

提交后立即输出 `TASK_ID`，每 10 秒查询一次，默认最多等待 30 分钟。HTTP 400 等非成功响应若包含任务 ID，继续查询同一任务；不重新提交。完成后输出视频 URL 和宿主标记；设置 `SKILL_OUTPUT_DIR` 时沿用项目自动下载逻辑。超时或中断本地等待不会取消服务端任务，可用 `status` 继续查询。

```bash
python scripts/muse_video.py list-models --json
python scripts/muse_video.py status --task-id "实际任务ID" --wait --json
```

## 调用示例

以下命令在项目根目录执行，示例域名需替换为实际素材直链。

```bash
# 文生视频，默认模型 muse-video-pro、横屏、5 秒、人物正常发音
python scripts/muse_video.py run --prompt "雨后街道，人物迎着晨光缓慢走来" --json

# 首尾帧、运镜、负面提示词；静音人物配音，保留口型与环境音
python scripts/muse_video.py run --prompt "角色说：欢迎回来；镜头缓缓推进，树叶沙沙作响" --seconds 10 --aspect-ratio 9:16 --camera-motion zoom_in --negative-prompt "画面抖动、模糊" --input-reference https://media.example.com/start.jpg --last-frame https://media.example.com/end.jpg --mute-voice true --json

# 多参考图，最多四张；可将 URL 换为实际图片 Base64
python scripts/muse_video.py run --prompt "保持人物服饰与场景一致，人物自然行走" --images https://media.example.com/person.jpg https://media.example.com/scene.jpg --seconds 8 --json

# 参考视频：生成 20 秒，提交前检测并建议源视频不超过 18 秒
python scripts/muse_video.py run --prompt "参考原视频的角色动作和镜头节奏" --video-url https://media.example.com/source.mp4 --seconds 20 --json

# 参数预览，无需 API Key，不提交生成任务
python scripts/muse_video.py run --prompt "海浪拍岸，镜头平稳环绕" --camera-motion orbit --dry-run --json
```

`--dry-run` 有参考视频时仍会联网读取该 URL 并执行时长检测；没有参考视频时为离线校验。真实生成、查询任务需要预先配置的 API Key，见 [AUTH.md](../AUTH.md)。

离线回归验证（模拟 ffprobe 与 API 响应，不发送生成请求）：

```bash
python -m unittest discover -s scripts -p test_muse_video.py -v
```
