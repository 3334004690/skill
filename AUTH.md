---
name: gemini-image-auth
description: >
  API Token 授权管理模块。当用户首次使用图像生成/编辑功能，或提示"未授权"、"401错误"、"请输入token"、"配置API Key"时触发。
  负责安全地收集、存储和复用用户的 API Token，使后续所有图像操作无需重复输入凭证。
---

# Gemini 图像服务 — 授权管理指南

## 概述

本模块管理调用 Gemini 图像生成 API 所需的 Bearer Token（API Key）。
Token 一旦保存，将在本次对话的所有后续请求中自动携带，无需重复输入。

---

## 第一步：引导用户提供 Token

**触发条件：** 以下任一情况出现时，必须执行本模块：
- 用户首次发起图像生成 / 编辑请求
- 当前上下文中 `GEMINI_API_KEY` 未定义或为空
- API 返回 `401 UNAUTHENTICATED` 或 `403 PERMISSION_DENIED`

**提示语模板（向用户展示）：**

```
🔑 需要您的 API Token 才能继续

请提供您的 Gemini 图像服务 API Key：
  • 格式示例：sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  • 如何获取：登录 https://aimaxhug.com 后在"API 管理"页面创建
  • 安全提示：Token 仅在本次对话中使用，不会被记录或外传

请直接回复您的 Token：
```

---

## 第二步：Token 接收与验证

用户回复 Token 后，执行以下操作：

### 2.1 格式预检

```python
import re

def validate_token_format(token: str) -> bool:
    """
    基础格式校验：
    - 不为空
    - 长度 >= 20 字符
    - 无明显占位符（如 'your_key', 'xxx', 'sk-'）
    """
    token = token.strip()
    if not token or len(token) < 20:
        return False
    placeholders = ["your_key", "your-key", "sk-xxxxx", "xxxxxxx", "<api", "填写"]
    if any(p in token.lower() for p in placeholders):
        return False
    return True
```

### 2.2 存储位置（按优先级）

AI 应将 Token 存入以下位置，后续请求直接读取，**无需再次询问用户**：

| 优先级 | 存储位置 | 说明 |
|--------|----------|------|
| 1 | 对话内存变量 `GEMINI_API_KEY` | 本次对话全程有效，推荐首选 |
| 2 | 当前工作目录 `.env` 文件 | 跨对话持久化，需文件系统权限 |
| 3 | 环境变量 `GEMINI_API_KEY` | 系统级，需 shell 权限 |

**内存存储示例（伪代码）：**

```python
# AI 在对话 context 中维护此变量
SESSION_CONFIG = {
    "GEMINI_API_KEY": None,      # 用户提供后填充
    "BASE_URL": "https://aimaxhug.com",
    "MODEL": "gemini-3.1-flash-image-preview",
    "token_verified": False
}

def set_token(token: str):
    SESSION_CONFIG["GEMINI_API_KEY"] = token.strip()
    SESSION_CONFIG["token_verified"] = False  # 待验证
```

**文件持久化示例：**

```python
import os

def persist_token_to_env(token: str, env_path: str = ".env"):
    """将 Token 写入 .env 文件（追加或更新）"""
    lines = []
    updated = False
    
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()
    
    new_lines = []
    for line in lines:
        if line.startswith("GEMINI_API_KEY="):
            new_lines.append(f"GEMINI_API_KEY={token}\n")
            updated = True
        else:
            new_lines.append(line)
    
    if not updated:
        new_lines.append(f"GEMINI_API_KEY={token}\n")
    
    with open(env_path, "w") as f:
        f.writelines(new_lines)
```

---

## 第三步：Token 有效性验证（可选但推荐）

存储前发送轻量探测请求验证 Token 真实有效：

```python
import requests

def verify_token(api_key: str, base_url: str = "https://aimaxhug.com") -> dict:
    """
    发送最小化测试请求验证 Token 有效性
    返回: {"valid": bool, "error": str or None}
    """
    test_url = f"{base_url}/v1/models/gemini-3.1-flash-image-preview:generateContent"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    # 极小的测试负载，不消耗图像配额
    payload = {
        "contents": [{"parts": [{"text": "test"}]}],
        "generationConfig": {"responseModalities": ["TEXT"]}
    }
    try:
        resp = requests.post(test_url, headers=headers, json=payload, timeout=10)
        if resp.status_code == 401:
            return {"valid": False, "error": "Token 无效，请检查后重试"}
        if resp.status_code == 403:
            return {"valid": False, "error": "无权限访问该模型，请确认账户套餐"}
        return {"valid": True, "error": None}
    except requests.Timeout:
        return {"valid": False, "error": "验证超时，请检查网络连接"}
    except Exception as e:
        return {"valid": False, "error": f"验证失败：{str(e)}"}
```

---

## 第四步：Token 读取（供其他 Skill 调用）

每次发起 API 请求前，统一通过以下函数获取 Token：

```python
import os

def get_api_key() -> str | None:
    """
    Token 读取优先级：
    1. 对话内存 SESSION_CONFIG
    2. 环境变量
    3. .env 文件
    返回 None 表示未配置，需重新触发授权流程
    """
    # 1. 对话内存
    if SESSION_CONFIG.get("GEMINI_API_KEY"):
        return SESSION_CONFIG["GEMINI_API_KEY"]
    
    # 2. 环境变量
    env_key = os.getenv("GEMINI_API_KEY")
    if env_key:
        SESSION_CONFIG["GEMINI_API_KEY"] = env_key
        return env_key
    
    # 3. .env 文件
    if os.path.exists(".env"):
        with open(".env") as f:
            for line in f:
                if line.startswith("GEMINI_API_KEY="):
                    key = line.split("=", 1)[1].strip()
                    if key:
                        SESSION_CONFIG["GEMINI_API_KEY"] = key
                        return key
    
    return None  # 未找到，触发授权流程
```

---

## 第五步：错误处理与重授权

| 错误场景 | AI 行为 |
|----------|---------|
| 用户输入了占位符文本 | 提示格式不正确，重新引导输入 |
| 验证返回 401 | 告知 Token 无效，清除存储，重新引导 |
| 验证返回 403 | 告知账户权限不足，建议检查套餐 |
| 验证超时 | 跳过验证，保存 Token，后续请求再判断 |
| 请求中途 401 | 清除 `SESSION_CONFIG["GEMINI_API_KEY"]`，重新触发本授权流程 |

**清除 Token：**

```python
def clear_token():
    SESSION_CONFIG["GEMINI_API_KEY"] = None
    SESSION_CONFIG["token_verified"] = False
    # 可选：同步清除 .env
```

---

## AI 行为规范

> ⚠️ **重要：** AI 在整个流程中必须遵守以下规则

1. **绝不在回复中回显完整 Token**，最多展示前 8 位加掩码：`sk-abc123...****`
2. **Token 存入内存后立即告知用户**："✅ Token 已保存，本次对话无需重复输入"
3. **切勿主动询问用户是否要保存 Token**，直接保存，用户如需清除可说"清除Token"
4. **每次图像请求前静默调用 `get_api_key()`**，返回 None 时才触发本授权流程
5. **不要将 Token 写入任何展示给用户的代码块或日志中**