---
name: gemini-image-edit
description: >
  Gemini 图像生成与编辑核心技能。当用户需要生成新图像、编辑已有图片、风格转换、背景替换、人物编辑、
  图像增强、超分辨率等任何图像处理任务时调用。支持纯文字生成（text-to-image）和图文结合编辑（image-to-image）。
  包含完整的 API 调用逻辑、参数说明、错误处理和输出展示方案。
  调用本 Skill 前必须确保 AUTH.md 中的 Token 已验证有效。
---

# Gemini 图像生成与编辑 — 完整技能手册

## 技能概述

| 属性 | 值 |
|------|----|
| 底层模型 | `gemini-3.1-flash-image-preview` |
| 服务端点 | `https://aimaxhug.com` |
| 支持格式 | PNG、JPEG、JPG、WEBP（输入）/ PNG（输出） |
| 认证方式 | Bearer Token（见 AUTH.md） |

---

## 一、能力范围

### 1.1 文生图（Text → Image）
用户只提供文字描述，不上传图片：
- 场景图、风景画、概念图
- 产品效果图、广告图
- 艺术插画、抽象图形

### 1.2 图像编辑（Image + Text → Image）
用户上传图片并提供编辑指令：
- **背景替换**：换背景、去背景、添加场景
- **风格迁移**：照片转油画 / 水彩 / 漫画 / 像素风
- **人物编辑**：改变表情、服装、发色、动作
- **对象操作**：添加 / 删除 / 替换图中物体
- **图像增强**：超分辨率、去噪、老照片修复
- **合成操作**：多人合照、添加文字效果

---

## 二、API 参数完整说明

### 2.1 请求端点

```
POST https://aimaxhug.com/v1/models/gemini-3.1-flash-image-preview:generateContent
```

### 2.2 请求头

```python
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"  # 从 AUTH.md get_api_key() 获取
}
```

### 2.3 请求体结构

```python
payload = {
    "contents": [
        {
            "parts": [
                # 部分 A：文字提示词（必填）
                {"text": "<用户的图像描述或编辑指令>"},
                
                # 部分 B：参考图片（可选，编辑模式必填）
                # 仅在用户上传了图片时加入
                {
                    "inline_data": {
                        "mime_type": "<image/jpeg | image/png | image/webp>",
                        "data": "<base64 编码的图片数据>"
                    }
                }
            ]
        }
    ],
    "generationConfig": {
        "responseModalities": ["TEXT", "IMAGE"],
        "imageConfig": {
            "aspectRatio": "<宽高比>",   # 可选，见参数表
            "imageSize": "<分辨率>"       # 可选，见参数表
        }
    }
}
```

### 2.4 参数枚举值

#### `aspectRatio`（宽高比）

| 值 | 描述 | 推荐使用场景 |
|----|------|-------------|
| `"1:1"` | 正方形 | 头像、社交媒体帖子、产品图 |
| `"4:5"` | 竖版略宽 | Instagram 竖版帖子 |
| `"2:3"` | 标准竖版 | 书籍封面、海报 |
| `"9:16"` | 手机竖屏 | 短视频封面、手机壁纸、Stories |
| `"3:4"` | 经典竖版 | 传统照片冲印比例 |
| `"4:3"` | 经典横版 | 传统电视、PPT 图片 |
| `"3:2"` | 标准横版 | 相机照片默认比例 |
| `"5:4"` | 略宽横版 | **默认值**，通用横版 |
| `"16:9"` | 宽屏横版 | 电脑壁纸、视频缩略图、横幅 |
| `"21:9"` | 超宽屏 | 电影感横幅、全景图 |
| `"4:1"` | 超宽条幅 | 网站 Banner、全景横幅 |
| `"1:4"` | 超高竖版 | 竖型 Banner、信息图 |
| `"8:1"` | 极宽条幅 | 网站顶部大图 |
| `"1:8"` | 极高竖版 | 特殊竖型展示 |

#### `imageSize`（输出分辨率）

| 值 | 描述 | 适用场景 | 生成速度 |
|----|------|----------|----------|
| `"512"` | 低分辨率 | 快速预览、缩略图 | ⚡ 最快 |
| `"1K"` | 标准清晰度 | 网页展示、社交媒体 | 🚀 快 |
| `"2K"` | 高清 | **默认值**，印刷级展示 | ⏱ 中等 |
| `"4K"` | 超高清 | 专业印刷、大屏展示 | 🐢 较慢 |

---

## 三、完整实现代码

### 3.1 工具函数

```python
import requests
import base64
import json
import os
import re
from pathlib import Path
from datetime import datetime


# ============================================================
# Token 管理（与 AUTH.md 联动）
# ============================================================

SESSION_CONFIG = {
    "GEMINI_API_KEY": None,
    "BASE_URL": "https://aimaxhug.com",
    "MODEL": "gemini-3.1-flash-image-preview"
}


def get_api_key() -> str | None:
    """读取 API Key，优先级：内存 > 环境变量 > .env 文件"""
    if SESSION_CONFIG.get("GEMINI_API_KEY"):
        return SESSION_CONFIG["GEMINI_API_KEY"]
    key = os.getenv("GEMINI_API_KEY")
    if key:
        SESSION_CONFIG["GEMINI_API_KEY"] = key
        return key
    if os.path.exists(".env"):
        with open(".env") as f:
            for line in f:
                if line.startswith("GEMINI_API_KEY="):
                    k = line.split("=", 1)[1].strip()
                    if k:
                        SESSION_CONFIG["GEMINI_API_KEY"] = k
                        return k
    return None


def set_api_key(token: str):
    """保存 Token 到内存"""
    SESSION_CONFIG["GEMINI_API_KEY"] = token.strip()


# ============================================================
# 图片处理工具
# ============================================================

def encode_image_to_base64(image_source) -> tuple[str, str]:
    """
    将图片转为 base64 字符串
    
    支持：
    - 文件路径（str / Path）
    - bytes 数据
    - 已是 base64 字符串
    
    返回: (base64_string, mime_type)
    """
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif"
    }
    
    if isinstance(image_source, (str, Path)):
        path = Path(image_source)
        mime_type = mime_map.get(path.suffix.lower(), "image/jpeg")
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        return data, mime_type
    
    elif isinstance(image_source, bytes):
        data = base64.b64encode(image_source).decode("utf-8")
        return data, "image/jpeg"
    
    elif isinstance(image_source, str) and len(image_source) > 200:
        # 已是 base64
        return image_source, "image/jpeg"
    
    raise ValueError(f"不支持的图片来源类型: {type(image_source)}")


def save_output_image(base64_data: str, output_path: str = None) -> str:
    """
    将 base64 图片数据保存为文件
    
    参数:
        base64_data: base64 编码的图片数据
        output_path: 保存路径（可选，默认自动生成）
    
    返回: 保存的文件路径
    """
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"gemini_output_{timestamp}.png"
    
    img_bytes = base64.b64decode(base64_data)
    with open(output_path, "wb") as f:
        f.write(img_bytes)
    
    return output_path
```

### 3.2 核心 API 调用函数

```python
def generate_image(
    prompt: str,
    image_source=None,
    aspect_ratio: str = "5:4",
    resolution: str = "2K",
    output_path: str = None,
    api_key: str = None
) -> dict:
    """
    Gemini 图像生成 / 编辑核心函数
    
    参数:
        prompt        (str, 必填)  图像描述或编辑指令
        image_source  (可选)       参考图片（文件路径 / bytes / base64）
                                   不提供则为纯文字生图
        aspect_ratio  (str, 可选)  输出宽高比，默认 "5:4"
                                   可选: "1:1","9:16","16:9","4:3","3:4",
                                         "2:3","3:2","21:9","4:1","1:4" 等
        resolution    (str, 可选)  输出分辨率，默认 "2K"
                                   可选: "512","1K","2K","4K"
        output_path   (str, 可选)  输出文件路径，默认自动命名
        api_key       (str, 可选)  手动传入 API Key（通常由 get_api_key() 自动获取）
    
    返回:
        {
            "success": bool,
            "image_path": str,         # 保存的图片路径（成功时）
            "image_base64": str,        # 图片 base64 数据（成功时）
            "mime_type": str,           # 图片 MIME 类型（成功时）
            "text_response": str,       # 模型文字回复（若有）
            "error": str,              # 错误信息（失败时）
            "error_code": int,         # HTTP 状态码（失败时）
            "raw_response": dict       # 完整原始响应（调试用）
        }
    """
    # 1. 获取 Token
    key = api_key or get_api_key()
    if not key:
        return {
            "success": False,
            "error": "未找到 API Token，请先执行授权流程（见 AUTH.md）",
            "error_code": 401
        }
    
    # 2. 参数验证
    valid_ratios = {
        "1:1","1:4","1:8","2:3","3:2","3:4","4:1","4:3",
        "4:5","5:4","8:1","9:16","16:9","21:9"
    }
    valid_resolutions = {"512", "1K", "2K", "4K"}
    
    if aspect_ratio not in valid_ratios:
        return {
            "success": False,
            "error": f"无效的 aspect_ratio: '{aspect_ratio}'。"
                     f"可选值: {', '.join(sorted(valid_ratios))}"
        }
    
    if resolution not in valid_resolutions:
        return {
            "success": False,
            "error": f"无效的 resolution: '{resolution}'。"
                     f"可选值: {', '.join(sorted(valid_resolutions))}"
        }
    
    # 3. 构建请求 parts
    parts = [{"text": prompt}]
    
    if image_source is not None:
        try:
            img_b64, mime_type = encode_image_to_base64(image_source)
            parts.append({
                "inline_data": {
                    "mime_type": mime_type,
                    "data": img_b64
                }
            })
        except Exception as e:
            return {"success": False, "error": f"图片处理失败: {str(e)}"}
    
    # 4. 构建完整 payload
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": {
                "aspectRatio": aspect_ratio,
                "imageSize": resolution
            }
        }
    }
    
    # 5. 发送请求
    url = (
        f"{SESSION_CONFIG['BASE_URL']}/v1/models/"
        f"{SESSION_CONFIG['MODEL']}:generateContent"
    )
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}"
    }
    
    try:
        response = requests.post(
            url, 
            headers=headers, 
            json=payload,
            timeout=120  # 4K 生成可能较慢
        )
    except requests.Timeout:
        return {
            "success": False,
            "error": "请求超时（>120秒），建议使用较低分辨率或稍后重试",
            "error_code": 408
        }
    except requests.ConnectionError:
        return {
            "success": False,
            "error": "网络连接失败，请检查网络或服务端点配置",
            "error_code": 0
        }
    
    # 6. 处理错误响应
    if response.status_code != 200:
        error_map = {
            400: "请求参数错误（INVALID_ARGUMENT），请检查 prompt 和参数格式",
            401: "Token 无效或已过期（UNAUTHENTICATED），请重新授权",
            403: "无权限访问该模型（PERMISSION_DENIED），请检查账户套餐",
            429: "请求频率超限（RESOURCE_EXHAUSTED），请稍后重试",
            500: "服务端内部错误（INTERNAL），请稍后重试"
        }
        error_msg = error_map.get(
            response.status_code,
            f"未知错误: {response.text[:200]}"
        )
        
        # 401 时触发重新授权
        if response.status_code == 401:
            SESSION_CONFIG["GEMINI_API_KEY"] = None
        
        return {
            "success": False,
            "error": error_msg,
            "error_code": response.status_code,
            "raw_response": response.text
        }
    
    # 7. 解析响应
    try:
        result = response.json()
    except json.JSONDecodeError:
        return {
            "success": False,
            "error": "响应解析失败，服务端返回了非 JSON 格式",
            "raw_response": response.text
        }
    
    # 8. 提取内容
    text_parts = []
    image_data = None
    image_mime = "image/png"
    
    # 响应结构：result.candidates[0].content.parts
    candidates = result.get("candidates", [])
    if not candidates:
        # 兼容直接返回 parts 的格式
        parts_list = result.get("parts", [])
    else:
        parts_list = candidates[0].get("content", {}).get("parts", [])
    
    for part in parts_list:
        if "text" in part:
            text_parts.append(part["text"])
        elif "inlineData" in part:
            image_data = part["inlineData"]["data"]
            image_mime = part["inlineData"].get("mimeType", "image/png")
    
    if not image_data:
        return {
            "success": False,
            "error": "API 响应中未找到图像数据，可能是内容被过滤",
            "text_response": "\n".join(text_parts),
            "raw_response": result
        }
    
    # 9. 保存图片
    saved_path = save_output_image(image_data, output_path)
    
    return {
        "success": True,
        "image_path": saved_path,
        "image_base64": image_data,
        "mime_type": image_mime,
        "text_response": "\n".join(text_parts),
        "raw_response": result
    }
```

### 3.3 批量生成（高级用法）

```python
def generate_images_batch(
    tasks: list[dict],
    api_key: str = None
) -> list[dict]:
    """
    批量生成图片
    
    参数:
        tasks: 任务列表，每项为 generate_image() 的参数 dict
               例: [
                 {"prompt": "...", "aspect_ratio": "16:9", "resolution": "2K"},
                 {"prompt": "...", "image_source": "path/to/img.jpg"}
               ]
    
    返回: 与 tasks 等长的结果列表
    """
    results = []
    key = api_key or get_api_key()
    
    for i, task in enumerate(tasks):
        print(f"处理任务 {i+1}/{len(tasks)}: {task.get('prompt', '')[:50]}...")
        result = generate_image(api_key=key, **task)
        results.append(result)
        
        if not result["success"]:
            print(f"  ❌ 失败: {result['error']}")
        else:
            print(f"  ✅ 已保存: {result['image_path']}")
    
    return results
```

---

## 四、AI 调用流程（标准操作步骤）

AI 在接收到图像请求时，严格按以下步骤执行：

```
┌─────────────────────────────────────────────────────────────┐
│ 步骤 1：检查 Token                                           │
│   调用 get_api_key()                                         │
│   → None：执行 AUTH.md 授权流程后返回步骤 1                  │
│   → 有效：进入步骤 2                                         │
├─────────────────────────────────────────────────────────────┤
│ 步骤 2：解析用户意图                                         │
│   • 提取 prompt（用户描述 / 编辑指令）                       │
│   • 检测是否有上传图片                                       │
│   • 识别宽高比偏好（见 INDEX.md 参数映射表）                  │
│   • 识别分辨率偏好                                           │
├─────────────────────────────────────────────────────────────┤
│ 步骤 3：提示词优化（可选但推荐）                              │
│   将用户的简短描述扩展为更具体的英文提示词                    │
│   示例：                                                     │
│   用户: "一只猫坐在窗边"                                     │
│   优化: "A fluffy orange tabby cat sitting on a windowsill,  │
│          warm sunlight streaming in, cozy interior,          │
│          shallow depth of field, photorealistic"             │
├─────────────────────────────────────────────────────────────┤
│ 步骤 4：调用 generate_image()                                │
│   传入所有解析到的参数                                       │
├─────────────────────────────────────────────────────────────┤
│ 步骤 5：处理结果                                             │
│   → success=True：展示图片（见第五章）                       │
│   → success=False：按错误类型处理（见第六章）                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 五、输出展示规范

### 5.1 成功时的标准输出

```python
def display_result(result: dict, user_prompt: str):
    """格式化展示生成结果"""
    
    if not result["success"]:
        print(f"❌ 生成失败：{result['error']}")
        return
    
    # 向用户展示
    print(f"""
✅ 图像生成成功！

📁 已保存至：{result['image_path']}
📐 文件大小：{os.path.getsize(result['image_path']) / 1024:.1f} KB
""")
    
    if result.get("text_response"):
        print(f"🤖 模型描述：{result['text_response']}")
    
    # 在支持图片渲染的环境中展示
    try:
        from IPython.display import Image, display
        display(Image(result["image_path"]))
    except ImportError:
        print(f"（请在文件管理器中打开 {result['image_path']} 查看）")
```

### 5.2 AI 向用户汇报格式（文字回复模板）

当图像生成成功时，AI 应按以下格式回复用户：

```
✅ 图像已生成！

🖼️ **内容**：[简述生成了什么]
📐 **规格**：[宽高比] × [分辨率]
💾 **文件**：[文件路径]

[如果模型有文字说明，此处引用]

需要调整吗？您可以告诉我：
• 修改构图（"把主体放在右边"）
• 调整风格（"更写实"/"更卡通"）
• 更换比例（"改成竖版 9:16"）
• 提升画质（"换 4K 分辨率"）
```

---

## 六、错误处理详细指南

### 6.1 错误代码处理表

| 错误码 | 场景 | AI 行为 | 用户提示 |
|--------|------|---------|----------|
| 401 | Token 失效 | 清除 Token，调用 AUTH.md | "Token 已失效，请重新提供 API Key" |
| 403 | 权限不足 | 不重试 | "账户无权访问该模型，请检查套餐" |
| 400 | 参数错误 | 检查并修正参数后重试 | "参数格式错误，正在自动修正..." |
| 429 | 频率限制 | 等待后提示用户 | "请求过于频繁，请 30 秒后重试" |
| 500 | 服务端错误 | 最多重试 2 次 | "服务暂时异常，正在重试..." |
| 408/超时 | 请求超时 | 建议降低分辨率 | "生成超时，建议改用 2K 分辨率" |
| 0 | 网络错误 | 提示检查网络 | "网络连接失败，请检查网络设置" |
| 内容过滤 | 无图片返回 | 提示修改 prompt | "内容可能触发安全过滤，请调整描述" |

### 6.2 自动重试逻辑

```python
import time

def generate_image_with_retry(
    prompt: str,
    max_retries: int = 3,
    retry_delay: float = 5.0,
    **kwargs
) -> dict:
    """带自动重试的图像生成"""
    
    retryable_codes = {500, 429}
    
    for attempt in range(1, max_retries + 1):
        result = generate_image(prompt=prompt, **kwargs)
        
        if result["success"]:
            return result
        
        error_code = result.get("error_code", 0)
        
        # 不可重试的错误直接返回
        if error_code in {400, 401, 403}:
            return result
        
        # 可重试的错误
        if error_code in retryable_codes and attempt < max_retries:
            wait = retry_delay * attempt  # 指数退避
            print(f"第 {attempt} 次重试失败，{wait}秒后重试...")
            time.sleep(wait)
            continue
        
        return result
    
    return result
```

---

## 七、使用示例

### 示例 1：文生图

```python
# 用户说："生成一张赛博朋克风格的城市夜景"
result = generate_image(
    prompt="Cyberpunk cityscape at night, neon lights reflecting on wet streets, "
           "towering skyscrapers, flying cars, purple and blue color palette, "
           "cinematic lighting, photorealistic, 8K detail",
    aspect_ratio="16:9",
    resolution="2K"
)
```

### 示例 2：图片编辑

```python
# 用户上传了一张照片，说："把背景换成日落海滩"
result = generate_image(
    prompt="Replace the background with a beautiful sunset beach scene, "
           "golden hour lighting, keep the subject unchanged, realistic blending",
    image_source="user_photo.jpg",
    aspect_ratio="4:3",
    resolution="2K"
)
```

### 示例 3：风格迁移

```python
# 用户说："把这张照片变成吉卜力动画风格"
result = generate_image(
    prompt="Convert this photo to Studio Ghibli anime art style, "
           "soft watercolor colors, whimsical atmosphere, detailed background",
    image_source="photo.jpg",
    aspect_ratio="16:9",
    resolution="2K"
)
```

### 示例 4：图像增强

```python
# 用户说："把这张图提升到 4K 分辨率"
result = generate_image(
    prompt="Upscale and enhance this image to ultra-high resolution, "
           "increase sharpness and detail, reduce noise, improve clarity",
    image_source="low_res.jpg",
    aspect_ratio="16:9",  # 保持原比例
    resolution="4K"
)
```

---

## 八、常见问题

**Q: 生成的图片是什么格式？**
A: 固定输出为 PNG 格式，通过 `image_path` 返回本地保存路径。

**Q: 能同时上传多张参考图吗？**
A: 当前 API 每次支持最多14张参考图。

**Q: 提示词用中文还是英文？**
A: 两者均支持，但英文提示词通常能获得更精准的结果。AI 应自动将中文提示优化为英文。

**Q: 如何保持图中人物不变只改背景？**
A: 在提示词中明确指定 "keep the subject/person unchanged, only change the background"。

**Q: 生成超时怎么办？**
A: 4K 分辨率生成约需 30-60 秒。建议先用 2K 预览，满意后再升 4K。

---

## 九、兼容性说明

本 Skill 设计为**通用接口**，兼容以下使用场景：

| 平台 / 宿主 | 兼容状态 | 备注 |
|-------------|----------|------|
| Claude.ai 网页版 | ✅ 完全兼容 | 图片通过文件路径展示 |
| Claude 桌面应用 | ✅ 完全兼容 | 同上 |
| Claude Code | ✅ 完全兼容 | 支持文件系统操作 |
| Cowork | ✅ 完全兼容 | 同上 |
| 自定义 API 接入 | ✅ 兼容 | 调整 BASE_URL 即可 |
| Jupyter Notebook | ✅ 兼容 | IPython.display 自动渲染 |
| 命令行脚本 | ✅ 兼容 | 保存为本地文件 |