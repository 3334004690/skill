# 百度 AI 搜索模块

通过 `scripts/ai_search.py` 调用联网搜索接口，返回网页引用结果。模型应根据 `references` 中的标题、摘要和正文回答用户，并附上相关来源 URL。

## Endpoint and Authentication

- Endpoint: `https://apis.aimaxhug.cloud/v1/ai_search`
- Authentication: `Authorization: Bearer <AIMAXHUG_API_KEY>`
- `Content-Type: application/json`（POST 时）

## Usage

```bash
# POST JSON（默认）
python {baseDir}/scripts/ai_search.py run --query "2026 年人工智能行业趋势"

# GET query string
python {baseDir}/scripts/ai_search.py run --query "北京今天的天气" --method get

# 也可以把关键词作为位置参数传入
python {baseDir}/scripts/ai_search.py run "最新科技新闻" --json
```

## Request

| CLI option | API field | Description |
|------------|-----------|-------------|
| `--query` / positional `q` | `q` | Required search keyword |
| `--method post` | JSON body | `{ "q": "搜索关键词" }` |
| `--method get` | Query string | `?q=搜索关键词` |

## Response

```json
{
  "request_id": "8dbac25d-bc69-4c69-8b67-d2489ef85225",
  "references": [
    {
      "id": 1,
      "url": "https://example.com/article",
      "title": "搜索结果标题",
      "date": "2026-07-24 17:28:46",
      "content": "搜索结果正文内容...",
      "icon": "https://example.com/favicon.ico",
      "type": "web",
      "website": "来源网站名称",
      "snippet": "内容摘要...",
      "rerank_score": 1,
      "authority_score": 0.5
    }
  ]
}
```

默认输出会展示每条结果的标题、来源、URL、日期、摘要和相关性；使用 `--json` 可保留 API 返回的完整字段。

## 来源与失败处理

先按 [AUTH.md](../AUTH.md) 完成依赖与 Key 自检。缺依赖时修复后再调用；缺 Key 时明确报告 `AIMAXHUG_API_KEY` 未配置，不伪造搜索结果或引用。

核对接口能力时优先查实际可读的官方文档、公开模型配置和接口响应。搜索不可用时，如当前环境有其他已授权的读取工具，可直接读取已知官方来源；否则说明未能在线核实并引用本地规则。每个关键数字链接到实际查阅的来源，区分“文档描述”“当前 CLI 校验”和“实际请求已验证”，不能仅列官网首页来证明具体参数。
