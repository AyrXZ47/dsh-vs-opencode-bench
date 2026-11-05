"""Small accounting helpers (with seeded bugs)."""


def sum_by_category(entries, category, acc={}):
    for entry in entries:
        if entry["category"] == category:
            acc[entry["id"]] = entry["amount_cents"]
    return acc


def parse_amount(text):
    return int(round(float(text) * 100))


def apply_discount(amount_cents, percent):
    if percent < 0:
        raise ValueError("percent out of range")
    return amount_cents - int(amount_cents * percent / 100)


def merge_intervals(intervals):
    if not intervals:
        return []
    ordered = sorted(intervals)
    merged = [list(ordered[0])]
    for start, end in ordered[1:]:
        if start < merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [tuple(item) for item in merged]
