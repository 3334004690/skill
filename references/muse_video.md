# Muse Video Pro 视频生成

使用 `scripts/muse_video.py`，默认模型为 `muse-video-pro`。参数依据用户于 2026-11-04 提供的说明；未通过付费生成请求核实服务端效果。提交、鉴权、轮询及产物下载沿用项目现有视频 CLI 的方式。

## 面向用户的创作菜单

用户询问“怎么用”“有哪些选项”时，使用下面的中文菜单。`python scripts/muse_video.py list-models` 也会输出此菜单；`--json` 的技术能力清单供 AI 内部核对，不直接展示给普通用户。

**🎬 Muse 视频创作**

| 想设置什么 | 可以怎么选 |
| :--- | :--- |
| ✍️ 画面内容 | 描述场景、人物动作和台词，**这是必填项** |
| ⏱️ 视频时长 | **默认 5 秒**；可选 5、8、10、20、30、40、50、60 秒，推荐 5–40 秒 |
| 🖼️ 画面比例 | **横屏 16:9**、竖屏 9:16、方形 1:1、横幅 4:3、竖幅 3:4 |
| 🔊 人物声音 | **正常说话**，或只做口型、不出声；环境音和背景音乐保留 |
| 🎥 镜头方式 | **由 AI 安排**，也可以选推进、环绕、跟拍、固定、向左移动 |
| 📎 参考素材 | 可选：参考图片（最多 4 张）、开头画面、结尾画面，或用于续写的视频 |
| 🚫 避免内容 | 可选：例如不要字幕、不要模糊、不要多余人物 |

菜单后只用一句自然的话收集关键信息：“告诉我想拍什么、做多少秒；有参考图片或视频，直接发给我。其他设置可以交给我。”用户已经给出这些信息时直接继续；未指定的可选设置用适用默认值，不要求逐项确认。使用续写素材时再解释目标是成片总时长，并用实测秒数说明能续写多少。

用户说“人物静音”时，用“只做口型、不出声，环境音和背景音乐保留”说明效果。镜头方式展示中文词，不把英文枚举、真假值或命令参数当成选项。

## AI 自动处理参考素材

用户只需要提供素材和创作要求。普通菜单、追问、确认话术不要要求用户提供某种协议的地址、转换编码、手动上传到图床，或填写内部参数；不展示上传接口返回的素材链接、文件元数据对象及中间请求体。用户明确索要技术用法或素材链接时再按需提供。最终作品正常展示。

内部执行方式：

1. 确认素材在生成中的用途：开头画面、结尾画面、人物/场景参考图，或续写视频。用户已说明用途就沿用；只有用途无法推断且会改变结果时才用中文补问。
2. **本地素材**：读取用户提供的真实附件或本地路径。续写视频先运行 `python scripts/video_duration.py "<本地视频路径>" --seconds <目标总秒数> --json`，确认时长适合续写，再上传。图片和视频由 AI 调用已有的 `python scripts/upload.py run "<路径1>" "<路径2>" --json`，按返回数组与文件顺序对应提取每项 `tmp_url`；无需让用户操作终端或自行转换链接。已有的有效上传结果可以复用。
3. **用户已有素材链接**：直接填入对应参数，不重新下载、上传或要求用户换成本地文件；续写视频仍执行时长检测，不跳过校验。
4. 将素材地址映射到内部字段：开头画面 → `input_reference` 字符串；结尾画面 → `last_frame` 字符串；人物/场景参考图 → `images` 字符串数组（最多 4 张）；续写视频 → `video_url` 字符串。Muse 取上传结果中的 `tmp_url`，不传完整上传对象，也不把元数据当作图片数组项。
5. 调用 `scripts/muse_video.py run ... --json` 生成。CLI 接收准备好的素材地址，不重复上传；AI 负责先调用上传脚本、再把返回地址填入生成参数。提交后按既有方式报告任务状态，完成后直接展示作品。

上传失败或素材不存在时，只暂停受影响的生成，简短说明“这份素材暂时没能处理成功”及真实原因；不伪造素材地址或声称已生成。续写时长不合适时可以说：“这段视频已经 20 秒，无法续写成 20 秒。可以换一段更短的视频，或把成片改为 30 秒。”不要擅自更改目标或裁剪素材。

上传接口与结果格式见 [upload.md](upload.md)。下面的技术说明供 AI 执行和排查使用，不原样复制成面向用户的菜单。

本地图片、视频上传时，公共入口自动按固定质量 40 / CRF 40 编码临时副本，再上传并返回实际压缩文件的地址，不设 1MB/2MB 体积目标。Muse 填写该返回地址，不另行上传原图或原视频；续写的实测时长规则保持有效，压缩不裁剪视频或降低画面尺寸。详见 [上传前压缩](upload.md#上传前压缩)。

## 内部调用参数

| API 字段 | 类型 | CLI 参数与规则 |
|----------|------|----------------|
| `model` | string | `--model`，默认且仅支持 `muse-video-pro` |
| `prompt` | string | `--prompt`，必填且非空，不截断 |
| `aspect_ratio` | string | `--aspect-ratio` / `--ratio`，支持 `16:9`、`9:16`、`1:1`、`4:3`、`3:4`，本地默认 `16:9` |
| `seconds` | string | `--seconds`，目标视频总时长；续写时包含源视频已有时长。支持 `"5"`、`"8"`、`"10"`、`"20"`、`"30"`、`"40"`、`"50"`、`"60"`；本地默认 5 秒，推荐 **5–40 秒**稳定产出 |
| `camera_motion` | string | `--camera-motion`，例如 `pan_left`、`zoom_in`、`orbit`、`tracking_shot`、`static`；这些是示例，不是本地硬性枚举 |
| `negative_prompt` | string | `--negative-prompt`，负面提示词 |
| `input_reference` | string | `--input-reference`，首帧 HTTP(S) URL，单个字符串 |
| `last_frame` | string | `--last-frame`，尾帧 HTTP(S) URL，单个字符串 |
| `images` | string[] | `--images URL1 URL2`，最多 4 张，支持 HTTP(S) URL、原始 Base64 或 `data:image/...;base64,...` |
| `video_url` | string | `--video-url`，参考视频 HTTP(S) 直链；提交前自动实测源视频时长 |
| `mute_voice` | boolean | `--mute-voice true/false`，默认 `false`；单写 `--mute-voice` 等同 `true` |

API 中含下划线的字段也支持同名 CLI 别名，如 `--input_reference`、`--mute_voice`。`--poll-timeout` 默认 1800 秒；`--json` 将结果写入 stdout，任务 ID、进度与提示写入 stderr。未提供的选填字段不进入请求体；本地默认的比例、秒数及 `mute_voice: false` 会明确提交。

首尾帧和 `video_url` 的内部请求字段仅接受 URL 字符串。本地素材由 AI 先调用项目上传脚本，再把返回地址填入这些字段；这是内部处理步骤，不是要求用户提供某种格式的素材。没有额外规定首尾帧与 `images` 互斥，也不要求尾帧必须搭配首帧。本地校验 URL/Base64 的格式，不代表已核实图片实际内容或远程素材可达性。

`seconds` 包含 `50`，已由用户确认。**接口 JSON 的 `seconds` 必须是字符串，例如 `"seconds": "20"`，不能发送数字 `"seconds": 20`**；后者会触发 `cannot unmarshal number into Go struct field .Alias.seconds of type string`。CLI 仍写 `--seconds 20`，脚本负责转换；`--dry-run` 的请求预览与实际提交保持相同字段类型。时长检测、续写余量和结果中的秒数保持数值计算，`mute_voice` 保持 boolean。AI 使用现有 CLI，不根据旧参数表另写请求。参考视频须在提交前实测时长，避免使用等于或超过目标生成时长的素材。

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

参考视频检测优先使用 PATH 中的 `ffprobe`，也可通过 `--ffprobe "绝对路径/ffprobe.exe"` 指定。缺少独立 ffprobe 时，使用已声明依赖 imageio-ffmpeg 提供的视频组件读取时长；可用项目自检安装依赖。检测不需要 API Key，也不替代真实生成所需的 `AIMAXHUG_API_KEY`。

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
