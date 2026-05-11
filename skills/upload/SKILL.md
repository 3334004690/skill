---
name: image-upload
description: >
  图片上传技能。当用户需要上传图片文件到服务器、获取临时访问URL时调用。
  上传前必须确保 AUTH.md 中的 Token 已验证有效。上传成功后返回临时URL，
  供后续图像编辑、生成等操作使用。
---

# 图片上传 — 完整技能手册

## 技能概述

| 属性 | 值 |
|------|----|
| 服务端点 | `https://base-api.aimaxhug.com` |
| 请求方式 | `multipart/form-data` |
| 认证方式 | Bearer Token（与 Gemini 图像服务共用，见 AUTH.md） |
| 支持格式 | JPEG、PNG、WEBP、GIF 等常见图片格式 |

---

## 一、API 规范

### 1.1 请求端点

```
POST https://base-api.aimaxhug.com/api/v2/upload/file
```

### 1.2 请求头

```
Authorization: Bearer sk-xxxxx
Content-Type: multipart/form-data
```

### 1.3 请求体

```
form-data:
  file: <文件二进制数据>
```

### 1.4 响应格式

**成功（200）：**
```json
{
    "status": 200,
    "code": 200,
    "data": {
        "tmp_url": "https://static.aimaxhug.com/ai-file-update-dyl/2026/05/11/xxx.jpg",
        "name": "2026-05-11T02-29-02-xxx.jpg",
        "type": "image/jpeg",
        "size": 391493
    },
    "message": "文件上传成功"
}
```

**缺少 API Key（401）：**
```json
{
    "status": 401,
    "code": 401,
    "message": "缺少API Key，请在Authorization头中提供Bearer token或在请求体中提供apiKey字段",
    "error": { "code": "INVALID_API_KEY" }
}
```

**API Key 无效（401）：**
```json
{
    "status": 401,
    "code": 401,
    "message": "API Key 无效，请检查后重试",
    "error": { "code": "INVALID_API_KEY" }
}
```

---

## 二、完整实现代码

### 2.1 Token 管理（与 AUTH.md 联动）

```python
import requests
import os

SESSION_CONFIG = {
    "GEMINI_API_KEY": None,
    "UPLOAD_BASE_URL": "https://base-api.aimaxhug.com"
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
```

### 2.2 上传文件核心函数

```python
def upload_file(
    file_path: str,
    api_key: str = None
) -> dict:
    """
    上传图片文件到服务器，获取临时访问 URL

    参数:
        file_path (str, 必填)  本地文件路径
        api_key   (str, 可选)  手动传入 API Key（通常由 get_api_key() 自动获取）

    返回:
        {
            "success": bool,
            "tmp_url": str,          # 临时访问 URL（成功时）
            "name": str,             # 文件名（成功时）
            "type": str,             # MIME 类型（成功时）
            "size": int,             # 文件大小（成功时）
            "error": str,            # 错误信息（失败时）
            "error_code": int        # HTTP 状态码（失败时）
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

    # 2. 检查本地文件是否存在
    if not os.path.exists(file_path):
        return {
            "success": False,
            "error": f"文件不存在: {file_path}",
            "error_code": 404
        }

    # 3. 发送上传请求
    url = f"{SESSION_CONFIG['UPLOAD_BASE_URL']}/api/v2/upload/file"
    headers = {
        "Authorization": f"Bearer {key}"
    }

    try:
        with open(file_path, "rb") as f:
            files = {"file": f}
            response = requests.post(
                url,
                headers=headers,
                files=files,
                timeout=60
            )
    except requests.Timeout:
        return {
            "success": False,
            "error": "上传超时（>60秒），请检查文件大小或网络连接",
            "error_code": 408
        }
    except requests.ConnectionError:
        return {
            "success": False,
            "error": "网络连接失败，请检查本地服务是否启动或网络连接",
            "error_code": 0
        }
    except FileNotFoundError:
        return {
            "success": False,
            "error": f"文件读取失败: {file_path}",
            "error_code": 404
        }

    # 4. 处理错误响应
    if response.status_code != 200:
        error_msg = ""
        try:
            resp_data = response.json()
            error_msg = resp_data.get("message", response.text[:200])
            
            # 401 时触发重新授权
            if response.status_code == 401:
                SESSION_CONFIG["GEMINI_API_KEY"] = None
                if resp_data.get("error", {}).get("code") == "INVALID_API_KEY":
                    error_msg = "API Key 无效，请检查后重试"
        except Exception:
            error_msg = response.text[:200]

        return {
            "success": False,
            "error": error_msg,
            "error_code": response.status_code
        }

    # 5. 解析成功响应
    try:
        result = response.json()
        data = result.get("data", {})
        
        return {
            "success": True,
            "tmp_url": data.get("tmp_url"),
            "name": data.get("name"),
            "type": data.get("type"),
            "size": data.get("size"),
            "message": result.get("message", "文件上传成功")
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"响应解析失败: {str(e)}",
            "error_code": 500
        }
```

### 2.3 上传并获取路径（快捷函数）

```python
def upload_and_get_url(
    file_path: str,
    api_key: str = None
) -> str | None:
    """
    上传图片并直接返回临时 URL 的快捷函数

    参数:
        file_path (str)  本地文件路径

    返回:
        str | None  成功返回 tmp_url，失败返回 None

    使用示例:
        url = upload_and_get_url("path/to/image.jpg")
        if url:
            print(f"上传成功: {url}")
        else:
            print("上传失败")
    """
    result = upload_file(file_path, api_key)
    if result["success"]:
        return result["tmp_url"]
    return None
```

---

## 三、AI 调用流程

```
┌─────────────────────────────────────────────────────────────┐
│ 步骤 1：检查 Token                                           │
│   调用 get_api_key()                                         │
│   → None：执行 AUTH.md 授权流程后返回步骤 1                  │
│   → 有效：进入步骤 2                                         │
├─────────────────────────────────────────────────────────────┤
│ 步骤 2：确认文件路径                                         │
│   • 检查用户提供的文件路径是否存在                           │
│   • 支持相对路径和绝对路径                                   │
│   • 确认文件为图片格式（jpg、png、webp、gif 等）             │
├─────────────────────────────────────────────────────────────┤
│ 步骤 3：调用 upload_file()                                   │
│   传入本地文件路径                                           │
├─────────────────────────────────────────────────────────────┤
│ 步骤 4：处理结果                                             │
│   → success=True：返回 tmp_url 给用户                        │
│   → success=False：按错误类型处理（见第四章）                │
└─────────────────────────────────────────────────────────────┘
```

### 标准输出格式

上传成功时，按以下格式回复用户：

```
✅ 图片上传成功！

🔗 临时访问地址：
   {tmp_url}

📄 文件名：{name}
🖼️ 类型：{type}
📦 大小：{size / 1024:.1f} KB
```

---

## 四、错误处理指南

### 4.1 错误代码处理表

| 错误码 | 场景 | AI 行为 | 用户提示 |
|--------|------|---------|----------|
| 401 | Token 无效或缺少 | 清除 Token，调用 AUTH.md | "API Key 无效或未提供，请重新授权" |
| 404 | 本地文件不存在 | 不重试，提示用户检查路径 | "文件不存在，请检查路径是否正确" |
| 408/超时 | 上传超时 | 提示检查文件大小 | "上传超时，请压缩图片后重试" |
| 0 | 网络错误 | 提示检查服务状态 | "无法连接到服务器，请检查本地服务是否启动" |
| 500 | 服务端错误 | 提示稍后重试 | "服务器异常，请稍后重试" |

### 4.2 文件大小建议

| 图片尺寸 | 预计耗时 | 建议 |
|----------|----------|------|
| < 1 MB | 1-3 秒 | 流畅上传 |
| 1-5 MB | 3-10 秒 | 正常范围 |
| 5-10 MB | 10-20 秒 | 建议压缩后上传 |
| > 10 MB | > 20 秒 | 强烈建议先压缩 |

---

## 五、使用示例

### 示例 1：基本上传

```python
# 用户说："帮我上传这张图片"
result = upload_file("D:/photos/example.jpg")

if result["success"]:
    print(f"上传成功！URL: {result['tmp_url']}")
else:
    print(f"上传失败: {result['error']}")
```

### 示例 2：上传后获取 URL 供后续使用

```python
# 上传图片后，将 URL 传递给其他技能使用
upload_result = upload_file("photo.jpg")
if upload_result["success"]:
    image_url = upload_result["tmp_url"]
    # 后续可以将 image_url 用于图像编辑、生成等操作
    print(f"图片 URL: {image_url}")
```

### 示例 3：快捷方式

```python
# 一句话上传并获取 URL
url = upload_and_get_url("avatar.png")
if url:
    # url 可以直接用于后续 API 调用
    pass
```

---

## 六、与其他技能的配合

本技能通常作为前置步骤使用：

1. **上传图片** → 获取 `tmp_url`
2. **将 `tmp_url` 传入其他技能**（如图像编辑、图像生成等）

```
用户提供本地图片路径
       │
       ▼
┌─────────────────┐
│  本 Skill：上传   │  ← 返回 tmp_url
└────────┬────────┘
         ▼
┌─────────────────────┐
│  其他 Skill：编辑/生成 │  ← 使用 tmp_url 作为输入
└─────────────────────┘
```
