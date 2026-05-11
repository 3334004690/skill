---
name: image-generation
description: >
  图像生成技能。支持 Nano Banana / Nano Banana Pro / gpt-image-2。
  按步骤执行：检查Token → 列出模型及参数 → 填入脚本生成 → 展示URL。
---

# 图像生成技能

## 第一步：检查 Token

不管上传文件还是生成图片都需要 Token，统一按以下流程处理：

```
检查 .env 文件是否存在且包含 AIMAXHUG_API_KEY
  ├── 不存在 → 询问用户输入 API Key
  │            保存到 .env：echo AIMAXHUG_API_KEY=sk-xxx > .env
  │            告知用户已保存，后续无需重复输入
  └── 存在   → 继续执行
```

> 注意：不要在输出中回显完整 Token，只展示前 8 位：`sk-abc123...****`

---

## 第二步：列出可用模型及参数

当用户表达"生图"意图时，先展示所有模型及详细参数约束，让用户选择：

```
📷 可用生图模型：

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1️⃣ Nano Banana（标准生图，速度快）
   API值:    gemini-3-pro-image-preview
   分辨率:   支持手动选择 1k / 2k / 4k ✅
   比例:     1:1, 9:16, 16:9, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 21:9

2️⃣ Nano Banana Pro（高质量生图）
   API值:    gemini-3.1-flash-image-preview
   分辨率:   支持手动选择 1k / 2k / 4k ✅
   比例:     1:1, 9:16, 16:9, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 21:9

3️⃣ gpt-image-2（照片级写实/艺术风格）
   API值:    gpt-image-2
   分辨率:   ❌ 不支持手动选择，按比例自动映射：
              • 9:16 / 16:9 → 4k
              • 1:1        → 2k
              • 其他       → 1k
   比例:     1:1, 9:16, 16:9, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 21:9

请选择模型并告诉我：提示词、比例、分辨率（如适用）
```

---

## 第三步：定义参数并执行

根据用户的选择，把参数填入以下固定脚本。**不要修改脚本逻辑，只填参数。**

参数填写规则：

| 模型 | model_key | proportion | resolution |
|------|-----------|------------|------------|
| Nano Banana | `nano-banana` | 用户选择 | 用户选择 1k/2k/4k |
| Nano Banana Pro | `nano-banana-pro` | 用户选择 | 用户选择 1k/2k/4k |
| gpt-image-2 | `gpt-image-2` | 用户选择 | **不填**（自动映射） |

如用户上传了本地图片，先用上传接口获取 URL，再填入 `input_images`。

### 上传脚本（如需要）

```bash
# 上传单张图片，返回 tmp_url
upload_resp=$(curl -s -X POST https://base-api.aimaxhug.com/api/v2/upload/file \
  -H "Authorization: Bearer $(grep AIMAXHUG_API_KEY .env | cut -d= -f2)" \
  -F "file=@/path/to/image.jpg")
echo "$upload_resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data']['tmp_url'])"
```

### 生图脚本

```python
import json, os, sys, time, requests

# ===== 用户参数（AI 填入） =====
MODEL_KEY = "nano-banana"           # nano-banana / nano-banana-pro / gpt-image-2
PROMPT = "一只橘猫坐在窗边"         # 提示词
PROPORTION = "16:9"                  # 比例
RESOLUTION = "2k"                    # 仅 nano-banana/pro 有效，gpt-image-2 填 None
INPUT_IMAGES = None                  # 上传的图片 [{tmp_url}...] 或 None
# ================================

API_KEY = os.getenv("AIMAXHUG_API_KEY") or open(".env").read().split("=", 1)[1].strip()

# 模型配置
MODELS = {
    "nano-banana":    {"api": "gemini-3-pro-image-preview",       "mode": "manual", "res": ["1k","2k","4k"]},
    "nano-banana-pro":{"api": "gemini-3.1-flash-image-preview",   "mode": "manual", "res": ["1k","2k","4k"]},
    "gpt-image-2":    {"api": "gpt-image-2",                     "mode": "auto",   "res": []},
}
RES_MAP = {"9:16":"4k","16:9":"4k","1:1":"2k"}

cfg = MODELS[MODEL_KEY]
body = {"model": cfg["api"], "prompt": PROMPT}
if PROPORTION: body["proportion"] = PROPORTION
if cfg["mode"] == "manual":
    body["resolution"] = RESOLUTION or cfg["res"][0]
elif cfg["mode"] == "auto":
    r = RES_MAP.get(PROPORTION, "1k")
    body["resolution"] = r
if INPUT_IMAGES: body["original_image"] = INPUT_IMAGES

# 假进度条
print(f"🚀 正在使用 {MODEL_KEY} 生成中...")
for i in range(1, 11):
    bar = "█" * i + "░" * (10 - i)
    print(f"\r   [{bar}] {i*10}%", end="", flush=True)
    time.sleep(0.3 + (i * 0.1))
print()

# 真实请求
resp = requests.post(
    "https://base-api.aimaxhug.com/api/v1/imageToImage",
    headers={"Content-Type":"application/json", "Authorization":f"Bearer {API_KEY}"},
    json=body, timeout=120,
)
data = resp.json()
url = data.get("data", {}).get("imageUrl", "")

if url:
    print(f"\n✅ 生成成功！")
    print(f"   📍 图片地址: {url}")
    print(f"   📐 比例: {PROPORTION or '默认'}  分辨率: {body.get('resolution','N/A')}")
else:
    print(f"\n❌ 失败: {data.get('message', '未知错误')}")
```

---

## 第四步：展示结果

生成完成后，按以下格式输出：

```
✅ 生成成功！

📍 图片地址: https://static.aimaxhug.com/xxx.jpg
📐 比例: 16:9  分辨率: 4k

🖼️ 如果环境支持，直接展示图片
```

> 注意：**不要下载图片**，直接展示 URL 路径即可。用户需要下载会自己处理。

如果用户上传了多张参考图，上传后也展示：

```
📤 已上传 2 张参考图：
  [1] https://static.aimaxhug.com/xxx.jpg  (原图1)
  [2] https://static.aimaxhug.com/xxx.jpg  (原图2)
```

---

## 完整流程示例

```
用户: "生一张猫的图片，16:9"

AI:
  → 检查 .env → 存在
  → 列出模型让用户选择
  → 用户: "用 Nano Banana，4k"
  → AI 填入脚本参数:
      MODEL_KEY = "nano-banana"
      PROMPT = "一只可爱的猫"
      PROPORTION = "16:9"
      RESOLUTION = "4k"
      INPUT_IMAGES = None
  → 执行脚本
  → 假进度条
  → 展示URL
```

```
用户: "把这张图换成赛博朋克风格"（上传了 photo.jpg）

AI:
  → 先上传图片获取 tmp_url
  → 列出模型
  → 用户: "Nano Banana Pro，2k"
  → AI 填入:
      INPUT_IMAGES = [{"tmp_url": "https://..."}]
      ...
  → 执行 → 展示URL
```
