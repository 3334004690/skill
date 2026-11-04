# Upload Module

Upload local images, videos, audio, or other files to Aimaxhug and return temp URL + metadata for media generation.

## When to Use

User provides local files that need to be used as generation references. The AI handles uploading and fills the returned references into the generation request. This includes image-to-image input, Muse first/last frames, reference images, and continuation videos. Existing usable media URLs are used directly without re-uploading.

For ordinary creative requests, keep intermediate media URLs and upload metadata in the execution flow. Tell the user which supplied materials are being used, without asking them to create URLs or showing technical upload fields. The final generated artwork/video is still presented normally; provide technical details when explicitly requested.

## Subcommands

| Subcommand | When to use |
|------------|-------------|
| `run` | **Default.** Upload file(s) and print result |

## 上传前压缩

本地参考图片、视频统一通过 `shared_client.py` 的公共上传入口处理，包含独立上传、图片生成内置上传和即梦 2.5 的素材上传。MiniMax H3 将本地素材编码为内嵌引用时也先复用同一压缩模块，不通过大体积内嵌内容绕过压缩。AI 无需另做压缩调用，避免重复压缩。

- **图片**：固定按质量 **40** 编码，保留原尺寸与完整构图，不因文件体积继续缩小。普通图片转 JPEG，透明图和动画转 WebP，保留透明度和动画，纠正拍摄方向；不保留无关元数据。
- **视频**：固定用 H.264 / CRF **40** 编码，保留源视频分辨率、帧率、时长与声音，不裁剪、变速或静音。H.264 对奇数宽高最多补 1 像素，不缩小主体画面；声音转兼容的 AAC，复查时长和音轨数量。
- **不设 1MB、2MB 等体积门槛**：编码后超过这些大小照常上传，不为满足某个大小额外降质、缩尺寸、降帧率或改为码率压缩。“40”是固定编码设置，不是压缩到原体积的 40%，也不保证固定大小；优先让 AI 识别画面内容。
- 压缩只生成临时副本，成功或失败后都会清理；用户原文件不改动。上传的文件名后缀、类型和内容采用压缩结果，服务器返回的 `tmp_url` 对应实际上传的压缩文件，后续生成使用这个地址。
- 编码失败、时长异常或声音丢失时停止上传并说明真实问题；不因压缩后的文件仍较大而报错，也不悄悄改为原文件上传或截短视频。模型自身已有的素材体积上限仍按该模型规则执行，不与本压缩设置混淆。
- 音频、HTML 和其他非图片/视频文件不压缩。生成的最终图片为显示而转存时显式保留原质量；此规则面向参考素材，不降低成品交付清晰度。用户已有可用素材链接直接使用，不为压缩重新上传。

依赖已声明在 `scripts/requirements.txt`：Pillow 处理图片，imageio-ffmpeg 提供视频编码器；优先使用 PATH 中已有的 FFmpeg。时长检测优先使用 ffprobe，缺少独立 ffprobe 时可使用同一视频组件读取时长。AI 使用项目自检安装缺少的依赖，技术细节不展示在普通创作菜单中。

离线回归验证包含真实图片/视频压缩和模拟 HTTP 上传，不调用付费生成接口：

```bash
python -m unittest discover -s scripts -p test_media_upload.py -v
```

## Usage

```bash
python {baseDir}/scripts/upload.py run <file_paths...> [options]
```

## Examples

```bash
# Upload single file
python {baseDir}/scripts/upload.py run photo.jpg

# Upload multiple files
python {baseDir}/scripts/upload.py run photo1.jpg photo2.png

# JSON output for scripting
python {baseDir}/scripts/upload.py run photo.jpg --json

# Video upload (for Muse continuation, check local duration before uploading)
python {baseDir}/scripts/upload.py run source.mp4 --json
```

## Options

| Option | Description |
|--------|-------------|
| `files` | Local file path(s) to upload (required, one or more) |
| `--json` | Output results as JSON |

## Output

With `--json`, the script returns an array with one data object per file, in input order. Each object includes the fields below; a `markedUrl` may also be present. `ai_image.py --input-images` uses the metadata object. Muse takes only each object's `tmp_url` string and fills `input_reference`, `last_frame`, `images`, or `video_url` according to the supplied material's role. See [Muse material handling](muse_video.md#ai-自动处理参考素材).

```json
{
    "tmp_url": "https://static.aimaxhug.com/xxx.jpg",
    "name": "xxx.jpg",
    "type": "image/jpeg",
    "size": 123456
}
```
