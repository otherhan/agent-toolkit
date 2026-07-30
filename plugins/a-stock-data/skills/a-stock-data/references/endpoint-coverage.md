# Endpoint coverage

The CLI exposes 52 bounded commands across the original ten data layers, local valuation, and
independent fallbacks. Run `capabilities --pretty` for provider URLs, dependency requirements, and
exact signatures.

## Command groups

| Group | Commands |
| --- | --- |
| Market | `tdx-bars`, `tdx-quotes`, `tdx-transactions`, `quote`, `baidu-kline` |
| Reports | `reports`, `industry-reports`, `report-pdf`, `eps-forecast`, `iwencai-search`, `iwencai-query` |
| Signals | `hot-reasons`, `northbound-realtime`, `northbound-history`, `concept-blocks`, `fund-flow-minute`, `dragon-tiger`, `daily-dragon-tiger`, `lockup-expiry`, `industry-ranking`, `board-fund-flow` |
| Funds | `margin-trading`, `block-trades`, `holder-count`, `dividends`, `fund-flow-120d` |
| News | `stock-news`, `cls-telegraph`, `global-news` |
| Fundamentals | `tdx-finance`, `tdx-f10`, `stock-info`, `financial-report` |
| Announcements | `announcements` |
| Limit market | `limit-up-pool`, `break-board-pool`, `limit-down-pool`, `yesterday-limit-up`, `limit-up-reasons`, `limit-sentiment` |
| ETF options | `option-contracts`, `option-quote`, `option-greeks` |
| Sentiment | `investor-relations`, `ths-hot-list`, `eastmoney-hot-rank`, `eastmoney-hot-concepts` |
| Valuation | `valuation`, `full-valuation` |
| Fallbacks | `dragon-tiger-backup`, `fund-flow-backup`, `announcements-backup` |

## Runtime levels

The direct `quote`, `reports`, `stock-info`, `global-news`, and `valuation` commands and their
generic `run` equivalents use the Python standard library. They remain available when optional
packages are absent.

The complete runtime uses:

- `requests` for reviewed direct HTTP integrations;
- `pandas` for table-shaped 10jqka and northbound results;
- `lxml` for consensus forecast HTML parsing;
- `mootdx` for TongdaXin TCP market, finance, and F10 data.

Only `iwencai-search` and `iwencai-query` require `IWENCAI_API_KEY`.

## Output and bounds

- Lists and pandas objects are normalized to JSON-safe values.
- NaN and infinity become `null`.
- Page sizes, limits, rankings, and batch ticker lists are bounded before provider access.
- Dates must use `YYYYMMDD` or `YYYY-MM-DD`.
- Provider, source URL, and UTC retrieval time appear in every successful envelope.
- Provider, parser, dependency, and parameter failures return a JSON error envelope.

## Upstream parity

The v3.5.1 upstream document counts 44 provider endpoints using a different counting convention:
some TongdaXin operations share one row, industry reports share the stock-report endpoint, and the
northbound history is a local cache. The Codex registry exposes those operations separately, so its
command count is 52 while retaining all documented layers and fallback functions.

The pinned source remains in `upstream-skill-v3.5.1.md` for attribution and regeneration. Do not
execute its tutorial examples directly.

## Validation gate

Keep an endpoint only when it has:

1. a registered, bounded command and signature;
2. provider and source metadata;
3. JSON-safe result conversion and structured errors;
4. a dependency and authentication declaration;
5. offline coverage for registry mapping and shared parsers;
6. a read-only live smoke path where the provider permits it.
