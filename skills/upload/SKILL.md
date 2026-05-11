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
# 从 .env 读取 Key，上传文件，直接取出 tmp_url
key=$(grep AIMAXHUG_API_KEY .env | cut -d= -f2)
resp=$(curl -s -X POST https://base-api.aimaxhug.com/api/v2/upload/file \
  -H "Authorization: Bearer $key" \
  -F "file=@/path/to/image.jpg")
tmp_url=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['tmp_url'])")
echo "tmp_url=$tmp_url"
```

多个文件就循环执行，结果拼成数组。

## 输出展示

上传成功后输出：

```
📤 上传成功！
   📍 URL: https://static.aimaxhug.com/xxx.jpg
   📄 文件名: xxx.jpg
```

上传的 `tmp_url` 直接传给生图/生视频接口的 `original_image` 参数（数组包裹）。
