#!/usr/bin/env python3
"""Structured CLI for the Codex-native A-share data Skill."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent))

from a_stock_data import (  # noqa: E402
    AStockDataError,
    eastmoney_global_news,
    eastmoney_reports,
    eastmoney_stock_info,
    tencent_quotes,
    valuation_metrics,
)
from a_stock_data.sources import retrieved_at  # noqa: E402
from a_stock_data.full_commands import (  # noqa: E402
    capabilities as full_capabilities,
    dependency_status,
    invoke,
)


def envelope(command: str, source_name: str, source_url: str, data: Any) -> Dict[str, Any]:
    return {
        "ok": True,
        "command": command,
        "source": {"name": source_name, "url": source_url},
        "retrieved_at": retrieved_at(),
        "data": data,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="a-stock-data")
    subparsers = parser.add_subparsers(dest="command", required=True)

    capabilities = subparsers.add_parser("capabilities")
    capabilities.add_argument("--group")
    capabilities.add_argument("--pretty", action="store_true")

    doctor = subparsers.add_parser("doctor")
    doctor.add_argument("--pretty", action="store_true")

    generic = subparsers.add_parser("run")
    generic.add_argument("endpoint")
    generic.add_argument("--params", default="{}")
    generic.add_argument("--pretty", action="store_true")

    quote = subparsers.add_parser("quote")
    quote.add_argument("tickers", nargs="+")
    quote.add_argument("--timeout", type=int, default=10)
    quote.add_argument("--pretty", action="store_true")

    reports = subparsers.add_parser("reports")
    reports.add_argument("ticker")
    reports.add_argument("--pages", type=int, default=1)
    reports.add_argument("--limit", type=int, default=20)
    reports.add_argument("--timeout", type=int, default=30)
    reports.add_argument("--pretty", action="store_true")

    stock_info = subparsers.add_parser("stock-info")
    stock_info.add_argument("ticker")
    stock_info.add_argument("--timeout", type=int, default=15)
    stock_info.add_argument("--pretty", action="store_true")

    news = subparsers.add_parser("global-news")
    news.add_argument("--limit", type=int, default=20)
    news.add_argument("--timeout", type=int, default=15)
    news.add_argument("--pretty", action="store_true")

    valuation = subparsers.add_parser("valuation")
    valuation.add_argument("--price", type=float, required=True)
    valuation.add_argument("--eps", type=float, required=True)
    valuation.add_argument("--cagr", type=float, required=True)
    valuation.add_argument("--target-pe", type=float, default=30.0)
    valuation.add_argument("--pretty", action="store_true")
    return parser


def run(args: argparse.Namespace) -> Dict[str, Any]:
    if args.command == "capabilities":
        return envelope(
            "capabilities",
            "local endpoint registry",
            "",
            full_capabilities(args.group),
        )
    if args.command == "doctor":
        dependencies = dependency_status()
        return envelope(
            "doctor",
            "local runtime",
            "",
            {
                "dependencies": dependencies,
                "full_runtime_ready": all(dependencies.values()),
                "iwencai_api_key_configured": bool(os.environ.get("IWENCAI_API_KEY")),
            },
        )
    if args.command == "run":
        try:
            params = json.loads(args.params)
        except json.JSONDecodeError as exc:
            raise AStockDataError(f"--params is not valid JSON: {exc.msg}") from exc
        endpoint, data = invoke(args.endpoint, params)
        return envelope(args.endpoint, endpoint.provider, endpoint.source_url, data)
    if args.command == "quote":
        return envelope(
            "quote",
            "Tencent Finance",
            "https://qt.gtimg.cn/",
            tencent_quotes(args.tickers, timeout=args.timeout),
        )
    if args.command == "reports":
        records = eastmoney_reports(args.ticker, pages=args.pages, timeout=args.timeout)
        limit = max(1, min(args.limit, 100))
        return envelope(
            "reports",
            "Eastmoney Report API",
            "https://reportapi.eastmoney.com/report/list",
            records[:limit],
        )
    if args.command == "stock-info":
        return envelope(
            "stock-info",
            "Eastmoney Push2",
            "https://push2.eastmoney.com/api/qt/stock/get",
            eastmoney_stock_info(args.ticker, timeout=args.timeout),
        )
    if args.command == "global-news":
        return envelope(
            "global-news",
            "Eastmoney 7x24",
            "https://np-weblist.eastmoney.com/comm/web/getFastNewsList",
            eastmoney_global_news(args.limit, timeout=args.timeout),
        )
    if args.command == "valuation":
        return envelope(
            "valuation",
            "local calculation",
            "",
            valuation_metrics(args.price, args.eps, args.cagr, args.target_pe),
        )
    raise AStockDataError(f"unsupported command: {args.command}")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        output = run(args)
        exit_code = 0
    except Exception as exc:
        output = {
            "ok": False,
            "command": args.command,
            "retrieved_at": retrieved_at(),
            "error": {"type": exc.__class__.__name__, "message": str(exc)},
        }
        exit_code = 1
    indent = 2 if getattr(args, "pretty", False) else None
    print(json.dumps(output, ensure_ascii=False, indent=indent, allow_nan=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
