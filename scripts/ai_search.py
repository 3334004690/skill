#!/usr/bin/env python3
"""Search the web through the Aimaxhug Baidu AI Search gateway."""

import argparse
import json as json_mod
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared.client import AimaxhugClient, AimaxhugError

SEARCH_ENDPOINT = "https://apis.aimaxhug.cloud/v1/ai_search"


def add_search_args(parser):
    parser.add_argument("q", nargs="?", help="搜索关键词")
    parser.add_argument("--query", "-q", dest="query", help="搜索关键词（也可作为位置参数传入）")
    parser.add_argument("--method", choices=("post", "get"), default="post",
                        help="请求方式（默认: post）")
    parser.add_argument("--json", action="store_true", help="原样输出 JSON 结果")


def _references(data):
    refs = data.get("references", []) if isinstance(data, dict) else []
    return refs if isinstance(refs, list) else []


def _print_results(data):
    print(f"搜索完成（request_id: {data.get('request_id', '未知')}）")
    refs = _references(data)
    if not refs:
        print("未找到搜索结果。")
        return
    print(f"找到 {len(refs)} 条结果：\n")
    for i, ref in enumerate(refs, 1):
        title = ref.get("title") or "无标题"
        url = ref.get("url") or ""
        website = ref.get("website") or ref.get("type") or ""
        snippet = ref.get("snippet") or ref.get("content") or ""
        print(f"[{i}] {title}")
        if website:
            print(f"来源: {website}")
        print(f"URL: {url}")
        if ref.get("date"):
            print(f"日期: {ref['date']}")
        if snippet:
            print(f"摘要: {snippet}")
        if ref.get("rerank_score") is not None:
            print(f"相关性: {ref['rerank_score']}")
        print()


def cmd_run(args):
    query = (args.query or args.q or "").strip()
    if not query:
        print("Error: 必须提供搜索关键词 q", file=sys.stderr)
        sys.exit(1)

    client = AimaxhugClient()
    try:
        if args.method == "get":
            data = client.get(SEARCH_ENDPOINT, params={"q": query})
        else:
            data = client.post(SEARCH_ENDPOINT, json={"q": query})
    except AimaxhugError as exc:
        print(f"Error: 搜索失败: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json_mod.dumps(data, ensure_ascii=False, indent=2))
    else:
        _print_results(data)


def main():
    parser = argparse.ArgumentParser(description="百度 AI 搜索（返回搜索引用供回答使用）")
    sub = parser.add_subparsers(dest="subcommand")
    run_parser = sub.add_parser("run", help="执行搜索（默认）")
    add_search_args(run_parser)
    args = parser.parse_args()

    if args.subcommand is None:
        parser.print_help()
        sys.exit(1)
    if args.subcommand == "run":
        cmd_run(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
