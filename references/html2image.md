# HTML 转图片

将本地 `.html` 文件上传到 Aimaxhug HTML 转图片接口，返回可直接展示的 PNG 图片链接。

## 用法

```bash
python {baseDir}/scripts/html2image.py <file.html>
python {baseDir}/scripts/html2image.py <file.html> --json
```

接口为 `POST https://apis.aimaxhug.cloud/api/convert/file`，使用 multipart 字段 `file`，仅接受 `.html` 文件。脚本自动携带 `AIMAXHUG_API_KEY`，成功后输出 `data.url` 和 Markdown 图片。

## 使用规则

- 用户直接提供或上传 `.html` 文件时，直接调用脚本转换，不需要额外确认。
- 用户要求生成网页时，网页文件生成完成后，询问是否需要转成图片；用户确认后调用脚本。
- 转换成功后直接展示返回的图片链接。
