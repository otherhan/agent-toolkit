---
name: a-stock-data
description: Fetch current China A-share market data through deterministic Codex commands. Use for A-share or ETF quotes, PE/PB/market-cap checks, company research reports, basic stock information, rolling market news, and forward-PE/PEG calculations. Use this data layer when another analysis workflow needs sourced market facts; do not present outputs as investment advice.
---

# A-Share Data

Use the bundled CLI instead of copying Python snippets into a temporary script. It returns a stable
JSON envelope with the source URL and retrieval timestamp.

## Run

Resolve `<skill-directory>` to the directory containing this `SKILL.md`, then run:

```bash
python3 "<skill-directory>/scripts/a_stock_data_cli.py" capabilities --pretty
python3 "<skill-directory>/scripts/a_stock_data_cli.py" quote 600519 000858 --pretty
python3 "<skill-directory>/scripts/a_stock_data_cli.py" reports 600519 --limit 10 --pretty
python3 "<skill-directory>/scripts/a_stock_data_cli.py" stock-info 600519 --pretty
python3 "<skill-directory>/scripts/a_stock_data_cli.py" global-news --limit 10 --pretty
python3 "<skill-directory>/scripts/a_stock_data_cli.py" valuation \
  --price 150 --eps 6.2 --cagr 0.18 --target-pe 30 --pretty
```

Network commands may require permission in a restricted Codex environment. Do not install packages:
the tested command path uses only the Python standard library.

## Workflow

1. Identify the smallest command that supplies the requested facts.
2. Run it once. For Eastmoney requests, keep the built-in serial throttle enabled.
3. Check `ok`, `source`, and `retrieved_at` before using `data`.
4. Distinguish observed values from calculations and interpretation.
5. Cite the named data source and timestamp in the answer.
6. For financial decisions, state that the result is informational and verify material figures
   against exchange filings or another authoritative source.

## Ticker rules

- Bare six-digit tickers are accepted.
- `sh`, `sz`, and `bj` prefixes are accepted when a code is ambiguous.
- Bare `000001` means Ping An Bank (`sz000001`); use `sh000001` for the SSE Composite.
- Common Shanghai indices such as `000300` and Shanghai ETFs beginning with `5` route to Shanghai.

## Failure handling

- If a provider rejects or throttles a request, stop repeated retries and report the provider error.
- Do not parallelize Eastmoney commands or loop over large ticker lists.
- Do not silently replace a failed value with a value from another date or instrument.
- Treat an empty result as unknown, not zero.

## Coverage

Read [references/endpoint-coverage.md](references/endpoint-coverage.md) before promising an endpoint
outside the six commands above. The original v3.5.1 reference is preserved at
[references/upstream-skill-v3.5.1.md](references/upstream-skill-v3.5.1.md) for porting and audit,
not as an instruction to execute untested snippets ad hoc.
