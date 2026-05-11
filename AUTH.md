# API 授权配置

在项目根目录创建 `.env` 文件：

```
AIMAXHUG_API_KEY=sk-xxxxx
```

每次请求时通过 `Authorization: Bearer sk-xxx` 头携带。
脚本会自动从 `.env` 读取，无需手动配置。
