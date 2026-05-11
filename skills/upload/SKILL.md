---
name: image-upload
description: >
  文件上传技能。在生图/生视频前，需要将用户本地文件上传到服务器获取临时URL时调用。
  调用前需确保 .env 中已有 API Key。
---

# 文件上传技能

## API

```
POST https://base-api.aimaxhug.com/api/v2/upload/file
Authorization: Bearer sk-xxxxx
Content-Type: multipart/form-data

file: <文件二进制>
```

## 响应

```json
{
    "status": 200,
    "data": {
        "tmp_url": "https://static.aimaxhug.com/xxx.jpg",
        "name": "xxx.jpg",
        "type": "image/jpeg",
        "size": 123456
    }
}
```

## 执行

用 curl 上传，一步到位：

```bash
# 从 .env 读取 Key，上传文件，取出完整 data 对象（全部字段都需要）
key=$(grep AIMAXHUG_API_KEY .env | cut -d= -f2)
resp=$(curl -s -X POST https://base-api.aimaxhug.com/api/v2/upload/file \
  -H "Authorization: Bearer $key" \
  -F "file=@/path/to/image.jpg")
echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d['data']))"
```

多个文件就循环执行，结果组成数组。

## 输出展示

上传成功后输出：

```
📤 上传成功！
   📍 [点击预览图片](https://static.aimaxhug.com/xxx.jpg)
   📄 文件名: xxx.jpg
   🖼️ 类型: image/jpeg
   📦 大小: 123.4 KB
```

如果环境支持 markdown 图片渲染，直接展示：

```markdown
📤 上传成功！
![上传图片](https://static.aimaxhug.com/xxx.jpg)
- 文件名: xxx.jpg
- 类型: image/jpeg
- 大小: 123.4 KB
```

## 重要：传递给生图接口

上传返回的 **data 对象完整的 4 个字段**都必须传给生图接口的 `original_image` 参数，缺一不可：

```json
// ✅ 正确：完整 data 对象
"original_image": [
    {
        "tmp_url": "https://static.aimaxhug.com/xxx.jpg",
        "name": "xxx.jpg",
        "type": "image/jpeg",
        "size": 123456
    }
]

// ❌ 错误：只传 tmp_url 不行，后端需要知道文件格式、大小等信息
"original_image": [
    {"tmp_url": "https://static.aimaxhug.com/xxx.jpg"}
]
```
