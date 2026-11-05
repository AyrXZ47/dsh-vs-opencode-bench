"""Hidden acceptance tests for the ledger phase."""

import os
import sys
import unittest

sys.path.insert(0, os.getcwd())

from ledger.ledger import apply_discount, merge_intervals, parse_amount, sum_by_category


class LedgerAcceptance(unittest.TestCase):
    def test_no_state_leak_between_calls(self):
        a = [{"id": 1, "category": "food", "amount_cents": 100}]
        b = [{"id": 2, "category": "travel", "amount_cents": 200}]
        self.assertEqual(sum_by_category(a, "food"), {1: 100})
        self.assertEqual(sum_by_category(b, "travel"), {2: 200})
        self.assertEqual(sum_by_category([], "food"), {})

    def test_parse_amount_valid(self):
        cases = {
            "0": 0,
            "0.00": 0,
            "12": 1200,
            "12.3": 1230,
            "12.34": 1234,
            "+5.05": 505,
            "-0.01": -1,
            " 7.50 ": 750,
            "00012.34": 1234,
        }
        for text, expected in cases.items():
            self.assertEqual(parse_amount(text), expected, text)

    def test_parse_amount_invalid(self):
        for text in ("", " ", ".5", "12.", "12.345", "1,23", "abc", "1.2.3", "1e3", "--1", "+", "12.-3", "1_000"):
            with self.assertRaises(ValueError, msg=text):
                parse_amount(text)

    def test_apply_discount(self):
        self.assertEqual(apply_discount(1000, 0), 1000)
        self.assertEqual(apply_discount(1000, 10), 900)
        self.assertEqual(apply_discount(1000, 100), 0)
        self.assertEqual(apply_discount(1001, 50), 501)
        self.assertEqual(apply_discount(999, 50), 500)
        self.assertEqual(apply_discount(1, 50), 1)
        self.assertEqual(apply_discount(3, 50), 2)
        self.assertEqual(apply_discount(0, 100), 0)

    def test_apply_discount_invalid(self):
        for amount, percent in ((-1, 10), (100, -1), (100, 101), (100, 101.5)):
            with self.assertRaises(ValueError, msg=(amount, percent)):
                apply_discount(amount, percent)

    def test_merge_intervals(self):
        self.assertEqual(merge_intervals([]), [])
        self.assertEqual(merge_intervals([(1, 2)]), [(1, 2)])
        self.assertEqual(merge_intervals([(0, 1), (1, 2)]), [(0, 2)])
        self.assertEqual(merge_intervals([(0, 2), (1, 3)]), [(0, 3)])
        self.assertEqual(merge_intervals([(0, 10), (2, 3)]), [(0, 10)])
        self.assertEqual(merge_intervals([(5, 6), (1, 2), (3, 4)]), [(1, 2), (3, 4), (5, 6)])
        self.assertEqual(merge_intervals([(1, 2), (3, 4), (2, 3)]), [(1, 4)])

    def test_merge_intervals_does_not_mutate_input(self):
        original = [(0, 1), (1, 2)]
        copy = list(original)
        merge_intervals(original)
        self.assertEqual(original, copy)

    def test_merge_returns_tuples(self):
        result = merge_intervals([(0, 1)])
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], tuple)


if __name__ == "__main__":
    unittest.main(verbosity=2)
