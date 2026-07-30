from __future__ import annotations

import ast
import sys
import unittest
from collections import Counter
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

from a_stock_data.full_commands import (  # noqa: E402
    ENDPOINTS,
    ENDPOINT_BY_NAME,
    capabilities,
    invoke,
)
from a_stock_data.sources import AStockDataError  # noqa: E402


EXPECTED_GROUPS = {
    "market",
    "reports",
    "signals",
    "funds",
    "news",
    "fundamentals",
    "announcements",
    "limit",
    "options",
    "sentiment",
    "valuation",
    "backups",
}


class RegistryTests(unittest.TestCase):
    def test_complete_surface_is_registered(self) -> None:
        self.assertGreaterEqual(len(ENDPOINTS), 44)
        self.assertEqual(set(ENDPOINT_BY_NAME), {endpoint.name for endpoint in ENDPOINTS})
        self.assertEqual({endpoint.group for endpoint in ENDPOINTS}, EXPECTED_GROUPS)

    def test_names_are_unique(self) -> None:
        counts = Counter(endpoint.name for endpoint in ENDPOINTS)
        self.assertFalse([name for name, count in counts.items() if count != 1])

    def test_every_endpoint_has_traceable_metadata(self) -> None:
        for endpoint in ENDPOINTS:
            with self.subTest(endpoint=endpoint.name):
                self.assertTrue(endpoint.provider)
                self.assertTrue(endpoint.description)
                self.assertTrue(endpoint.signature or endpoint.name == "northbound-realtime")

    def test_group_filter(self) -> None:
        self.assertTrue(capabilities("options"))
        self.assertTrue(all(item["group"] == "options" for item in capabilities("options")))

    def test_bounds_fail_closed(self) -> None:
        with self.assertRaises(AStockDataError):
            invoke("global-news", {"page_size": 1000})

    def test_generated_upstream_module_has_all_targets(self) -> None:
        module_path = SCRIPTS_DIR / "a_stock_data" / "upstream_full.py"
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
        expected = {
            endpoint.target.split(":", 1)[1]
            for endpoint in ENDPOINTS
            if endpoint.target.startswith("upstream:")
        }
        self.assertFalse(expected - functions)


if __name__ == "__main__":
    unittest.main()
