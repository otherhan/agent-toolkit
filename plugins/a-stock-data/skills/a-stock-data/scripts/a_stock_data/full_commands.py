"""Complete endpoint registry and safe invocation layer."""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import math
import os
import re
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, Mapping

from .sources import (
    AStockDataError,
    eastmoney_global_news,
    eastmoney_reports,
    eastmoney_stock_info,
    tencent_quotes,
    valuation_metrics,
)


FULL_DEPENDENCIES = ("requests", "pandas", "mootdx", "lxml")
HTTP_DEPENDENCIES = ("requests",)
PANDAS_DEPENDENCIES = ("requests", "pandas")
HTML_DEPENDENCIES = ("requests", "pandas", "lxml")
TDX_DEPENDENCIES = ("requests", "mootdx")


@dataclass(frozen=True)
class Endpoint:
    name: str
    group: str
    provider: str
    source_url: str
    target: str
    description: str
    dependencies: tuple[str, ...] = HTTP_DEPENDENCIES
    writes_files: bool = False
    requires_key: str | None = None
    signature: str = ""

    def public(self) -> Dict[str, Any]:
        data = asdict(self)
        data.pop("target")
        return data


def _endpoint(
    name: str,
    group: str,
    provider: str,
    source_url: str,
    target: str,
    description: str,
    *,
    dependencies: tuple[str, ...] = HTTP_DEPENDENCIES,
    writes_files: bool = False,
    requires_key: str | None = None,
    signature: str = "",
) -> Endpoint:
    return Endpoint(
        name,
        group,
        provider,
        source_url,
        target,
        description,
        dependencies,
        writes_files,
        requires_key,
        signature,
    )


ENDPOINTS = [
    _endpoint("tdx-bars", "market", "mootdx / TongdaXin", "tcp://TongdaXin", "tdx:bars", "Multi-period OHLCV bars.", dependencies=TDX_DEPENDENCIES, signature="symbol, frequency=9, offset=100"),
    _endpoint("tdx-quotes", "market", "mootdx / TongdaXin", "tcp://TongdaXin", "tdx:quotes", "Real-time quote, order book, and volume fields.", dependencies=TDX_DEPENDENCIES, signature="symbol"),
    _endpoint("tdx-transactions", "market", "mootdx / TongdaXin", "tcp://TongdaXin", "tdx:transaction", "Tick transactions for a trading date.", dependencies=TDX_DEPENDENCIES, signature="symbol, date"),
    _endpoint("quote", "market", "Tencent Finance", "https://qt.gtimg.cn/", "core:tencent_quotes", "Price, PE, PB, market cap, turnover, and limits.", dependencies=(), signature="codes, timeout=10"),
    _endpoint("baidu-kline", "market", "Baidu Stock", "https://finance.pae.baidu.com/selfselect/getstockquotation", "upstream:baidu_kline_with_ma", "Daily K-line with MA5, MA10, and MA20.", signature="code, start_time=''"),
    _endpoint("reports", "reports", "Eastmoney Report API", "https://reportapi.eastmoney.com/report/list", "core:eastmoney_reports", "Stock research-report metadata and forecast fields.", dependencies=(), signature="code, max_pages=1"),
    _endpoint("industry-reports", "reports", "Eastmoney Report API", "https://reportapi.eastmoney.com/report/list", "upstream:eastmoney_industry_reports", "Industry research-report metadata.", signature="industry_code='*', max_pages=5, begin_time, end_time"),
    _endpoint("report-pdf", "reports", "Eastmoney PDF", "https://pdf.dfcfw.com/", "upstream:download_pdf", "Download one report PDF from a report record.", writes_files=True, signature="record, target_dir"),
    _endpoint("eps-forecast", "reports", "10jqka", "https://basic.10jqka.com.cn/", "upstream:ths_eps_forecast", "Consensus EPS forecast table.", dependencies=HTML_DEPENDENCIES, signature="code"),
    _endpoint("iwencai-search", "reports", "iWenCai OpenAPI", "https://openapi.iwencai.com/", "upstream:iwencai_search", "Natural-language report search.", requires_key="IWENCAI_API_KEY", signature="query, channel='report', size=50"),
    _endpoint("iwencai-query", "reports", "iWenCai OpenAPI", "https://openapi.iwencai.com/", "upstream:iwencai_query", "Natural-language structured query.", requires_key="IWENCAI_API_KEY", signature="query, page=1, limit=50"),
    _endpoint("hot-reasons", "signals", "10jqka", "https://eq.10jqka.com.cn/", "upstream:ths_hot_reason", "Strong stocks and editorial reason tags.", dependencies=PANDAS_DEPENDENCIES, signature="date=None"),
    _endpoint("northbound-realtime", "signals", "10jqka", "https://data.hexin.cn/", "upstream:hsgt_realtime", "Minute-level northbound flow.", dependencies=PANDAS_DEPENDENCIES, signature=""),
    _endpoint("northbound-history", "signals", "Local cache", "", "upstream:_load_northbound_history", "Locally cached northbound snapshots.", dependencies=PANDAS_DEPENDENCIES, signature="n=20"),
    _endpoint("concept-blocks", "signals", "Eastmoney Push2", "https://push2.eastmoney.com/api/qt/slist/get", "upstream:eastmoney_concept_blocks", "Industry, concept, and region membership.", signature="code"),
    _endpoint("fund-flow-minute", "signals", "Eastmoney Push2", "https://push2.eastmoney.com/api/qt/stock/fflow/kline/get", "upstream:eastmoney_fund_flow_minute", "Minute-level order-size fund flow.", signature="code"),
    _endpoint("dragon-tiger", "signals", "Eastmoney Data Center", "https://datacenter-web.eastmoney.com/", "upstream:dragon_tiger_board", "Stock dragon-tiger records and top seats.", signature="code, trade_date, look_back=30"),
    _endpoint("daily-dragon-tiger", "signals", "Eastmoney Data Center", "https://datacenter-web.eastmoney.com/", "upstream:daily_dragon_tiger", "Daily whole-market dragon-tiger ranking.", signature="trade_date=None, min_net_buy=None"),
    _endpoint("lockup-expiry", "signals", "Eastmoney Data Center", "https://datacenter-web.eastmoney.com/", "upstream:lockup_expiry", "Historical and upcoming lockup expiries.", signature="code, trade_date, forward_days=90"),
    _endpoint("industry-ranking", "signals", "Eastmoney Push2", "https://push2.eastmoney.com/api/qt/clist/get", "upstream:industry_comparison", "Industry gain/loss and breadth ranking.", signature="top_n=20"),
    _endpoint("board-fund-flow", "signals", "Eastmoney Push2", "https://push2.eastmoney.com/api/qt/clist/get", "upstream:board_fund_flow", "Industry, concept, or region fund flow for today, 5d, or 10d.", signature="board_type='industry', period='today', top_n=20"),
    _endpoint("margin-trading", "funds", "Eastmoney Data Center", "https://datacenter-web.eastmoney.com/", "upstream:margin_trading", "Margin financing and securities lending.", signature="code, page_size=30"),
    _endpoint("block-trades", "funds", "Eastmoney Data Center", "https://datacenter-web.eastmoney.com/", "upstream:block_trade", "Block trade price, volume, parties, and premium.", signature="code, page_size=20"),
    _endpoint("holder-count", "funds", "Eastmoney Data Center", "https://datacenter-web.eastmoney.com/", "upstream:holder_num_change", "Shareholder count and concentration changes.", signature="code, page_size=10"),
    _endpoint("dividends", "funds", "Eastmoney Data Center", "https://datacenter-web.eastmoney.com/", "upstream:dividend_history", "Dividend, bonus-share, and transfer history.", signature="code, page_size=20"),
    _endpoint("fund-flow-120d", "funds", "Eastmoney Push2", "https://push2.eastmoney.com/api/qt/stock/fflow/daykline/get", "upstream:stock_fund_flow_120d", "Daily order-size fund flow for up to 120 days.", signature="code"),
    _endpoint("stock-news", "news", "Eastmoney Search", "https://search-api-web.eastmoney.com/", "upstream:eastmoney_stock_news", "Stock-specific news stream.", signature="code, page_size=20"),
    _endpoint("cls-telegraph", "news", "CLS", "https://www.cls.cn/nodeapi/updateTelegraphList", "upstream:cls_telegraph", "Real-time market telegraph.", signature="page_size=50"),
    _endpoint("global-news", "news", "Eastmoney 7x24", "https://np-weblist.eastmoney.com/comm/web/getFastNewsList", "core:eastmoney_global_news", "Rolling global financial headlines.", dependencies=(), signature="page_size=20, timeout=15"),
    _endpoint("tdx-finance", "fundamentals", "mootdx / TongdaXin", "tcp://TongdaXin", "tdx:finance", "37-field quarterly finance snapshot.", dependencies=TDX_DEPENDENCIES, signature="symbol"),
    _endpoint("tdx-f10", "fundamentals", "mootdx / TongdaXin", "tcp://TongdaXin", "tdx:F10", "F10 company text by category.", dependencies=TDX_DEPENDENCIES, signature="symbol, name"),
    _endpoint("stock-info", "fundamentals", "Eastmoney Push2", "https://push2.eastmoney.com/api/qt/stock/get", "core:eastmoney_stock_info", "Name, industry, shares, market cap, listing date.", dependencies=(), signature="code, timeout=15"),
    _endpoint("financial-report", "fundamentals", "Sina Finance", "https://quotes.sina.cn/cn/api/openapi.php/", "upstream:sina_financial_report", "Income statement, balance sheet, or cash-flow statement.", signature="code, report_type='lrb', num=8"),
    _endpoint("announcements", "announcements", "CNInfo", "https://www.cninfo.com.cn/new/hisAnnouncement/query", "upstream:cninfo_announcements", "Exchange announcements with PDF links.", signature="code, page_size=30"),
    _endpoint("limit-up-pool", "limit", "Eastmoney Push2Ex", "https://push2ex.eastmoney.com/getTopicZTPool", "upstream:em_zt_pool", "Limit-up pool and board statistics.", signature="date"),
    _endpoint("break-board-pool", "limit", "Eastmoney Push2Ex", "https://push2ex.eastmoney.com/getTopicZBPool", "upstream:em_zb_pool", "Stocks that opened after reaching limit-up.", signature="date"),
    _endpoint("limit-down-pool", "limit", "Eastmoney Push2Ex", "https://push2ex.eastmoney.com/getTopicDTPool", "upstream:em_dt_pool", "Limit-down pool.", signature="date"),
    _endpoint("yesterday-limit-up", "limit", "Eastmoney Push2Ex", "https://push2ex.eastmoney.com/getTopicYzztPool", "upstream:em_yzt_pool", "Performance of yesterday's limit-up stocks.", signature="date"),
    _endpoint("limit-up-reasons", "limit", "10jqka", "https://data.10jqka.com.cn/", "upstream:ths_limit_up_pool", "Limit-up reasons, pattern, and seal rate.", signature="date"),
    _endpoint("limit-sentiment", "limit", "Composite", "", "upstream:limit_up_sentiment", "Break rate, maximum board height, and ladder.", signature="date"),
    _endpoint("option-contracts", "options", "Sina Options", "https://hq.sinajs.cn/", "upstream:sina_option_codes", "ETF option contracts grouped by expiry.", signature="underlying='510050', call=true"),
    _endpoint("option-quote", "options", "Sina Options", "https://hq.sinajs.cn/", "upstream:sina_option_tquote", "Option T-quote and market fields.", signature="code"),
    _endpoint("option-greeks", "options", "Sina Options", "https://hq.sinajs.cn/", "upstream:sina_option_greeks", "Delta, Gamma, Theta, Vega, and IV.", signature="code"),
    _endpoint("investor-relations", "sentiment", "CNInfo IRM", "https://irm.cninfo.com.cn/", "upstream:cninfo_irm", "Investor questions and official company replies.", signature="code, page_size=30, page_num=1"),
    _endpoint("ths-hot-list", "sentiment", "10jqka", "https://eq.10jqka.com.cn/", "upstream:ths_hot_list", "Popularity, concepts, and rank movement.", signature="period='hour'"),
    _endpoint("eastmoney-hot-rank", "sentiment", "Eastmoney", "https://emappdata.eastmoney.com/", "upstream:em_hot_rank", "Eastmoney stock popularity ranking.", signature="top=50"),
    _endpoint("eastmoney-hot-concepts", "sentiment", "Eastmoney", "https://emappdata.eastmoney.com/", "upstream:em_hot_concept", "Current hot concepts associated with a stock.", signature="code"),
    _endpoint("valuation", "valuation", "Local calculation", "", "core:valuation_metrics", "Forward PE, PEG, and PE digestion time.", dependencies=(), signature="price, eps, cagr, target_pe=30"),
    _endpoint("full-valuation", "valuation", "Composite", "", "upstream:full_valuation", "Quote plus consensus forecast and valuation metrics.", dependencies=HTML_DEPENDENCIES, signature="code"),
    _endpoint("dragon-tiger-backup", "backups", "SSE / SZSE", "https://query.sse.com.cn/", "upstream:dragon_tiger_backup", "Official exchange fallback for dragon-tiger data.", signature="trade_date"),
    _endpoint("fund-flow-backup", "backups", "Sina Finance", "https://quotes.sina.cn/", "upstream:fund_flow_backup", "Independent daily order-size fund-flow fallback.", signature="code, days=60"),
    _endpoint("announcements-backup", "backups", "SZSE / Eastmoney", "https://www.szse.cn/", "upstream:announcements_backup", "Announcement fallback with PDF links.", signature="code, page_size=20"),
]

ENDPOINT_BY_NAME = {endpoint.name: endpoint for endpoint in ENDPOINTS}


def dependency_status() -> Dict[str, bool]:
    return {name: importlib.util.find_spec(name) is not None for name in FULL_DEPENDENCIES}


def capabilities(group: str | None = None) -> list[Dict[str, Any]]:
    selected = ENDPOINTS
    if group:
        selected = [endpoint for endpoint in selected if endpoint.group == group]
    return [endpoint.public() for endpoint in selected]


def _bounded(params: Mapping[str, Any]) -> None:
    limits = {
        "page": 100,
        "page_num": 100,
        "pages": 5,
        "max_pages": 5,
        "page_size": 100,
        "limit": 100,
        "size": 100,
        "top": 100,
        "top_n": 100,
        "n": 365,
        "days": 365,
        "look_back": 365,
        "forward_days": 365,
        "offset": 2000,
    }
    for key, maximum in limits.items():
        if key not in params:
            continue
        value = params[key]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0 or value > maximum:
            raise AStockDataError(f"{key} must be an integer between 0 and {maximum}")
    for key in ("codes", "symbol"):
        value = params.get(key)
        if isinstance(value, list) and len(value) > 20:
            raise AStockDataError(f"{key} accepts at most 20 items")
    for key in ("date", "trade_date"):
        value = params.get(key)
        if value is not None and not re.fullmatch(r"\d{8}|\d{4}-\d{2}-\d{2}", str(value)):
            raise AStockDataError(f"{key} must be YYYYMMDD or YYYY-MM-DD")


def _json_safe(value: Any) -> Any:
    if hasattr(value, "to_dict") and value.__class__.__module__.startswith("pandas"):
        value = value.to_dict(orient="records")
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except (TypeError, ValueError):
            pass
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _load_upstream(endpoint: Endpoint) -> Any:
    missing = [name for name in endpoint.dependencies if not dependency_status()[name]]
    if missing:
        joined = " ".join(missing)
        raise AStockDataError(
            f"{endpoint.name} requires optional packages: {', '.join(missing)}; "
            f"install with: python3 -m pip install {joined}"
        )
    return importlib.import_module(".upstream_full", __package__)


def _call_checked(function: Callable[..., Any], params: Dict[str, Any]) -> Any:
    signature = inspect.signature(function)
    try:
        bound = signature.bind(**params)
    except TypeError as exc:
        raise AStockDataError(str(exc)) from exc
    return function(*bound.args, **bound.kwargs)


def invoke(name: str, params: Dict[str, Any]) -> tuple[Endpoint, Any]:
    endpoint = ENDPOINT_BY_NAME.get(name)
    if endpoint is None:
        raise AStockDataError(f"unknown endpoint {name!r}")
    if not isinstance(params, dict):
        raise AStockDataError("params must be a JSON object")
    _bounded(params)
    if endpoint.requires_key and not os.environ.get(endpoint.requires_key):
        raise AStockDataError(
            f"{endpoint.name} requires environment variable {endpoint.requires_key}"
        )

    kind, target = endpoint.target.split(":", 1)
    if kind == "core":
        core_functions: Dict[str, Callable[..., Any]] = {
            "tencent_quotes": tencent_quotes,
            "eastmoney_reports": lambda code, max_pages=1, timeout=30: eastmoney_reports(
                code, pages=max_pages, timeout=timeout
            ),
            "eastmoney_stock_info": eastmoney_stock_info,
            "eastmoney_global_news": lambda page_size=20, timeout=15: eastmoney_global_news(
                page_size, timeout=timeout
            ),
            "valuation_metrics": valuation_metrics,
        }
        result = _call_checked(core_functions[target], params)
    else:
        module = _load_upstream(endpoint)
        if kind == "upstream":
            result = _call_checked(getattr(module, target), params)
        elif kind == "tdx":
            client = module.tdx_client()
            result = _call_checked(getattr(client, target), params)
        else:
            raise AStockDataError(f"invalid endpoint target {endpoint.target!r}")
    return endpoint, _json_safe(result)
