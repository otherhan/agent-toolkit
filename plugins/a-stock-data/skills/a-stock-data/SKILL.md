---
name: a-stock-data
description: Fetch and structure China A-share, index, ETF, and ETF-option data through a complete Codex CLI. Use for quotes, K-lines, order books, research reports, consensus forecasts, market signals, capital flows, dragon-tiger lists, lockups, margin trading, block trades, holders, dividends, news, financial statements, F10, announcements, limit-up pools, options, investor relations, popularity rankings, valuation, and independent fallback sources. Preserve provider attribution and timestamps; never present results as investment advice.
---

# A-Share Data

Use the bundled CLI. Do not copy Python snippets from the upstream reference into temporary files.
Every command returns a JSON envelope with `ok`, `command`, `source`, `retrieved_at`, and either
`data` or `error`.

## Start

Resolve `<skill-dir>` to this `SKILL.md` directory:

```bash
python3 "<skill-dir>/scripts/a_stock_data_cli.py" doctor --pretty
python3 "<skill-dir>/scripts/a_stock_data_cli.py" capabilities --pretty
python3 "<skill-dir>/scripts/a_stock_data_cli.py" capabilities --group signals --pretty
```

`doctor` reports optional packages without installing them. The zero-dependency commands below use
only the Python standard library:

```bash
python3 "<skill-dir>/scripts/a_stock_data_cli.py" quote 600519 000858 --pretty
python3 "<skill-dir>/scripts/a_stock_data_cli.py" reports 600519 --limit 10 --pretty
python3 "<skill-dir>/scripts/a_stock_data_cli.py" stock-info 600519 --pretty
python3 "<skill-dir>/scripts/a_stock_data_cli.py" global-news --limit 10 --pretty
python3 "<skill-dir>/scripts/a_stock_data_cli.py" valuation \
  --price 150 --eps 6.2 --cagr 0.18 --target-pe 30 --pretty
```

## Run the Complete Surface

Use `run <endpoint> --params '<JSON object>'`. Read
[references/endpoint-coverage.md](references/endpoint-coverage.md) when selecting an endpoint.

```bash
# K-line with moving averages
python3 "<skill-dir>/scripts/a_stock_data_cli.py" run baidu-kline \
  --params '{"code":"600519"}' --pretty

# Industry fund flow
python3 "<skill-dir>/scripts/a_stock_data_cli.py" run board-fund-flow \
  --params '{"board_type":"industry","period":"5d","top_n":10}' --pretty

# Margin trading
python3 "<skill-dir>/scripts/a_stock_data_cli.py" run margin-trading \
  --params '{"code":"600519","page_size":20}' --pretty

# Financial statement
python3 "<skill-dir>/scripts/a_stock_data_cli.py" run financial-report \
  --params '{"code":"600519","report_type":"lrb","num":4}' --pretty

# Limit-up market sentiment
python3 "<skill-dir>/scripts/a_stock_data_cli.py" run limit-sentiment \
  --params '{"date":"20260729"}' --pretty

# Investor questions and company replies
python3 "<skill-dir>/scripts/a_stock_data_cli.py" run investor-relations \
  --params '{"code":"002594","page_size":20,"page_num":1}' --pretty
```

The full upstream-compatible runtime uses `requests`, `pandas`, `mootdx`, and `lxml`. If `doctor`
reports a missing package, ask before installing it, then use:

```bash
python3 -m pip install -r "<skill-dir>/scripts/requirements.txt"
```

Only iWenCai endpoints require a key. Read it from `IWENCAI_API_KEY`; never print the value.

## Workflow

1. Select the smallest endpoint that supplies the requested facts.
2. Run `doctor` before the first full-runtime endpoint in an unfamiliar environment.
3. Keep Eastmoney calls serial; the bundled client applies delay and retry handling.
4. Check `ok`, `source`, and `retrieved_at` before interpreting `data`.
5. Treat empty results as unknown, not zero.
6. Distinguish live observations, historical facts, analyst forecasts, and local calculations.
7. If a primary source fails, use a registered independent fallback only when the task requires it;
   identify the fallback explicitly.
8. Verify material financial figures against exchange filings or another authoritative source.

## Ticker and Date Rules

- Accept bare six-digit codes and explicit `sh`, `sz`, or `bj` prefixes.
- Treat bare `000001` as Ping An Bank; use `sh000001` for the SSE Composite.
- Route common `000xxx` Shanghai indices and `5xxxxx` Shanghai ETFs to Shanghai.
- Use the endpoint signature returned by `capabilities`; pool endpoints generally use `YYYYMMDD`,
  while announcement and data-center endpoints also accept `YYYY-MM-DD`.

## Guardrails

- Do not place orders or mutate brokerage accounts.
- Do not parallelize Eastmoney calls or perform unbounded whole-market loops.
- Do not download a report PDF unless the user requests the file.
- Do not silently substitute a different date, market, security, or provider.
- Do not describe provider opinions or heuristic signals as facts.
- Present the result as informational, not personalized investment advice.

## Maintenance

The complete executable compatibility module is generated from the pinned, attributed v3.5.1
reference. After a reviewed reference update, run:

```bash
python3 "<skill-dir>/scripts/build_upstream_module.py"
python3 -m unittest discover -s "<skill-dir>/scripts/tests" -v
```

Local overlays are explicit in the builder and fail closed when their reviewed source text changes.
