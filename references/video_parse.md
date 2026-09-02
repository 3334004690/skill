# 短视频解析模块

使用 `scripts/video_parse.py` 将短视频分享链接解析为可播放的视频直链。

## Endpoint and Authentication

- Endpoint: `https://apis.aimaxhug.cloud/v1/video-parse`
- Method: POST
- Headers: `Authorization: Bearer <AIMAXHUG_API_KEY>`、`Content-Type: application/json`
- Body: `{ "url": "短视频分享链接" }`

支持平台：抖音、小红书、快手、B站、微博、皮皮虾、知乎视频、西瓜视频、TikTok、YouTube。

## Usage

```bash
# 使用 --url
python {baseDir}/scripts/video_parse.py run --url "https://v.douyin.com/3nuNZF203Kw/"

# 使用位置参数
python {baseDir}/scripts/video_parse.py run "https://v.douyin.com/3nuNZF203Kw/"

# 保留完整 JSON 响应
python {baseDir}/scripts/video_parse.py run --url "https://v.douyin.com/3nuNZF203Kw/" --json
```

## Response

```json
{
  "success": true,
  "message": "",
  "data": {
    "request_id": "aadf168c8f304d04",
    "url": "https://www.douyin.com/aweme/v1/play/?video_id=...",
    "title": "视频标题",
    "platform": "抖音"
  }
}
```

向用户回答时可以使用解析结果中的标题、平台和视频直链；不要把分享链接误当作解析后的直链。
