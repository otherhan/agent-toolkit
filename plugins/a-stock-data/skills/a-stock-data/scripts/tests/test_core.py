from __future__ import annotations

import http.client
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

from a_stock_data import (  # noqa: E402
    AStockDataError,
    eastmoney_secid,
    normalize_ticker,
    parse_tencent_response,
    prefixed_ticker,
    valuation_metrics,
)
from a_stock_data import sources  # noqa: E402


class RoutingTests(unittest.TestCase):
    def test_market_prefixes_and_ambiguity(self) -> None:
        self.assertEqual(prefixed_ticker("600519"), "sh600519")
        self.assertEqual(prefixed_ticker("510050"), "sh510050")
        self.assertEqual(prefixed_ticker("000300"), "sh000300")
        self.assertEqual(prefixed_ticker("000001"), "sz000001")
        self.assertEqual(prefixed_ticker("sh000001"), "sh000001")
        self.assertEqual(prefixed_ticker("832000"), "bj832000")

    def test_eastmoney_secid_preserves_explicit_market(self) -> None:
        self.assertEqual(eastmoney_secid("sh000001"), "1.000001")
        self.assertEqual(eastmoney_secid("sz000001"), "0.000001")
        self.assertEqual(eastmoney_secid("000300"), "1.000300")
        self.assertEqual(eastmoney_secid("600519"), "1.600519")

    def test_invalid_ticker_fails_closed(self) -> None:
        with self.assertRaises(AStockDataError):
            normalize_ticker("519")


class TencentParserTests(unittest.TestCase):
    def test_parser_uses_calibrated_indexes(self) -> None:
        fields = [""] * 53
        fields[1] = "测试股份"
        fields[2] = "600000"
        fields[3] = "10.50"
        fields[39] = "12.3"
        fields[43] = "4.5"
        fields[44] = "101.0"
        fields[45] = "205.0"
        fields[46] = "1.8"
        payload = 'v_sh600000="' + "~".join(fields) + '";'
        parsed = parse_tencent_response(payload, {"sh600000": "600000"})["600000"]
        self.assertEqual(parsed["pe_ttm"], 12.3)
        self.assertEqual(parsed["amplitude_percent"], 4.5)
        self.assertEqual(parsed["float_market_cap_100m_cny"], 101.0)
        self.assertEqual(parsed["market_cap_100m_cny"], 205.0)
        self.assertEqual(parsed["pb"], 1.8)


class TransportTests(unittest.TestCase):
    def test_remote_disconnect_becomes_domain_error(self) -> None:
        opener = mock.Mock()
        opener.side_effect = http.client.RemoteDisconnected("closed")
        with mock.patch("urllib.request.urlopen", opener):
            with self.assertRaisesRegex(AStockDataError, "provider connection failed"):
                sources._request_bytes("https://example.invalid/")


class ValuationTests(unittest.TestCase):
    def test_forward_metrics(self) -> None:
        result = valuation_metrics(100, 5, 0.20, 15)
        self.assertEqual(result["forward_pe"], 20)
        self.assertEqual(result["peg"], 1)
        self.assertGreater(result["pe_digestion_years"], 0)

    def test_non_positive_eps_is_unknown(self) -> None:
        result = valuation_metrics(100, 0, 0.20)
        self.assertIsNone(result["forward_pe"])
        self.assertIsNone(result["peg"])


class CliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> dict:
        completed = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "a_stock_data_cli.py"), *args],
            check=False,
            capture_output=True,
            text=True,
        )
        return json.loads(completed.stdout)

    def test_capabilities_is_valid_json(self) -> None:
        output = self.run_cli("capabilities")
        self.assertTrue(output["ok"])
        self.assertGreaterEqual(len(output["data"]), 44)

    def test_generic_valuation(self) -> None:
        output = self.run_cli(
            "run",
            "valuation",
            "--params",
            '{"price":100,"eps":5,"cagr":0.2,"target_pe":15}',
        )
        self.assertTrue(output["ok"])
        self.assertEqual(output["data"]["forward_pe"], 20)

    def test_invalid_json_still_returns_json(self) -> None:
        output = self.run_cli("run", "valuation", "--params", "{")
        self.assertFalse(output["ok"])
        self.assertEqual(output["error"]["type"], "AStockDataError")


if __name__ == "__main__":
    unittest.main()
