# Endpoint coverage

## Codex-tested command surface

| Command | Provider | Capability |
| --- | --- | --- |
| `capabilities` | Local | Report the installed command surface |
| `quote` | Tencent Finance | Price, change, PE, PB, market cap, turnover, limits |
| `reports` | Eastmoney Report API | Stock research-report metadata and forecast fields |
| `stock-info` | Eastmoney Push2 | Name, industry, shares, market cap, listing date |
| `global-news` | Eastmoney 7×24 | Rolling global financial headlines |
| `valuation` | Local | Forward PE, PEG, and PE digestion time |

## Upstream parity

This first Codex-native release intentionally exposes only endpoints with a deterministic CLI,
offline parser tests, bounded arguments, source metadata, and structured error handling.

The upstream v3.5.1 Skill documents 44 endpoints across quotes, reports, signals, capital flows,
news, fundamentals, announcements, limit-up trading, ETF options, and investor interactions.
Those definitions remain in `upstream-skill-v3.5.1.md` for attribution and incremental porting.
Do not describe an unported endpoint as supported by the CLI.

## Porting gate

Add another endpoint only with:

1. a bounded CLI command;
2. a provider-specific parser separated from transport;
3. offline parser tests using representative fixtures;
4. source URL and retrieval time in the output envelope;
5. throttling or authentication handling where required;
6. a live smoke test that does not place orders or mutate provider state.
