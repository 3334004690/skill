# 小红书平台解析

脚本：`scripts/xhs.py`。接口前缀为：

`https://api.aimaxhug.cloud/social`

运行前配置 `AIMAXHUG_API_KEY` 环境变量，或在项目根目录 `.env` 中配置。脚本自动发送：

```text
Authorization: Bearer <AIMAXHUG_API_KEY>
Content-Type: application/json
```

所有命令支持 `--json`，只输出接口原始 JSON。

## 命令与接口

| 命令 | 用途 | 方法与路径 |
| --- | --- | --- |
| `xhs-hot-accounts` | 小红书热门账号推荐 | POST `/story/api/xhsData/query` |
| `xhs-account-detail` | 获取账号信息（优质库） | POST `/story/api/xhsUser/queryAccountDetail` |
| `xhs-work-detail` | 获取作品详情（优质库） | POST `/story/api/xhsUser/queryWorkDetail` |
| `search-xhs-users` | 搜索关键词获取账号 | POST `/story/api/xhsUser/searchUser` |
| `search-xhs-articles` | 搜索关键词获取作品 | POST `/story/api/xhsUser/searchArticle` |
| `search-xhs-ai-works` | 搜索小红书 AI 相关作品 | POST `/story/api/parseWork/queryXhsAiMsgs` |
| `xhs-comments` | 获取一级评论（广域库） | POST `/story/api/xhs/commentSubmit` |
| `xhs-viral-insight` | 小红书爆款笔记洞察 | POST `/story/api/xhs/search/search` |
| `xhs-seven-day-hot` | 七日爆款笔记 | GET `/story/api/cozeSkill/getXhsCozeSkillDataSeven` |
| `xhs-work-list` | 查询账号作品列表 | POST `/story/api/xhsUser/queryWorkList` |
| `xhs-low-powder-explosive` | 黑马爆文榜 | GET `/story/api/cozeSkill/getLowPowderExplosiveArticle` |
| `xhs-daily-hot` | 每日爆款笔记榜单 | GET `/story/api/cozeSkill/getXhsCozeSkillDataOne` |
| `extract-xhs-audio-text` | 视频文案提取 | POST `/story/api/parseWork/audioTextExtract/submit/xhs` |

## 账号与作品

### 热门账号推荐

```bash
python scripts/xhs.py xhs-hot-accounts \
  --date-type 1 --rank-date 2026-08-16 --category "综合全部"
```

`dateType` 可选 `1`（日）、`2`（周）、`3`（月）；`rankDate` 和 `category` 可选。

### 账号信息

```bash
python scripts/xhs.py xhs-account-detail \
  --account-id rosy1109 --user-id 5a73c5fa4eacab4c4ccc9778
```

`accountId` 必填，`userId` 可选。

### 作品详情

```bash
python scripts/xhs.py xhs-work-detail --work-id 6a03be1b0000000035033163
python scripts/xhs.py xhs-work-detail --work-link "https://www.xiaohongshu.com/explore/6a2ac3020000000035022d8e"
```

`workId`、`workLink` 必须二选一。

### 搜索账号

```bash
python scripts/xhs.py search-xhs-users \
  --keyword "赵露思" --offset 0 --sort-type _0
```

`keyword` 必填；`offset` 默认 `0`；`sortType` 可选 `_0`（相关性）、`_2`（最近发文）、`_4`（红狐指数）。

### 搜索作品

```bash
python scripts/xhs.py search-xhs-articles \
  --keyword "美食" --offset 0 --sort-type _0 --exact-match false
```

`keyword` 必填；`exactMatch` 默认 `false`；`sortType` 可选 `_0`（相关性）、`_2`（发布时间）、`_4`（互动数）。

### 查询账号作品列表

```bash
python scripts/xhs.py xhs-work-list \
  --red-id rosy1109 --offset 0 --sort-type _0 \
  --publish-time-start "2026-07-01 00:00:00" \
  --publish-time-end "2026-08-01 00:00:00"
```

`redId`、`userid` 至少提供一个；`offset` 默认 `0`；时间参数可使用 `yyyy-MM-dd` 或 `yyyy-MM-dd HH:mm:ss`。

## AI、评论与爆款分析

### 搜索 AI 相关作品

```bash
python scripts/xhs.py search-xhs-ai-works \
  --keyword AI --page-num 1 --page-size 20 \
  --start-time "2026-06-01 00:00:00" \
  --end-time "2026-06-02 00:00:00"
```

`keyword`、`startTime`、`endTime` 必填；`pageNum` 默认 `1`；`pageSize` 默认 `20`，最大 `50`。

### 获取一级评论

```bash
python scripts/xhs.py xhs-comments \
  --opus-id 6a546c340000000007022631 --data-num 20
```

`opusId`、`dataNum` 必填；`dataNum=-1` 表示获取全部评论。

### 爆款笔记洞察

```bash
python scripts/xhs.py xhs-viral-insight \
  --keyword "AIGC创业" --page-num 1 --page-size 10 \
  --start-date 2026-07-01 --end-date 2026-07-31
```

`keyword`、日期范围可选；无关键词时按互动数降序返回热门数据；`pageNum` 默认 `1`，`pageSize` 默认 `10`，最大 `50`。

### 七日爆款笔记

```bash
python scripts/xhs.py xhs-seven-day-hot \
  --rank-date 2026-08-10 --category "综合全部"
```

`rankDate`、`category` 均可选。

## 榜单与视频文案

### 黑马爆文榜

```bash
python scripts/xhs.py xhs-low-powder-explosive \
  --category "潮流鞋包" --rank-date 2026-09-08
```

`category`、`rankDate` 必填，日期格式为 `yyyy-MM-dd`。

### 每日爆款笔记榜单

```bash
python scripts/xhs.py xhs-daily-hot \
  --rank-date 2026-08-25 --category "综合全部"
```

`rankDate`、`category` 必填，日期格式为 `yyyy-MM-dd`。

### 视频文案提取

```bash
python scripts/xhs.py extract-xhs-audio-text \
  --url "https://www.xiaohongshu.com/explore/6a3c7aa6000000001003e071"
```

`url` 必填。响应中的 `taskId`、`status`、`text`、`stampSents`、`failReason` 等字段会原样输出。
