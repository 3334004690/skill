---
name: ai-media-skills-index
description: >
  AI 媒体工具技能索引，列出图像生成与编辑、视频与音频生成、声音克隆、百度搜索、短视频解析、文件上传、网页转图片和社交媒体数据查询的适用关键词与文件结构。
  具体流程见 SKILL.md，脚本在 scripts/。
---

# aimaxhug AI 媒体工具 — 技能索引

## 触发条件

> **适用范围：** 下表关键词用于识别可能相关的请求；是否使用本技能，应结合用户意图、明确指定的工具及当前环境中的可用能力判断。选用本技能后，读取 `SKILL.md` 中的对应工作流程。

| 类别 | 触发关键词 |
|------|-----------|
| 图像生成 | 生图、画图、AI绘图、文生图、生成图片、create image、generate image、text to image |
| 图片编辑 | 修改图片、编辑图片、换背景、风格迁移、图生图、image to image、image edit |
| 视频生成 | 生视频、文生视频、图生视频、首尾帧视频、参考视频驱动、AI视频、即梦视频、Seedance视频、MiniMax视频、MiniMax H3、generate video、text to video |
| 音频生成 | 文生音频、文字生音频、语音合成、声音克隆、AI音频、text to speech、TTS、generate audio |
| 百度搜索 | 百度搜索、AI搜索、联网搜索、网页搜索、搜索一下、web search、Baidu search、search the web |
| 短视频解析 | 短视频解析、视频解析、解析视频、提取视频链接、解析抖音、解析小红书、parse video、video parse |
| 社交媒体平台解析 | 自媒体平台解析、社交媒体平台解析、抖音账号搜索、抖音作品搜索、抖音榜单、抖音账号信息、抖音视频文案提取、小红书账号搜索、小红书作品搜索、小红书榜单 |
| 文件上传 | 上传文件、上传图片、upload file、upload image |
| 网页转图片 | 网页转图片、HTML转图片、网页截图、html to image、html screenshot |

## 文件结构

交付目录仅保留两层（根目录和一级子目录），`SKILL.md` 为主入口，包含平台要求的版本、显示名称及中英文描述。

```
SKILL.md                 ← 主技能入口（AI 读取）
INDEX.md                 ← 技能索引
AUTH.md                  ← API 授权配置说明
scripts/
  ai_image.py            ← 生图脚本
  minimax_video.py       ← 视频生成脚本（即梦 Seedance 2.0/2.5 Pro + MiniMax H3）
  ai_audio.py            ← 文生音频和声音克隆脚本（MiniMax Speech 2.8）
  ai_search.py           ← 百度 AI 搜索脚本（支持 GET / POST）
  video_parse.py         ← 短视频解析脚本（提取视频直链）
  html2image.py          ← HTML 转图片脚本
  upload.py              ← 上传脚本
  social_media.py        ← 社交媒体平台解析脚本
  xhs.py                 ← 小红书平台解析脚本
  shared_config.py       ← API Key 配置与项目路径
  shared_client.py       ← 公共 API 客户端
  shared_download.py     ← 产物下载与本地保存
  shared_markers.py      ← 宿主资源标记
  requirements.txt      ← Python 依赖
references/
  ai_image.md            ← 生图参考文档
  minimax_video.md       ← 视频生成参考文档（即梦 Seedance + MiniMax H3）
  ai_audio.md            ← 音频生成参考文档
  ai_search.md           ← 百度搜索参考文档
  video_parse.md         ← 短视频解析参考文档
  html2image.md          ← HTML 转图片参考文档
  upload.md              ← 上传参考文档
  social_media.md        ← 社交媒体平台解析参考文档
  xhs.md                 ← 小红书平台解析参考文档
```

读取 `SKILL.md` 按步骤执行。

## 社交媒体平台解析

触发词：自媒体平台解析、社交媒体数据、抖音账号搜索、抖音作品搜索、抖音榜单、抖音账号信息、抖音视频文案提取、小红书账号搜索、小红书作品搜索、小红书榜单、小红书评论、小红书视频文案。

- Script: `scripts/social_media.py`
- Reference: `references/social_media.md`
- 当前功能：抖音账号、作品、榜单、用户、AI 作品搜索及视频文案提取，详见 `references/social_media.md`

- Script: `scripts/xhs.py`
- Reference: `references/xhs.md`
- 当前功能：小红书账号、作品、榜单、评论、AI 作品搜索及视频文案提取，详见 `references/xhs.md`
