"""Visible tests for the ledger package."""

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ledger.ledger import apply_discount, merge_intervals, parse_amount, sum_by_category


class LedgerSmokeTest(unittest.TestCase):
    def test_sum_by_category(self):
        entries = [
            {"id": 1, "category": "food", "amount_cents": 1200},
            {"id": 2, "category": "travel", "amount_cents": 500},
            {"id": 3, "category": "food", "amount_cents": 300},
        ]
        self.assertEqual(sum_by_category(entries, "food"), {1: 1200, 3: 300})

    def test_parse_amount_basic(self):
        self.assertEqual(parse_amount("12.34"), 1234)
        self.assertEqual(parse_amount("-3.05"), -305)

    def test_parse_amount_more_than_two_decimals(self):
        with self.assertRaises(ValueError):
            parse_amount("12.345")

    def test_apply_discount_basic(self):
        self.assertEqual(apply_discount(1000, 10), 900)

    def test_apply_discount_out_of_range(self):
        with self.assertRaises(ValueError):
            apply_discount(1000, 101)

    def test_merge_touching(self):
        self.assertEqual(merge_intervals([(0, 1), (1, 2)]), [(0, 2)])


if __name__ == "__main__":
    unittest.main()
