#!/usr/bin/env python3
"""Xiaohongshu data tools backed by the Aimaxhug social API."""

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
    "hot-accounts": f"{SOCIAL_API_PREFIX}/story/api/xhsData/query",
    "account-detail": f"{SOCIAL_API_PREFIX}/story/api/xhsUser/queryAccountDetail",
    "work-detail": f"{SOCIAL_API_PREFIX}/story/api/xhsUser/queryWorkDetail",
    "search-users": f"{SOCIAL_API_PREFIX}/story/api/xhsUser/searchUser",
    "search-articles": f"{SOCIAL_API_PREFIX}/story/api/xhsUser/searchArticle",
    "search-ai-works": f"{SOCIAL_API_PREFIX}/story/api/parseWork/queryXhsAiMsgs",
    "comments": f"{SOCIAL_API_PREFIX}/story/api/xhs/commentSubmit",
    "viral-insight": f"{SOCIAL_API_PREFIX}/story/api/xhs/search/search",
    "seven-day-hot": f"{SOCIAL_API_PREFIX}/story/api/cozeSkill/getXhsCozeSkillDataSeven",
    "work-list": f"{SOCIAL_API_PREFIX}/story/api/xhsUser/queryWorkList",
    "low-powder-explosive": f"{SOCIAL_API_PREFIX}/story/api/cozeSkill/getLowPowderExplosiveArticle",
    "daily-hot": f"{SOCIAL_API_PREFIX}/story/api/cozeSkill/getXhsCozeSkillDataOne",
    "audio-text": f"{SOCIAL_API_PREFIX}/story/api/parseWork/audioTextExtract/submit/xhs",
}


def _compact(payload: dict) -> dict:
    return {key: value for key, value in payload.items() if value is not None}


def _text(value: Optional[str], name: str) -> str:
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


def _date_or_datetime(value: str) -> str:
    try:
        datetime.strptime(value, DATE_FORMAT)
        return value
    except (TypeError, ValueError):
        return _datetime_value(value)


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


def _build_hot_accounts(args: argparse.Namespace) -> dict:
    return _compact({"dateType": args.date_type, "rankDate": args.rank_date, "type": args.category})


def _build_account_detail(args: argparse.Namespace) -> dict:
    return _compact({"accountId": _text(args.account_id, "accountId"), "userId": args.user_id})


def _build_work_detail(args: argparse.Namespace) -> dict:
    work_id = _optional_text(args.work_id)
    work_link = _optional_text(args.work_link)
    if bool(work_id) == bool(work_link):
        raise ValueError("workId、workLink 必须二选一")
    return _compact({"workId": work_id, "workLink": work_link})


def _build_search_users(args: argparse.Namespace) -> dict:
    return {"keyword": _text(args.keyword, "keyword"), "offset": args.offset, "sortType": args.sort_type}


def _build_search_articles(args: argparse.Namespace) -> dict:
    return {
        "keyword": _text(args.keyword, "keyword"),
        "offset": args.offset,
        "sortType": args.sort_type,
        "exactMatch": args.exact_match,
    }


def _build_ai_works(args: argparse.Namespace) -> dict:
    _validate_range(args.start_time, args.end_time, "时间")
    return {
        "keyword": _text(args.keyword, "keyword"),
        "pageNum": args.page_num,
        "pageSize": args.page_size,
        "startTime": args.start_time,
        "endTime": args.end_time,
    }


def _build_comments(args: argparse.Namespace) -> dict:
    if args.data_num < -1:
        raise ValueError("dataNum 必须为 -1 或非负整数")
    return {"opusId": _text(args.opus_id, "opusId"), "dataNum": args.data_num}


def _build_viral_insight(args: argparse.Namespace) -> dict:
    _validate_range(args.start_date, args.end_date, "日期")
    return _compact(
        {
            "keyword": args.keyword,
            "pageNum": args.page_num,
            "pageSize": args.page_size,
            "startDate": args.start_date,
            "endDate": args.end_date,
        }
    )


def _build_seven_day_hot(args: argparse.Namespace) -> dict:
    return _compact({"rankDate": args.rank_date, "category": args.category})


def _build_work_list(args: argparse.Namespace) -> dict:
    red_id = _optional_text(args.red_id)
    user_id = _optional_text(args.user_id)
    if not red_id and not user_id:
        raise ValueError("redId、userid 至少提供一个")
    _validate_range(args.publish_time_start, args.publish_time_end, "发布时间")
    return _compact(
        {
            "redId": red_id,
            "userid": user_id,
            "offset": args.offset,
            "sortType": args.sort_type,
            "publishTimeStart": args.publish_time_start,
            "publishTimeEnd": args.publish_time_end,
        }
    )


def _build_low_powder(args: argparse.Namespace) -> dict:
    return {"category": _text(args.category, "category"), "rankDate": _text(args.rank_date, "rankDate")}


def _build_daily_hot(args: argparse.Namespace) -> dict:
    return {"rankDate": _text(args.rank_date, "rankDate"), "category": _text(args.category, "category")}


def _build_audio_text(args: argparse.Namespace) -> dict:
    return {"url": args.url}


def _request(args: argparse.Namespace, endpoint: str, label: str, payload: dict, method: str = "post") -> None:
    client = AimaxhugClient()
    headers = {"Content-Type": "application/json"}
    try:
        if method == "get":
            response = client.get(endpoint, params=payload, headers=headers, timeout=120)
        else:
            response = client.post(endpoint, json=payload, headers=headers, timeout=120)
    except AimaxhugError as exc:
        print(f"Error: {label}失败: {exc}", file=sys.stderr)
        raise SystemExit(1)
    if not args.json:
        print(f"{label}完成")
    print(json.dumps(response, ensure_ascii=False, indent=2))


def _run(args: argparse.Namespace, endpoint_key: str, label: str, builder, method: str = "post") -> None:
    try:
        payload = builder(args)
    except (TypeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
    _request(args, ENDPOINTS[endpoint_key], label, payload, method)


def _add_json(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="仅输出接口原始 JSON")


def _add_offset_sort(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--offset", type=_non_negative_int, default=0)
    parser.add_argument("--sort-type", "--sortType", dest="sort_type", choices=SORT_TYPES, default="_0")


def _add_page(parser: argparse.ArgumentParser, default_size: int = 10) -> None:
    parser.add_argument("--page-num", "--pageNum", dest="page_num", type=_positive_int, default=1)
    parser.add_argument("--page-size", "--pageSize", dest="page_size", type=_page_size, default=default_size)


def _add_date_range(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--start-date", "--startDate", dest="start_date", type=_date)
    parser.add_argument("--end-date", "--endDate", dest="end_date", type=_date)


def _add_time_range(parser: argparse.ArgumentParser, required: bool = False) -> None:
    parser.add_argument("--start-time", "--startTime", dest="start_time", type=_datetime_value, required=required)
    parser.add_argument("--end-time", "--endTime", dest="end_time", type=_datetime_value, required=required)


def _add_category(parser: argparse.ArgumentParser, required: bool = False) -> None:
    parser.add_argument("--category", "--type", dest="category", required=required)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="小红书平台解析工具")
    sub = parser.add_subparsers(dest="command")

    command = sub.add_parser("xhs-hot-accounts", help="小红书热门账号推荐")
    command.add_argument("--date-type", "--dateType", dest="date_type", type=int, choices=(1, 2, 3))
    command.add_argument("--rank-date", "--rankDate", dest="rank_date", type=_date)
    _add_category(command)
    _add_json(command)

    command = sub.add_parser("xhs-account-detail", help="获取小红书账号信息（优质库）")
    command.add_argument("--account-id", "--accountId", dest="account_id", required=True)
    command.add_argument("--user-id", "--userId", dest="user_id")
    _add_json(command)

    command = sub.add_parser("xhs-work-detail", help="获取小红书作品内容详情（优质库）")
    command.add_argument("--work-id", "--workId", dest="work_id")
    command.add_argument("--work-link", "--workLink", dest="work_link", type=_http_url)
    _add_json(command)

    command = sub.add_parser("search-xhs-users", help="搜索关键词获取小红书账号")
    command.add_argument("--keyword", "-k", required=True)
    _add_offset_sort(command)
    _add_json(command)

    command = sub.add_parser("search-xhs-articles", help="搜索关键词获取小红书作品")
    command.add_argument("--keyword", "-k", required=True)
    _add_offset_sort(command)
    command.add_argument("--exact-match", "--exactMatch", dest="exact_match", type=_boolean, default=False)
    _add_json(command)

    command = sub.add_parser("search-xhs-ai-works", help="搜索小红书 AI 相关作品")
    command.add_argument("--keyword", "-k", required=True)
    _add_page(command, default_size=20)
    _add_time_range(command, required=True)
    _add_json(command)

    command = sub.add_parser("xhs-comments", help="获取小红书一级评论")
    command.add_argument("--opus-id", "--opusId", dest="opus_id", required=True)
    command.add_argument("--data-num", "--dataNum", dest="data_num", type=int, required=True)
    _add_json(command)

    command = sub.add_parser("xhs-viral-insight", help="小红书爆款笔记洞察")
    command.add_argument("--keyword", "-k")
    _add_page(command)
    _add_date_range(command)
    _add_json(command)

    command = sub.add_parser("xhs-seven-day-hot", help="小红书七日爆款笔记")
    command.add_argument("--rank-date", "--rankDate", dest="rank_date", type=_date)
    _add_category(command)
    _add_json(command)

    command = sub.add_parser("xhs-work-list", help="查询小红书账号作品列表")
    command.add_argument("--red-id", "--redId", dest="red_id")
    command.add_argument("--user-id", "--userid", dest="user_id")
    _add_offset_sort(command)
    command.add_argument("--publish-time-start", "--publishTimeStart", dest="publish_time_start", type=_date_or_datetime)
    command.add_argument("--publish-time-end", "--publishTimeEnd", dest="publish_time_end", type=_date_or_datetime)
    _add_json(command)

    command = sub.add_parser("xhs-low-powder-explosive", help="小红书黑马爆文榜")
    _add_category(command, required=True)
    command.add_argument("--rank-date", "--rankDate", dest="rank_date", required=True, type=_date)
    _add_json(command)

    command = sub.add_parser("xhs-daily-hot", help="小红书每日爆款笔记榜单")
    command.add_argument("--rank-date", "--rankDate", dest="rank_date", required=True, type=_date)
    _add_category(command, required=True)
    _add_json(command)

    command = sub.add_parser("extract-xhs-audio-text", help="提取小红书视频文案")
    command.add_argument("--url", required=True, type=_http_url)
    _add_json(command)
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    commands = {
        "xhs-hot-accounts": ("hot-accounts", "小红书热门账号推荐", _build_hot_accounts, "post"),
        "xhs-account-detail": ("account-detail", "小红书账号信息", _build_account_detail, "post"),
        "xhs-work-detail": ("work-detail", "小红书作品详情", _build_work_detail, "post"),
        "search-xhs-users": ("search-users", "小红书账号搜索", _build_search_users, "post"),
        "search-xhs-articles": ("search-articles", "小红书作品搜索", _build_search_articles, "post"),
        "search-xhs-ai-works": ("search-ai-works", "小红书 AI 作品搜索", _build_ai_works, "post"),
        "xhs-comments": ("comments", "小红书一级评论", _build_comments, "post"),
        "xhs-viral-insight": ("viral-insight", "小红书爆款笔记洞察", _build_viral_insight, "post"),
        "xhs-seven-day-hot": ("seven-day-hot", "小红书七日爆款笔记", _build_seven_day_hot, "get"),
        "xhs-work-list": ("work-list", "小红书账号作品列表", _build_work_list, "post"),
        "xhs-low-powder-explosive": ("low-powder-explosive", "小红书黑马爆文榜", _build_low_powder, "get"),
        "xhs-daily-hot": ("daily-hot", "小红书每日爆款笔记榜单", _build_daily_hot, "get"),
        "extract-xhs-audio-text": ("audio-text", "小红书视频文案提取", _build_audio_text, "post"),
    }
    if args.command not in commands:
        parser.print_help()
        raise SystemExit(1)
    endpoint_key, label, builder, method = commands[args.command]
    _run(args, endpoint_key, label, builder, method)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
