#!/usr/bin/env python3
"""Douyin data tools backed by the Aimaxhug API."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared.client import AimaxhugClient, AimaxhugError

SOCIAL_API_PREFIX = "https://api.aimaxhug.cloud/social"
SORT_TYPES = ("_0", "_2", "_4")
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

ENDPOINTS = {
    "search-users": f"{SOCIAL_API_PREFIX}/story/api/dyData/searchUser",
    "search-accounts": f"{SOCIAL_API_PREFIX}/story/api/dy/data/searchAccount",
    "query-work-list": f"{SOCIAL_API_PREFIX}/story/api/dyData/queryWorkList",
    "list-works-by-account": f"{SOCIAL_API_PREFIX}/story/api/dy/data/listWorkByAccount",
    "search-articles": f"{SOCIAL_API_PREFIX}/story/api/dyData/searchArticle",
    "search-works": f"{SOCIAL_API_PREFIX}/story/api/dy/data/searchWork",
    "query-work": f"{SOCIAL_API_PREFIX}/story/api/dyData/queryWork",
    "work-detail": f"{SOCIAL_API_PREFIX}/story/api/dy/data/workDetail",
    "recommend-accounts": f"{SOCIAL_API_PREFIX}/story/api/dyData/query",
    "likes-rank": f"{SOCIAL_API_PREFIX}/story/api/dy/search/likesRank",
    "query-user": f"{SOCIAL_API_PREFIX}/story/api/dyData/queryUser",
    "search-ai-works": f"{SOCIAL_API_PREFIX}/story/api/parseWork/queryDyAiMsgs",
    "daily-rank": f"{SOCIAL_API_PREFIX}/story/api/dy/search/getDailyRank",
    "weekly-rank": f"{SOCIAL_API_PREFIX}/story/api/dy/search/getWeeklyRank",
    "extract-audio-text": f"{SOCIAL_API_PREFIX}/story/api/parseWork/audioTextExtract/submit/douyin",
}
DOUYIN_SEARCH_USERS_ENDPOINT = ENDPOINTS["search-users"]


def _compact(payload: dict) -> dict:
    return {key: value for key, value in payload.items() if value is not None}


def _text(value: str, name: str) -> str:
    value = (value or "").strip()
    if not value:
        raise ValueError(f"{name} 不能为空")
    return value


def _optional_text(value: Optional[str]) -> Optional[str]:
    value = (value or "").strip()
    return value or None


def _non_negative_int(value: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("必须是整数") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("不能小于 0")
    return number


def _positive_int(value: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("必须是整数") from exc
    if number < 1:
        raise argparse.ArgumentTypeError("必须大于等于 1")
    return number


def _page_size(value: str) -> int:
    number = _positive_int(value)
    if number > 50:
        raise argparse.ArgumentTypeError("每页大小不能超过 50")
    return number


def _date(value: str) -> str:
    try:
        datetime.strptime(value, DATE_FORMAT)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("日期格式必须是 yyyy-MM-dd") from exc
    return value


def _datetime_value(value: str) -> str:
    try:
        datetime.strptime(value, DATETIME_FORMAT)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("时间格式必须是 yyyy-MM-dd HH:mm:ss") from exc
    return value


def _boolean(value: str) -> bool:
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError("布尔值必须是 true 或 false")


def _http_url(value: str) -> str:
    value = _text(value, "url")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise argparse.ArgumentTypeError("必须提供 http:// 或 https:// URL")
    return value


def _validate_range(start: Optional[str], end: Optional[str], label: str) -> None:
    if start and end and start > end:
        raise ValueError(f"{label} 的开始时间不能晚于结束时间")


def build_search_payload(keyword: str, offset: int = 0, sort_type: str = "_0") -> dict:
    """Build and validate the original Douyin user-search request body."""
    keyword = _text(keyword, "keyword")
    if offset < 0:
        raise ValueError("offset 不能小于 0")
    if sort_type not in SORT_TYPES:
        raise ValueError(f"sortType 必须是 {', '.join(SORT_TYPES)} 之一")
    return {"keyword": keyword, "offset": offset, "sortType": sort_type}


def _build_search_account_payload(args: argparse.Namespace) -> dict:
    return {
        "keyword": _text(args.keyword, "keyword"),
        "pageNum": args.page_num,
        "pageSize": args.page_size,
    }


def _build_query_work_list_payload(args: argparse.Namespace) -> dict:
    identifiers = {
        "accountId": _optional_text(args.account_id),
        "authorUrl": _optional_text(args.author_url),
        "secUserId": _optional_text(args.sec_user_id),
    }
    if not any(identifiers.values()):
        raise ValueError("accountId、authorUrl、secUserId 至少提供一个")
    return _compact({**identifiers, "offset": args.offset, "sortType": args.sort_type})


def _build_list_works_payload(args: argparse.Namespace) -> dict:
    identifiers = {
        "userId": _optional_text(args.user_id),
        "uniqueName": _optional_text(args.unique_name),
        "shortId": _optional_text(args.short_id),
    }
    provided = [key for key, value in identifiers.items() if value]
    if len(provided) != 1:
        raise ValueError("userId、uniqueName、shortId 必须三选一")
    return _compact(
        {
            **identifiers,
            "pageNum": args.page_num,
            "pageSize": args.page_size,
            "startDate": args.start_date,
            "endDate": args.end_date,
        }
    )


def _build_search_article_payload(args: argparse.Namespace) -> dict:
    _validate_range(args.start_date, args.end_date, "日期")
    return _compact(
        {
            "keyword": _text(args.keyword, "keyword"),
            "startDate": args.start_date,
            "endDate": args.end_date,
            "offset": args.offset,
            "sortType": args.sort_type,
        }
    )


def _build_search_work_payload(args: argparse.Namespace) -> dict:
    _validate_range(args.start_date, args.end_date, "日期")
    return _compact(
        {
            "keyword": _text(args.keyword, "keyword"),
            "exactMatch": args.exact_match,
            "startDate": args.start_date,
            "endDate": args.end_date,
            "pageNum": args.page_num,
            "pageSize": args.page_size,
        }
    )


def _build_query_work_payload(args: argparse.Namespace) -> dict:
    work_id = _optional_text(args.work_id)
    work_url = _optional_text(args.work_url)
    provided = [value for value in (work_id, work_url) if value]
    if len(provided) != 1:
        raise ValueError("workId、workUrl 必须二选一")
    return _compact({"workId": work_id, "workUrl": work_url})


def _build_work_detail_payload(args: argparse.Namespace) -> dict:
    return {"videoId": _text(args.video_id, "videoId")}


def _build_recommend_accounts_payload(args: argparse.Namespace) -> dict:
    return {
        "dateType": _text(args.date_type, "dateType"),
        "rankDate": args.rank_date,
        "type": _text(args.category, "type"),
    }


def _build_likes_rank_payload(args: argparse.Namespace) -> dict:
    _validate_range(args.start_time, args.end_time, "时间")
    return _compact(
        {
            "type": _optional_text(args.category),
            "startTime": args.start_time,
            "endTime": args.end_time,
        }
    )


def _build_query_user_payload(args: argparse.Namespace) -> dict:
    return {"accountId": _text(args.account_id, "accountId")}


def _build_ai_works_payload(args: argparse.Namespace) -> dict:
    _validate_range(args.start_time, args.end_time, "时间")
    return _compact(
        {
            "keyword": _text(args.keyword, "keyword"),
            "pageNum": args.page_num,
            "pageSize": args.page_size,
            "startTime": args.start_time,
            "endTime": args.end_time,
        }
    )


def _build_rank_payload(args: argparse.Namespace) -> dict:
    return _compact({"type": _optional_text(args.category), "startTime": args.start_time})


def _build_audio_text_payload(args: argparse.Namespace) -> dict:
    return {"url": args.url}


def _request(args: argparse.Namespace, endpoint: str, label: str, payload: dict) -> None:
    client = AimaxhugClient()
    try:
        response = client.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=120,
        )
    except AimaxhugError as exc:
        print(f"Error: {label}失败: {exc}", file=sys.stderr)
        raise SystemExit(1)

    if not args.json:
        print(f"{label}完成")
    print(json.dumps(response, ensure_ascii=False, indent=2))


def _run(args: argparse.Namespace, endpoint_key: str, label: str, builder) -> None:
    try:
        payload = builder(args)
    except (TypeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
    _request(args, ENDPOINTS[endpoint_key], label, payload)


def _add_json(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="仅输出接口原始 JSON")


def _add_keyword(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--keyword", "-k", required=True, help="搜索关键词")


def _add_page(parser: argparse.ArgumentParser, page_size: int = 10) -> None:
    parser.add_argument("--page-num", "--pageNum", dest="page_num", type=_positive_int, default=1)
    parser.add_argument(
        "--page-size", "--pageSize", dest="page_size", type=_page_size, default=page_size
    )


def _add_dates(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--start-date", "--startDate", dest="start_date", type=_date)
    parser.add_argument("--end-date", "--endDate", dest="end_date", type=_date)


def _add_offset_sort(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--offset", type=_non_negative_int, default=0)
    parser.add_argument(
        "--sort-type", "--sortType", dest="sort_type", choices=SORT_TYPES, default="_0"
    )


def _add_category(
    parser: argparse.ArgumentParser, help_text: str = "分类", required: bool = False
) -> None:
    parser.add_argument("--type", dest="category", help=help_text, required=required)


def _add_search_users_parser(subparsers) -> None:
    parser = subparsers.add_parser("search-douyin-users", help="搜索关键词获取抖音账号（优质库）")
    parser.add_argument("keyword", nargs="?", help="搜索关键词")
    parser.add_argument("--keyword", "-k", dest="keyword_option", help="搜索关键词")
    parser.add_argument("--offset", type=_non_negative_int, default=0)
    parser.add_argument(
        "--sort-type", "--sortType", dest="sort_type", choices=SORT_TYPES, default="_0"
    )
    _add_json(parser)
    return parser


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="社交媒体平台解析工具")
    subparsers = parser.add_subparsers(dest="command")

    _add_search_users_parser(subparsers)

    command = subparsers.add_parser("search-douyin-accounts", help="搜索关键词获取抖音账号（广域库）")
    _add_keyword(command)
    _add_page(command)
    _add_json(command)

    command = subparsers.add_parser("query-douyin-work-list", help="获取抖音账号作品列表（优质库）")
    command.add_argument("--account-id", "--accountId", dest="account_id")
    command.add_argument("--author-url", "--authorUrl", dest="author_url")
    command.add_argument("--sec-user-id", "--secUserId", dest="sec_user_id")
    _add_offset_sort(command)
    _add_json(command)

    command = subparsers.add_parser("list-douyin-works-by-account", help="获取抖音账号作品列表（广域库）")
    command.add_argument("--user-id", "--userId", dest="user_id")
    command.add_argument("--unique-name", "--uniqueName", dest="unique_name")
    command.add_argument("--short-id", "--shortId", dest="short_id")
    _add_page(command)
    _add_dates(command)
    _add_json(command)

    command = subparsers.add_parser("search-douyin-articles", help="搜索关键词获取抖音作品（优质库）")
    _add_keyword(command)
    _add_dates(command)
    _add_offset_sort(command)
    _add_json(command)

    command = subparsers.add_parser("search-douyin-works", help="搜索关键词获取抖音作品（广域库）")
    _add_keyword(command)
    command.add_argument("--exact-match", "--exactMatch", dest="exact_match", type=_boolean, default=False)
    _add_dates(command)
    _add_page(command)
    _add_json(command)

    command = subparsers.add_parser("query-douyin-work", help="获取抖音作品内容详情（优质库）")
    command.add_argument("--work-id", "--workId", dest="work_id")
    command.add_argument("--work-url", "--workUrl", dest="work_url", type=_http_url)
    _add_json(command)

    command = subparsers.add_parser("get-douyin-work-detail", help="获取抖音作品内容详情（广域库）")
    command.add_argument("--video-id", "--videoId", dest="video_id", required=True)
    _add_json(command)

    command = subparsers.add_parser("recommend-douyin-accounts", help="获取抖音热门账号推荐")
    command.add_argument("--date-type", "--dateType", dest="date_type", choices=("days", "weeks", "months"), required=True)
    command.add_argument("--rank-date", "--rankDate", dest="rank_date", type=_date, required=True)
    _add_category(command, "账号类别", required=True)
    _add_json(command)

    command = subparsers.add_parser("douyin-likes-rank", help="获取抖音每日热门作品榜")
    _add_category(command, "作品类别，不传查询全部")
    command.add_argument("--start-time", "--startTime", dest="start_time", type=_date)
    command.add_argument("--end-time", "--endTime", dest="end_time", type=_date)
    _add_json(command)

    command = subparsers.add_parser("query-douyin-user", help="获取抖音账号信息（优质库）")
    command.add_argument("--account-id", "--accountId", dest="account_id", required=True)
    _add_json(command)

    command = subparsers.add_parser("search-douyin-ai-works", help="搜索抖音 AI 相关作品")
    _add_keyword(command)
    command.add_argument("--page-num", "--pageNum", dest="page_num", type=_positive_int, default=1)
    command.add_argument("--page-size", "--pageSize", dest="page_size", type=_positive_int, default=20)
    command.add_argument("--start-time", "--startTime", dest="start_time", type=_datetime_value)
    command.add_argument("--end-time", "--endTime", dest="end_time", type=_datetime_value)
    _add_json(command)

    for name, help_text in (("douyin-daily-rank", "抖音每日点赞飙升榜"), ("douyin-weekly-rank", "抖音七日点赞飙升榜")):
        command = subparsers.add_parser(name, help=help_text)
        _add_category(command, "分类，不传或填写全部查询全部")
        command.add_argument("--start-time", "--startTime", dest="start_time", type=_date)
        _add_json(command)

    command = subparsers.add_parser("extract-douyin-audio-text", help="提取抖音视频文案/字幕")
    command.add_argument("--url", required=True, type=_http_url, help="抖音视频链接")
    _add_json(command)
    return parser


def _run_search_users(args: argparse.Namespace) -> None:
    keyword = args.keyword_option if args.keyword_option is not None else (args.keyword or "")
    _run(
        args,
        "search-users",
        "抖音账号搜索",
        lambda _: build_search_payload(keyword, args.offset, args.sort_type),
    )


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    commands = {
        "search-douyin-accounts": ("search-accounts", "抖音广域账号搜索", _build_search_account_payload),
        "query-douyin-work-list": ("query-work-list", "抖音优质账号作品列表", _build_query_work_list_payload),
        "list-douyin-works-by-account": ("list-works-by-account", "抖音广域账号作品列表", _build_list_works_payload),
        "search-douyin-articles": ("search-articles", "抖音优质作品搜索", _build_search_article_payload),
        "search-douyin-works": ("search-works", "抖音广域作品搜索", _build_search_work_payload),
        "query-douyin-work": ("query-work", "抖音优质作品详情", _build_query_work_payload),
        "get-douyin-work-detail": ("work-detail", "抖音广域作品详情", _build_work_detail_payload),
        "recommend-douyin-accounts": ("recommend-accounts", "抖音热门账号推荐", _build_recommend_accounts_payload),
        "douyin-likes-rank": ("likes-rank", "抖音热门作品榜", _build_likes_rank_payload),
        "query-douyin-user": ("query-user", "抖音账号信息", _build_query_user_payload),
        "search-douyin-ai-works": ("search-ai-works", "抖音 AI 作品搜索", _build_ai_works_payload),
        "douyin-daily-rank": ("daily-rank", "抖音每日点赞飙升榜", _build_rank_payload),
        "douyin-weekly-rank": ("weekly-rank", "抖音七日点赞飙升榜", _build_rank_payload),
        "extract-douyin-audio-text": ("extract-audio-text", "抖音视频文案提取", _build_audio_text_payload),
    }
    if args.command == "search-douyin-users":
        _run_search_users(args)
    elif args.command in commands:
        endpoint_key, label, builder = commands[args.command]
        _run(args, endpoint_key, label, builder)
    else:
        parser.print_help()
        raise SystemExit(1)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
