"""
report_pricing.py
=================
Dynamic report pricing engine for Edustat.

Weight tables are derived from the official pricing specification.
Total weight = product of all individual filter weights.
Final price is looked up from the total-weight → price table.
"""

from __future__ import annotations
from typing import Any


# ──────────────────────────────────────────────
# 1.  INDIVIDUAL FILTER WEIGHT TABLES
# ──────────────────────────────────────────────

def _lookup(value: int, table: list[tuple]) -> int:
    """
    table is a list of (upper_bound_inclusive, weight) pairs sorted ascending.
    The last entry's upper_bound should be float('inf') to catch everything above.
    """
    for upper, weight in table:
        if value <= upper:
            return weight
    return table[-1][1]   # fallback: return max weight


# ExamYear weight table
_YEAR_TABLE: list[tuple[int, int]] = [
    (1,   1),
    (2,   2),
    (3,   3),
    (4,   4),
    (5,   5),
    (7,   6),   # 6-7
    (10,  9),   # 8-10
    (13, 12),   # 11-13
    (16, 15),   # 14-16
    (19, 18),   # 17-19
    (int(1e9), 20),  # >= 20
]

# State weight table
_STATE_TABLE: list[tuple[int, int]] = [
    (1,   2),
    (2,   4),
    (3,   6),
    (4,   8),
    (5,  10),
    (10, 12),   # 6-10
    (17, 14),   # 11-17
    (24, 16),   # 18-24
    (29, 18),   # 25-29
    (int(1e9), 20),  # 30-38 and above
]

# Subject / Special Need / School weight table  (shared shape)
_SUBJECT_TABLE: list[tuple[int, int]] = [
    (1,  1),
    (2,  2),
    (3,  3),
    (4,  4),
    (5,  5),
    (10, 6),    # 6-10
    (17, 7),    # 11-17
    (24, 8),    # 18-24
    (29, 9),    # 25-29
    (int(1e9), 10),  # 30-38 and above
]

# LGA weight table  (identical shape to Subject table)
_LGA_TABLE = _SUBJECT_TABLE


# ──────────────────────────────────────────────
# 2.  TOTAL-WEIGHT → PRICE TABLE  (₦)
# ──────────────────────────────────────────────

_PRICE_TABLE: list[tuple[int, int]] = [
    (4,    15_000),
    (5,    20_000),
    (10,   25_000),    # 6-10
    (17,   35_000),    # 11-17
    (23,   45_000),    # 18-23
    (35,   60_000),    # 24-35
    (50,   80_000),    # 36-50
    (65,  100_000),    # 51-65
    (80,  120_000),    # 66-80
    (100, 150_000),    # 81-100
    (150, 200_000),    # 101-150
    (250, 300_000),    # 151-250
    (500, 400_000),    # 251-500
    (1000, 500_000),   # 501-1000
    (1500, 600_000),   # 1001-1500
    (2000, 700_000),   # 1501-2000
    (3000, 800_000),   # 2001-3000
    (4000, 900_000),   # 3001-4000
    (5000, 1_000_000), # 4001-5000
    (int(1e9), 1_200_000),  # 5001-6000 and above
]


# ──────────────────────────────────────────────
# 3.  PUBLIC API
# ──────────────────────────────────────────────

def get_filter_weight(filter_name: str, selected_count: int) -> int:
    """
    Return the weight for a single filter dimension based on how many
    options the user selected.

    Filters not listed here contribute a weight of 1 (neutral multiplier).
    
    Parameters
    ----------
    filter_name    : canonical filter key, e.g. "ExamYear", "State"
    selected_count : number of values selected by the user (0 is treated as 1)
    """
    n = max(selected_count, 1)   # 0 selections → treat as 1

    weight_map = {
        "ExamYear":    _YEAR_TABLE,
        "State":       _STATE_TABLE,
        "Origin":      _STATE_TABLE,   # same shape as State
        "Subject":     _SUBJECT_TABLE,
        "Disability":  _SUBJECT_TABLE, # "Special Need" in spec
        "Sponsor":     _SUBJECT_TABLE, # "School" in spec
        "centre":      _LGA_TABLE,     # centre ≈ LGA granularity
        "AgeGroup":    _SUBJECT_TABLE,
        "ExamType":    _SUBJECT_TABLE,
        "Grade":       _SUBJECT_TABLE,
        "Status":      _SUBJECT_TABLE,
        "Sex":         _SUBJECT_TABLE,
    }

    table = weight_map.get(filter_name)
    if table is None:
        return 1   # unknown filter → neutral

    return _lookup(n, table)


def calculate_report_price(filter_values: dict[str, Any]) -> dict:
    """
    Given the dict of selected filter values (as stored in configure_filters.py),
    compute:
      - individual filter weights
      - total weight (product of all weights)
      - price in ₦

    Parameters
    ----------
    filter_values : dict mapping filter_name → list of selected values
                    e.g. {"ExamYear": [2020, 2021], "State": ["Lagos"], ...}
                    Entries that are empty, None, or ["All"] are ignored.

    Returns
    -------
    dict with keys:
        filter_weights   : {filter_name: weight}
        total_weight     : int
        price            : int  (₦)
        price_formatted  : str  (e.g. "₦45,000")
        breakdown        : human-readable list of strings
    """
    # ── normalise: skip "All" / empty selections ──────────────────────────────
    active_filters: dict[str, int] = {}   # filter_name → count of selected values

    for fname, fval in filter_values.items():
        if not fval:
            continue
        if isinstance(fval, list):
            if fval == ["All"] or len(fval) == 0:
                continue
            active_filters[fname] = len(fval)
        else:
            # scalar value
            active_filters[fname] = 1

    if not active_filters:
        # No meaningful filters selected → minimum price
        return {
            "filter_weights": {},
            "total_weight": 4,
            "price": 15_000,
            "price_formatted": "₦15,000",
            "breakdown": ["No filters selected — minimum price applied"],
        }

    # ── compute individual weights ────────────────────────────────────────────
    filter_weights: dict[str, int] = {}
    for fname, count in active_filters.items():
        filter_weights[fname] = get_filter_weight(fname, count)

    # ── total weight = PRODUCT of all weights ─────────────────────────────────
    total_weight = 1
    for w in filter_weights.values():
        total_weight *= w

    # ── look up price ─────────────────────────────────────────────────────────
    price = _lookup(total_weight, _PRICE_TABLE)

    # ── build human-readable breakdown ────────────────────────────────────────
    breakdown = []
    for fname, count in active_filters.items():
        w = filter_weights[fname]
        breakdown.append(
            f"{fname}: {count} selection{'s' if count != 1 else ''} → weight {w}"
        )
    breakdown.append(
        f"Total weight = {' × '.join(str(w) for w in filter_weights.values())} = {total_weight}"
    )
    breakdown.append(f"Price = ₦{price:,}")

    return {
        "filter_weights":  filter_weights,
        "total_weight":    total_weight,
        "price":           price,
        "price_formatted": f"₦{price:,}",
        "breakdown":       breakdown,
    }


def format_price_breakdown_html(pricing: dict) -> str:
    """
    Returns a compact HTML string suitable for st.markdown(..., unsafe_allow_html=True).
    """
    rows = "".join(
        f"<tr><td style='padding:4px 12px 4px 0;color:#6b7280;font-size:0.87rem'>{line.split('→')[0].strip()}</td>"
        f"<td style='padding:4px 0;font-weight:600;font-size:0.87rem'>{'→' + line.split('→')[1] if '→' in line else line}</td></tr>"
        for line in pricing["breakdown"][:-2]   # individual filter lines
    )
    return f"""
<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:1rem 1.2rem;margin-top:1rem;">
    <div style="font-family:'DM Sans',sans-serif;">
        <div style="font-size:0.78rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;
                    color:#2563eb;margin-bottom:0.6rem;">💰 Pricing Breakdown</div>
        <table style="border-collapse:collapse;width:100%">{rows}</table>
        <div style="border-top:1px solid #e2e8f0;margin-top:0.6rem;padding-top:0.6rem;
                    font-size:0.88rem;color:#374151;">
            <strong>Total weight:</strong> {pricing['total_weight']}
        </div>
        <div style="font-family:'Playfair Display',serif;font-size:1.5rem;font-weight:700;
                    color:#0f172a;margin-top:0.4rem;">
            {pricing['price_formatted']}
        </div>
    </div>
</div>
"""