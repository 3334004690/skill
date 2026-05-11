---
name: image-generation
description: >
  图像生成技能。支持 Nano Banana / Nano Banana Pro / gpt-image-2 等模型。
  用户请求生图、图生图、图片编辑时调用。包含完整 Python 实现代码，
  AI 可直接复制运行。调用前需确保 AUTH.md Token 已验证。
---

# 图像生成 — 综合技能

## 模型注册表

所有模型共用同一端点，通过 `model` 字段区分：

| CLI Key | 模型名 | API 值 | 分辨率模式 |
|---------|--------|--------|-----------|
| `nano-banana` | Nano Banana | `gemini-3-pro-image-preview` | 手动 1k/2k/4k |
| `nano-banana-pro` | Nano Banana Pro | `gemini-3.1-flash-image-preview` | 手动 1k/2k/4k |
| `gpt-image-2` | gpt-image-2 | `gpt-image-2` | 自动按比例映射 |

### 触发路由

```
用户请求生图
  ├── 指定模型       ──→ 对应模型
  ├── 高画质/商业级   ──→ nano-banana-pro
  ├── 日常快速出图    ──→ nano-banana
  ├── 照片级写实/风格 ──→ gpt-image-2
  └── 未明确偏好      ──→ nano-banana（默认）
```

---

## 一、API 规范

### 统一端点

```
POST https://base-api.aimaxhug.com/api/v1/imageToImage
Authorization: Bearer sk-xxxxx
Content-Type: application/json
```

### 请求体结构

```json
{
    "model": "gemini-3-pro-image-preview",
    "prompt": "一只猫坐在窗边",
    "original_image": [
        {"tmp_url": "https://...", "name": "cat.jpg", "type": "image/jpeg", "size": 12345}
    ],
    "proportion": "16:9",
    "resolution": "2k"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model` | string | 是 | 模型 API 值（见注册表） |
| `prompt` | string | 是 | 图像描述或编辑指令 |
| `original_image` | array | 否 | 上传返回的 `{tmp_url,name,type,size}` 数组；不传=文生图 |
| `proportion` | string | 否 | 比例: `1:1`, `9:16`, `16:9`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `21:9` |
| `resolution` | string | 否 | `1k` / `2k` / `4k`（仅 manual 模式模型可用） |

### 响应格式

```json
{
    "status": 200,
    "code": 200,
    "data": {
        "imageUrl": "https://static.aimaxhug.com/..."
    },
    "message": "success"
}
```

---

## 二、模型参数约束

### Nano Banana（`gemini-3-pro-image-preview`）

| 属性 | 值 |
|------|-----|
| 分辨率模式 | manual — 用户可传 `resolution` 参数 |
| 支持分辨率 | `1k`, `2k`, `4k`（默认 `1k`） |
| 支持比例 | `1:1`, `9:16`, `16:9`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `21:9` |
| 定位 | 标准图像生成，速度快、性价比高 |

### Nano Banana Pro（`gemini-3.1-flash-image-preview`）

| 属性 | 值 |
|------|-----|
| 分辨率模式 | manual — 用户可传 `resolution` 参数 |
| 支持分辨率 | `1k`, `2k`, `4k`（默认 `1k`） |
| 支持比例 | `1:1`, `9:16`, `16:9`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `21:9` |
| 定位 | 高质量图像生成，Nano Banana 上位替代 |

### gpt-image-2（`gpt-image-2`）

| 属性 | 值 |
|------|-----|
| 分辨率模式 | auto — 不支持手动选，按比例自动映射 |
| 比例→分辨率 | `9:16`→`4k`, `16:9`→`4k`, `1:1`→`2k`, 其他→`1k` |
| 支持比例 | `1:1`, `9:16`, `16:9`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `21:9` |
| 定位 | 照片级写实、精准构图、艺术风格 |

---

## 三、完整代码实现

```python
#!/usr/bin/env python3
"""AI Image Generation — 直接复制运行"""

import json
import os
import sys
from pathlib import Path

import requests


# ============================================================
# 配置
# ============================================================

BASE_URL = "https://base-api.aimaxhug.com"
ENDPOINT = f"{BASE_URL}/api/v1/imageToImage"
UPLOAD_URL = f"{BASE_URL}/api/v2/upload/file"

# 从环境变量或参数获取
API_KEY = os.getenv("AIMAXHUG_API_KEY") or ""


def get_api_key():
    if API_KEY:
        return API_KEY
    raise SystemExit("Error: 请设置 AIMAXHUG_API_KEY 环境变量或 --api-key 参数")


# ============================================================
# 模型注册表
# ============================================================

MODELS = {
    "nano-banana": {
        "api_model": "gemini-3-pro-image-preview",
        "name": "Nano Banana",
        "resolution_mode": "manual",
        "resolutions": ["1k", "2k", "4k"],
    },
    "nano-banana-pro": {
        "api_model": "gemini-3.1-flash-image-preview",
        "name": "Nano Banana Pro",
        "resolution_mode": "manual",
        "resolutions": ["1k", "2k", "4k"],
    },
    "gpt-image-2": {
        "api_model": "gpt-image-2",
        "name": "gpt-image-2",
        "resolution_mode": "auto",
        "resolution_map": {"9:16": "4k", "16:9": "4k", "1:1": "2k"},
        "default_resolution": "1k",
    },
}

# 共同支持的比例
PROPORTIONS = ["1:1", "9:16", "16:9", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "21:9"]


# ============================================================
# 上传文件
# ============================================================

def upload_file(file_path):
    """上传本地文件，返回 {tmp_url, name, type, size}"""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    with open(path, "rb") as f:
        resp = requests.post(
            UPLOAD_URL,
            headers={"Authorization": f"Bearer {get_api_key()}"},
            files={"file": f},
            timeout=120,
        )

    data = resp.json()
    if resp.status_code != 200 or data.get("status") != 200:
        raise RuntimeError(f"上传失败: {data.get('message', resp.text)}")

    return data["data"]


def upload_files(paths):
    return [upload_file(p) for p in paths]


# ============================================================
# 生图主函数
# ============================================================

def generate(
    model_key,
    prompt,
    input_images=None,
    proportion=None,
    resolution=None,
    api_key=None,
):
    """生成图片

    参数:
        model_key: 模型 key（nano-banana / nano-banana-pro / gpt-image-2）
        prompt: 提示词
        input_images: [{tmp_url, name, type, size}, ...] 或 None（文生图）
        proportion: 比例，如 "16:9"
        resolution: 分辨率，仅 manual 模式模型可用
        api_key: API Key

    返回: {"success": bool, "image_url": str, ...}
    """
    global API_KEY
    if api_key:
        API_KEY = api_key

    model = MODELS.get(model_key)
    if not model:
        known = ", ".join(MODELS.keys())
        raise ValueError(f"未知模型 '{model_key}'，可选: {known}")

    # 构建请求体
    body = {"model": model["api_model"], "prompt": prompt.strip()}

    if input_images:
        body["original_image"] = input_images

    if proportion:
        if proportion not in PROPORTIONS:
            raise ValueError(f"不支持的比例 '{proportion}'，可选: {PROPORTIONS}")
        body["proportion"] = proportion

    # 分辨率处理
    if model["resolution_mode"] == "manual":
        r = resolution or model["resolutions"][0]
        if r not in model["resolutions"]:
            raise ValueError(f"不支持的分辨率 '{r}'，可选: {model['resolutions']}")
        body["resolution"] = r
    elif model["resolution_mode"] == "auto":
        rmap = model.get("resolution_map", {})
        if proportion and proportion in rmap:
            body["resolution"] = rmap[proportion]
        elif model.get("default_resolution"):
            body["resolution"] = model["default_resolution"]

    # 发送请求
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_api_key()}",
    }

    try:
        resp = requests.post(ENDPOINT, headers=headers, json=body, timeout=120)
    except requests.exceptions.Timeout:
        return {"success": False, "error": "请求超时"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "网络连接失败"}

    try:
        data = resp.json()
    except json.JSONDecodeError:
        return {"success": False, "error": f"响应解析失败: {resp.text[:200]}"}

    if resp.status_code != 200:
        return {"success": False, "error": data.get("message", f"HTTP {resp.status_code}")}

    image_url = data.get("data", {}).get("imageUrl")
    if not image_url:
        return {"success": False, "error": "返回数据中没有 imageUrl"}

    return {
        "success": True,
        "image_url": image_url,
        "model": model["name"],
        "api_model": model["api_model"],
        "prompt": prompt,
        "proportion": proportion,
        "resolution": body.get("resolution"),
    }


# ============================================================
# CLI 入口
# ============================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="AI 图像生成")
    parser.add_argument("--api-key", help="API Key")
    parser.add_argument("--model", default="nano-banana", choices=list(MODELS.keys()),
                        help="模型 key")
    parser.add_argument("--prompt", required=True, help="提示词")
    parser.add_argument("--proportion", help=f"比例: {', '.join(PROPORTIONS)}")
    parser.add_argument("--resolution", help="分辨率: 1k/2k/4k（仅 manual 模型）")
    parser.add_argument("--input-images", nargs="+", help="本地图片路径")
    parser.add_argument("--input-urls", nargs="+", help="已上传的 tmp_url")
    parser.add_argument("-o", "--output", help="下载路径")

    args = parser.parse_args()

    # API Key
    global API_KEY
    if args.api_key:
        API_KEY = args.api_key

    # 上传
    images = []
    if args.input_images:
        print("正在上传文件...", file=sys.stderr)
        images = upload_files(args.input_images)
    if args.input_urls:
        for url in args.input_urls:
            images.append({"tmp_url": url, "name": "", "type": "", "size": 0})

    # 生图
    print("正在生成图片...", file=sys.stderr)
    result = generate(args.model, args.prompt, images or None,
                      args.proportion, args.resolution)

    if not result["success"]:
        print(f"失败: {result['error']}", file=sys.stderr)
        sys.exit(1)

    print(f"\n✅ 生成成功!")
    print(f"   模型: {result['model']} ({result['api_model']})")
    print(f"   URL: {result['image_url']}")
    if result.get("proportion"):
        print(f"   比例: {result['proportion']}")
    if result.get("resolution"):
        print(f"   分辨率: {result['resolution']}")

    if args.output:
        r = requests.get(result["image_url"])
        r.raise_for_status()
        with open(args.output, "wb") as f:
            f.write(r.content)
        print(f"   已保存: {args.output}")


if __name__ == "__main__":
    main()
```

---

## 四、使用示例

### 文生图

```bash
python -c "
import ai_image
result = ai_image.generate('nano-banana', '一只橘猫坐在窗边', proportion='16:9', resolution='2k')
print(result['image_url'])
"
```

### 图生图（自动上传本地图片）

```bash
python ai_image.py --model nano-banana-pro --prompt "换成赛博朋克风格" \
    --input-images photo.jpg --proportion 16:9 --resolution 4k
```

### gpt-image-2（无需传分辨率）

```bash
python ai_image.py --model gpt-image-2 --prompt "一只猫" --proportion 1:1
```

### 查看可用模型

```python
for key, cfg in MODELS.items():
    print(f"{key}: {cfg['name']} ({cfg['api_model']})")
```

---

## 五、错误处理

| 场景 | 处理方式 |
|------|----------|
| 401 Token 无效 | 清除 Token，触发 AUTH.md 重新授权 |
| 文件不存在 | 提示用户检查路径 |
| 上传超时 | 建议压缩图片后重试 |
| 网络连接失败 | 检查网络/服务状态 |
| 不支持的比例/分辨率 | 提示可用选项 |

---

## 六、上传接口

上传文件使用独立接口：

```
POST https://base-api.aimaxhug.com/api/v2/upload/file
Authorization: Bearer sk-xxxxx
Content-Type: multipart/form-data

file: <文件二进制>
```

返回 `{tmp_url, name, type, size}` 直接传入 `original_image` 参数（数组包裹）。
