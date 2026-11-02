# Omni 视频生成

使用独立脚本 `scripts/omni_video.py`；鉴权复用 `shared_client.py`，提交及查询路径与现有视频接口相同。无需修改或调用 `minimax_video.py`。参数依据用户于 2026-11-02 提供的说明；Gemini 能力和素材限制未另行联网核实。

## 支持模型

| `model` | CLI |
|---------|-----|
| `omni-fast-v2v-no-water` | `--model omni-fast-v2v-no-water` |
| `omni-fast` | `--model omni-fast` |
| `omni-fast-no-water` | `--model omni-fast-no-water` |

三个模型均使用下列参数，不套用即梦或 MiniMax 的时长、参考素材及提示词限制。

## 参数与命令映射

| JSON 参数 | 类型 | 必填 | 默认 / 范围 | CLI 与说明 |
|-----------|------|------|-------------|------------|
| `model` | string | 是 | 上表三个完整模型 key | `--model` 必须明确指定，无默认模型 |
| `prompt` | string | 是 | 非空，无本地硬性长度上限 | `--prompt`；完整透传，不截断，交由 Gemini 官方处理 |
| `aspect_ratio` | string | 否 | `16:9`；`16:9` / `9:16` | `--ratio` 或 `--aspect-ratio` |
| `seconds` / `duration` | string / int | 否 | `10` | `--seconds "10"` 保留字符串；`--duration 10` 使用整数；二选一，默认提交 `duration: 10` |
| `image_url` | string | 否 | — | `--image-url`；单张公网 HTTP(S) 图片 URL 或 `data:image/...;base64,...` |
| `first_image_url` | string | 否 | — | `--first-image-url`；公网首帧图片 URL |
| `last_image_url` | string | 否 | — | `--last-image-url`；公网末帧图片 URL |
| `video` / `video_url` | string | 否 | — | `--video` / `--video-url`；源视频公网 URL，两个字段可各放一个视频；每个≤8MB、≤1920×1080 |
| `videos` | string[] | 否 | 最多 2 个 | `--videos URL1 URL2`；每个≤8MB、≤1920×1080 |
| `images` | string[] | 否 | 最多 5 张 | `--images URL1 URL2`；每张≤8MB；也可传图片 Base64 data URI |

`--poll-timeout`（默认 1800 秒）和 `--json` 延续现有 CLI；另提供 `run --dry-run --json` 离线预检，无需密钥，也不会上传或提交。`--resolution`、音频参数及 MiniMax 专用参数不用于 Omni；不要混用 `--first-image` 和 `--first-image-url`。

时长参数表示请求值。**当前 Gemini 固定输出约 10 秒**，传入 5、15 或其他秒数不保证改变产物时长。脚本只要求传入正整数秒，不套用 4–15 秒或 15/30 秒校验。JSON 结果中的 `requested_duration` 是请求值，`expected_duration: 10` 是当前预期值，不代表测量过产物时长。

## 素材检查范围

- `video`、`video_url`、`videos` 所有输入合计最多两个源视频，不能用混合字段绕过上限。
- URL 素材直接透传，不自动上传本地路径；先取得公网直链再调用。本地图片也可由调用方转换为 `data:image` Base64 后传 `image_url`。
- CLI 校验数量、明显非公网地址、URL 格式和图片 Base64 格式；对 `images` 内的 Base64 图片校验解码后≤8MB。
- CLI 不抓取远程素材，因此远程文件的≤8MB、视频≤1920×1080、实际图片/视频内容以及域名公网可达性由调用方及接口确认。不要把本地格式校验说成已实测文件大小或分辨率。
- `image_url`、首尾帧和 `images` 之间没有用户提供的互斥规则，脚本不擅自添加。未提供的选填字段不进入 JSON。

## 接口与查询

```text
POST https://apis.aimaxhug.cloud/v1/videos
GET  https://apis.aimaxhug.cloud/v1/videos/{model}/{task_id}
Authorization: Bearer <AIMAXHUG_API_KEY>
```

公开 [OpenAPI](https://apis.aimaxhug.cloud/openapi.json) 于 2026-11-02 查阅确认了通用提交与按模型查询的路径，以及生成参数原样透传的方式；此来源不单独证明上表全部 Omni 能力。

脚本提交后打印任务 ID，每 10 秒轮询一次，默认最多等待 30 分钟。HTTP 400 若带 `task_id`，继续查询同一任务，避免重复提交。V2V 响应回显的源视频 URL 不作为生成结果。设置 `SKILL_OUTPUT_DIR` 时沿用技能的产物自动保存方式。

```bash
python scripts/omni_video.py list-models --json
python scripts/omni_video.py status --model omni-fast --task-id "实际任务ID" --wait --json
```

## 调用示例

以下命令在技能根目录执行；`media.example.com` 是占位域名，调用前替换为实际素材直链。

```bash
# 文生视频，默认横屏和请求时长 10 秒
python scripts/omni_video.py run --model omni-fast --prompt "清晨的海浪涌向沙滩，镜头缓慢推进" --json

# 单张参考图；seconds 以字符串提交，实际输出仍约 10 秒
python scripts/omni_video.py run --model omni-fast-no-water --prompt "参考图片中的场景，镜头平稳环绕" --aspect-ratio 9:16 --seconds "10" --image-url https://media.example.com/reference.jpg --json

# 首尾帧
python scripts/omni_video.py run --model omni-fast-no-water --prompt "从首帧自然过渡到末帧" --first-image-url https://media.example.com/start.jpg --last-image-url https://media.example.com/end.jpg --duration 10 --json

# 两段源视频，分别使用 video 和 video_url
python scripts/omni_video.py run --model omni-fast-v2v-no-water --prompt "结合两段源视频的场景与动作，保持镜头连贯" --video https://media.example.com/first.mp4 --video-url https://media.example.com/second.mp4 --ratio 16:9 --json

# videos 数组与多参考图
python scripts/omni_video.py run --model omni-fast-v2v-no-water --prompt "参考人物形象和视频动作节奏" --videos https://media.example.com/first.mp4 https://media.example.com/second.mp4 --images https://media.example.com/person.jpg https://media.example.com/scene.jpg --json
```

Base64 单图示例（将占位内容替换为真实图片 Base64）：

```text
python scripts/omni_video.py run --model omni-fast --prompt "参考图片生成自然运动的视频" --image-url "data:image/png;base64,<真实图片Base64>" --json
```
