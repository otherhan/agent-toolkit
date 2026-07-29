"""Deterministic, standard-library data clients derived from a-stock-data v3.5.1."""

from __future__ import annotations

import json
import math
import random
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
)
SH_INDEX = {"000300", "000905", "000016", "000688", "000852", "000010"}
REPORT_API = "https://reportapi.eastmoney.com/report/list"
STOCK_INFO_API = "https://push2.eastmoney.com/api/qt/stock/get"
GLOBAL_NEWS_API = "https://np-weblist.eastmoney.com/comm/web/getFastNewsList"
TENCENT_QUOTE_API = "https://qt.gtimg.cn/q="
_eastmoney_last_call = 0.0


class AStockDataError(RuntimeError):
    """A provider, input, or parsing failure safe to expose through the CLI."""


def retrieved_at() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_ticker(value: str) -> str:
    raw = value.strip().lower()
    if raw.startswith(("sh", "sz", "bj")):
        raw = raw[2:]
    if "." in raw:
        raw = raw.split(".", 1)[0]
    if len(raw) != 6 or not raw.isdigit():
        raise AStockDataError(f"invalid ticker {value!r}; expected six digits with optional market")
    return raw


def prefixed_ticker(value: str) -> str:
    raw = value.strip().lower()
    if raw.startswith(("sh", "sz", "bj")):
        return raw[:2] + normalize_ticker(raw)
    code = normalize_ticker(raw)
    if code.startswith("92"):
        return "bj" + code
    if code in SH_INDEX or code.startswith(("5", "6", "9")):
        return "sh" + code
    if code.startswith(("4", "8")):
        return "bj" + code
    return "sz" + code


def _float(values: List[str], index: int) -> Optional[float]:
    if index >= len(values) or values[index] == "":
        return None
    try:
        return float(values[index])
    except ValueError:
        return None


def parse_tencent_response(payload: str, requested: Mapping[str, str]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for line in payload.strip().split(";"):
        if not line.strip() or "=" not in line or '"' not in line:
            continue
        key = line.split("=", 1)[0].split("_")[-1]
        values = line.split('"', 2)[1].split("~")
        if len(values) < 53:
            continue
        output_key = requested.get(key, key[2:])
        result[output_key] = {
            "code": values[2] or key[2:],
            "market_code": key,
            "name": values[1],
            "price": _float(values, 3),
            "last_close": _float(values, 4),
            "open": _float(values, 5),
            "change_amount": _float(values, 31),
            "change_percent": _float(values, 32),
            "high": _float(values, 33),
            "low": _float(values, 34),
            "amount_10k_cny": _float(values, 37),
            "turnover_percent": _float(values, 38),
            "pe_ttm": _float(values, 39),
            "amplitude_percent": _float(values, 43),
            "float_market_cap_100m_cny": _float(values, 44),
            "market_cap_100m_cny": _float(values, 45),
            "pb": _float(values, 46),
            "limit_up": _float(values, 47),
            "limit_down": _float(values, 48),
            "volume_ratio": _float(values, 49),
            "pe_static": _float(values, 52),
        }
    return result


def _request_bytes(
    url: str,
    *,
    headers: Optional[Mapping[str, str]] = None,
    timeout: int = 15,
) -> bytes:
    request_headers: MutableMapping[str, str] = {"User-Agent": USER_AGENT}
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(url, headers=dict(request_headers))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        raise AStockDataError(f"provider returned HTTP {exc.code} for {url}") from exc
    except urllib.error.URLError as exc:
        raise AStockDataError(f"provider request failed for {url}: {exc.reason}") from exc


def _request_json(
    base_url: str,
    params: Mapping[str, Any],
    *,
    headers: Optional[Mapping[str, str]] = None,
    timeout: int = 15,
    eastmoney: bool = False,
) -> Dict[str, Any]:
    global _eastmoney_last_call
    if eastmoney:
        wait = 1.0 - (time.monotonic() - _eastmoney_last_call)
        if wait > 0:
            time.sleep(wait + random.uniform(0.1, 0.35))
    query = urllib.parse.urlencode(params)
    url = base_url + ("&" if "?" in base_url else "?") + query
    try:
        payload = _request_bytes(url, headers=headers, timeout=timeout)
    finally:
        if eastmoney:
            _eastmoney_last_call = time.monotonic()
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AStockDataError(f"provider returned invalid JSON for {base_url}") from exc
    if not isinstance(decoded, dict):
        raise AStockDataError(f"provider returned unexpected JSON for {base_url}")
    return decoded


def tencent_quotes(codes: Iterable[str], timeout: int = 10) -> Dict[str, Any]:
    original = list(codes)
    if not original:
        raise AStockDataError("at least one ticker is required")
    if len(original) > 20:
        raise AStockDataError("quote accepts at most 20 tickers per request")
    requested = {prefixed_ticker(code): code for code in original}
    url = TENCENT_QUOTE_API + ",".join(requested)
    payload = _request_bytes(url, timeout=timeout).decode("gbk", errors="replace")
    result = parse_tencent_response(payload, requested)
    if not result:
        raise AStockDataError("Tencent returned no recognized quote rows")
    return result


def eastmoney_reports(code: str, pages: int = 1, timeout: int = 30) -> List[Dict[str, Any]]:
    ticker = normalize_ticker(code)
    pages = max(1, min(pages, 5))
    records: List[Dict[str, Any]] = []
    for page in range(1, pages + 1):
        params = {
            "industryCode": "*",
            "pageSize": "100",
            "industry": "*",
            "rating": "*",
            "ratingChange": "*",
            "beginTime": "2000-01-01",
            "endTime": "2030-01-01",
            "pageNo": str(page),
            "fields": "",
            "qType": "0",
            "orgCode": "",
            "code": ticker,
            "rcode": "",
            "p": str(page),
            "pageNum": str(page),
            "pageNumber": str(page),
        }
        decoded = _request_json(
            REPORT_API,
            params,
            headers={"Referer": "https://data.eastmoney.com/"},
            timeout=timeout,
            eastmoney=True,
        )
        rows = decoded.get("data") or []
        if not isinstance(rows, list) or not rows:
            break
        records.extend(row for row in rows if isinstance(row, dict))
        total_pages = int(decoded.get("TotalPage") or 1)
        if page >= total_pages:
            break
    return records


def eastmoney_stock_info(code: str, timeout: int = 15) -> Dict[str, Any]:
    ticker = normalize_ticker(code)
    market = 1 if ticker.startswith(("5", "6", "9")) else 0
    decoded = _request_json(
        STOCK_INFO_API,
        {
            "fltt": "2",
            "invt": "2",
            "fields": "f57,f58,f84,f85,f127,f116,f117,f189,f43",
            "secid": f"{market}.{ticker}",
        },
        timeout=timeout,
        eastmoney=True,
    )
    data = decoded.get("data") or {}
    if not isinstance(data, dict) or not data.get("f57"):
        raise AStockDataError("Eastmoney returned no stock information")
    return {
        "code": data.get("f57"),
        "name": data.get("f58"),
        "industry": data.get("f127"),
        "total_shares": data.get("f84"),
        "float_shares": data.get("f85"),
        "market_cap_cny": data.get("f116"),
        "float_market_cap_cny": data.get("f117"),
        "list_date": str(data.get("f189") or ""),
        "price": data.get("f43"),
    }


def eastmoney_global_news(limit: int = 20, timeout: int = 15) -> List[Dict[str, Any]]:
    limit = max(1, min(limit, 100))
    decoded = _request_json(
        GLOBAL_NEWS_API,
        {
            "client": "web",
            "biz": "web_724",
            "fastColumn": "102",
            "sortEnd": "",
            "pageSize": str(limit),
            "req_trace": str(uuid.uuid4()),
        },
        headers={"Referer": "https://kuaixun.eastmoney.com/"},
        timeout=timeout,
        eastmoney=True,
    )
    rows = decoded.get("data", {}).get("fastNewsList", [])
    if not isinstance(rows, list):
        raise AStockDataError("Eastmoney returned unexpected news data")
    return [
        {
            "title": item.get("title", ""),
            "summary": (item.get("summary") or "")[:500],
            "time": item.get("showTime", ""),
        }
        for item in rows
        if isinstance(item, dict)
    ]


def valuation_metrics(
    price: float,
    eps: float,
    cagr: float,
    target_pe: float = 30.0,
) -> Dict[str, Any]:
    if price < 0 or target_pe <= 0:
        raise AStockDataError("price must be non-negative and target PE must be positive")
    forward_pe = None if eps <= 0 else price / eps
    peg = None if cagr <= 0 or forward_pe is None else forward_pe / (cagr * 100)
    if forward_pe is None or cagr <= 0:
        digestion_years = None
    elif forward_pe <= target_pe:
        digestion_years = 0.0
    else:
        digestion_years = math.log(forward_pe / target_pe) / math.log(1 + cagr)
    return {
        "forward_pe": forward_pe,
        "peg": peg,
        "pe_digestion_years": digestion_years,
        "inputs": {
            "price": price,
            "eps": eps,
            "cagr_decimal": cagr,
            "target_pe": target_pe,
        },
    }
