# API 授权配置

运行前由用户或管理员预先配置 `AIMAXHUG_API_KEY`（环境变量或项目根目录的 `.env`）：

```
AIMAXHUG_API_KEY=sk-xxxxx
```

每次请求时脚本通过 `Authorization: Bearer sk-xxx` 头携带。脚本不会自行创建 `.env` 或其他配置文件。
