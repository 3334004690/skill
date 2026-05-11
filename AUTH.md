---
name: api-auth
description: >
  API Key 配置说明。调用所有接口都需要 Bearer Token，
  从 .env 文件中读取 AIMAXHUG_API_KEY，无需单独验证，API 会自动校验。
---

# API 授权配置

## 配置方式

在项目根目录创建 `.env` 文件：

```
AIMAXHUG_API_KEY=sk-xxxxx
```

## 说明

- Token 在每次请求时通过 `Authorization: Bearer sk-xxx` 头携带
- Token 无效时 API 会返回 `401` 错误提示，无需前置验证
- 上传和生图脚本都会自动从 `.env` 读取 Token
