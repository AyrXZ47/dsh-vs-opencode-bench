"""Ledger reference implementation (not shipped to agents)."""

import re


def sum_by_category(entries, category):
    return {
        entry["id"]: entry["amount_cents"]
        for entry in entries
        if entry["category"] == category
    }


_AMOUNT_RE = re.compile(r"^([+-]?)(\d+)(?:\.(\d{1,2}))?$")


def parse_amount(text):
    if not isinstance(text, str):
        raise ValueError("amount must be a string")
    match = _AMOUNT_RE.fullmatch(text.strip())
    if not match:
        raise ValueError("invalid amount")
    sign, whole, fraction = match.groups()
    cents = int(whole) * 100
    if fraction:
        cents += int(fraction.ljust(2, "0"))
    return -cents if sign == "-" else cents


def apply_discount(amount_cents, percent):
    if not isinstance(amount_cents, int) or isinstance(amount_cents, bool):
        raise ValueError("amount_cents must be an integer")
    if not isinstance(percent, int) or isinstance(percent, bool):
        raise ValueError("percent must be an integer")
    if amount_cents < 0:
        raise ValueError("amount_cents must be >= 0")
    if not 0 <= percent <= 100:
        raise ValueError("percent out of range")
    return (amount_cents * (100 - percent) + 50) // 100


def merge_intervals(intervals):
    if not intervals:
        return []
    ordered = sorted(tuple(item) for item in intervals)
    merged = [list(ordered[0])]
    for start, end in ordered[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [tuple(item) for item in merged]
