# 社交媒体平台解析：抖音

脚本：`scripts/social_media.py`。所有接口都使用 `POST`、`application/json`，请求前缀为：

`https://api.aimaxhug.cloud/social`

运行前配置 `AIMAXHUG_API_KEY` 环境变量，或在项目根目录 `.env` 中配置。脚本会自动发送：

```text
Authorization: Bearer <AIMAXHUG_API_KEY>
Content-Type: application/json
```

所有命令都支持 `--json`，只输出接口原始 JSON。

## 命令总览

| 命令 | 数据库/用途 | 接口 |
| --- | --- | --- |
| `search-douyin-users` | 搜索抖音账号（优质库） | `/story/api/dyData/searchUser` |
| `search-douyin-accounts` | 搜索抖音账号（广域库） | `/story/api/dy/data/searchAccount` |
| `query-douyin-work-list` | 账号作品列表（优质库） | `/story/api/dyData/queryWorkList` |
| `list-douyin-works-by-account` | 账号作品列表（广域库） | `/story/api/dy/data/listWorkByAccount` |
| `search-douyin-articles` | 搜索作品（优质库） | `/story/api/dyData/searchArticle` |
| `search-douyin-works` | 搜索作品（广域库） | `/story/api/dy/data/searchWork` |
| `query-douyin-work` | 作品详情（优质库） | `/story/api/dyData/queryWork` |
| `get-douyin-work-detail` | 作品详情（广域库） | `/story/api/dy/data/workDetail` |
| `recommend-douyin-accounts` | 热门账号推荐 | `/story/api/dyData/query` |
| `douyin-likes-rank` | 每日热门作品榜 | `/story/api/dy/search/likesRank` |
| `query-douyin-user` | 账号信息（优质库） | `/story/api/dyData/queryUser` |
| `search-douyin-ai-works` | AI 垂类作品搜索 | `/story/api/parseWork/queryDyAiMsgs` |
| `douyin-daily-rank` | 每日点赞飙升榜 | `/story/api/dy/search/getDailyRank` |
| `douyin-weekly-rank` | 七日点赞飙升榜 | `/story/api/dy/search/getWeeklyRank` |
| `extract-douyin-audio-text` | 视频文案/字幕提取 | `/story/api/parseWork/audioTextExtract/submit/douyin` |

## 账号与作品搜索

### 搜索账号（优质库）

```bash
python scripts/social_media.py search-douyin-users --keyword "摄影"
python scripts/social_media.py search-douyin-users "摄影" --offset 20 --sort-type _2
```

参数：`keyword` 必填；`offset` 默认 `0`；`sortType` 默认 `_0`，可选 `_0`（相关性）、`_2`（最新）、`_4`（最热）。

### 搜索账号（广域库）

```bash
python scripts/social_media.py search-douyin-accounts \
  --keyword "罗志祥" --page-num 1 --page-size 10
```

参数：`keyword` 必填；`pageNum` 从 `1` 开始，默认 `1`；`pageSize` 默认 `10`，最大 `50`。

### 账号作品列表（优质库）

```bash
python scripts/social_media.py query-douyin-work-list \
  --account-id nxpt260212 --offset 0 --sort-type _0
```

`accountId`、`authorUrl`、`secUserId` 至少提供一个；`offset` 默认 `0`；`sortType` 默认 `_0`，可选 `_0`、`_2`、`_4`。

### 账号作品列表（广域库）

```bash
python scripts/social_media.py list-douyin-works-by-account \
  --user-id 3822358551859599 --page-num 1 --page-size 10 \
  --start-date 2026-07-01 --end-date 2026-07-20
```

`userId`、`uniqueName`、`shortId` 必须三选一；`pageNum` 默认 `1`；`pageSize` 默认 `10`，最大 `50`；日期格式为 `yyyy-MM-dd`。

### 搜索作品（优质库）

```bash
python scripts/social_media.py search-douyin-articles \
  --keyword "示例关键词" --start-date 2026-07-01 --end-date 2026-07-20 \
  --offset 0 --sort-type _0
```

`keyword` 必填；日期可选；`offset` 默认 `0`；`sortType` 默认 `_0`，可选 `_0`、`_2`、`_4`。

### 搜索作品（广域库）

```bash
python scripts/social_media.py search-douyin-works \
  --keyword "美食" --exact-match false --page-num 1 --page-size 10
```

`keyword` 必填；`exactMatch` 默认 `false`，设为 `true` 时按完整短语匹配；日期可选；`pageNum` 默认 `1`；`pageSize` 默认 `10`，最大 `50`。

## 作品与账号详情

### 作品详情（优质库）

```bash
python scripts/social_media.py query-douyin-work --work-id 10000123456789
python scripts/social_media.py query-douyin-work --work-url "https://www.douyin.com/video/xxx"
```

`workId`、`workUrl` 必须二选一。

### 作品详情（广域库）

```bash
python scripts/social_media.py get-douyin-work-detail \
  --video-id 7663047997038644499
```

`videoId` 必填，对应抖音 `aweme_id`。

### 账号信息（优质库）

```bash
python scripts/social_media.py query-douyin-user --account-id dy_user123
```

`accountId` 必填，支持 `unique_id`、`short_id`、`uid` 任一形式。

## 榜单与推荐

### 热门账号推荐

```bash
python scripts/social_media.py recommend-douyin-accounts \
  --date-type days --rank-date 2026-08-16 --type "个人才艺"
```

`dateType` 必填，可选 `days`、`weeks`、`months`；`rankDate` 必填，格式 `yyyy-MM-dd`；`type` 必填，支持接口文档中的账号类别。

### 每日热门作品榜

```bash
python scripts/social_media.py douyin-likes-rank \
  --type "二次元" --start-time 2026-08-11 --end-time 2026-08-12
```

`type`、日期均可省略；省略 `type` 查询全部分类，日期格式为 `yyyy-MM-dd`。

### 每日/七日点赞飙升榜

```bash
python scripts/social_media.py douyin-daily-rank --type "全部" --start-time 2026-08-16
python scripts/social_media.py douyin-weekly-rank --type "游戏" --start-time 2026-08-17
```

`type` 和 `startTime` 均可选；不传分类或传 `全部` 时查询全部分类，日期格式为 `yyyy-MM-dd`。

## AI 作品与文案提取

### 搜索抖音 AI 相关作品

```bash
python scripts/social_media.py search-douyin-ai-works \
  --keyword AI --page-num 1 --page-size 20 \
  --start-time "2026-06-01 00:00:00" \
  --end-time "2026-06-02 00:00:00"
```

`keyword` 必填；`pageNum` 默认 `1`；`pageSize` 默认 `20`；时间可选，格式为 `yyyy-MM-dd HH:mm:ss`。

### 提取抖音视频文案/字幕

```bash
python scripts/social_media.py extract-douyin-audio-text \
  --url "https://v.douyin.com/pjE9uqFMK68/"
```

`url` 必填。接口可能返回异步任务，响应中的 `taskId`、`status`、`text`、`stampSents`、`failReason` 等字段会原样输出。
