"""
Numeric and currency formatting utilities for MPLADS FundGuard.
Handles Indian numbering systems, currency, percentages, and missing data safely.
"""

import math
from typing import Optional, Union

Number = Union[int, float]


def is_valid_number(val: Optional[Number]) -> bool:
    """Checks whether a value is a finite, non-null number."""
    if val is None:
        return False
    if isinstance(val, (int, float)):
        return not (math.isnan(val) or math.isinf(val))
    return False


def format_indian_number(num_str: str) -> str:
    """Formats a non-negative integer string in the Indian numbering system (e.g., 12,34,567)."""
    if len(num_str) <= 3:
        return num_str
    last_three = num_str[-3:]
    remaining = num_str[:-3]
    chunks = []
    while len(remaining) > 2:
        chunks.append(remaining[-2:])
        remaining = remaining[:-2]
    if remaining:
        chunks.append(remaining)
    chunks.reverse()
    return ",".join(chunks) + "," + last_three


def inr(val: Optional[Number], decimals: int = 0) -> str:
    """
    Formats a value into Indian Rupees with ₹ symbol and Indian comma notation.
    Example: 1234567 -> ₹12,34,567; None -> —
    """
    if not is_valid_number(val):
        return "—"

    assert val is not None
    sign = "-" if val < 0 else ""
    abs_val = abs(val)

    if decimals > 0:
        rounded_val = round(abs_val, decimals)
        parts = f"{rounded_val:.{decimals}f}".split(".")
        int_part = format_indian_number(parts[0])
        dec_part = parts[1]
        return f"{sign}₹{int_part}.{dec_part}"
    else:
        int_val = int(round(abs_val))
        int_part = format_indian_number(str(int_val))
        return f"{sign}₹{int_part}"


def lakh_crore(val: Optional[Number]) -> str:
    """
    Formats large currency amounts into Crores (Cr) or Lakhs (L).
    Example: 54200000 -> ₹5.42 Cr; 1250000 -> ₹12.50 L; 50000 -> ₹50,000; None -> —
    """
    if not is_valid_number(val):
        return "—"

    assert val is not None
    if val == 0:
        return "₹0"

    sign = "-" if val < 0 else ""
    abs_val = abs(val)

    if abs_val >= 1e7:
        cr = abs_val / 1e7
        return f"{sign}₹{cr:.2f} Cr"
    elif abs_val >= 1e5:
        lakh = abs_val / 1e5
        return f"{sign}₹{lakh:.2f} L"
    else:
        return inr(val, decimals=0)


def pct(val: Optional[Number], decimals: int = 1, is_ratio: bool = False) -> str:
    """
    Formats a percentage.
    If is_ratio is True, multiplies by 100 first (e.g. 0.845 -> 84.5%).
    Example: 84.52 -> 84.5%; None -> —
    """
    if not is_valid_number(val):
        return "—"

    assert val is not None
    actual_val = val * 100.0 if is_ratio else val
    return f"{actual_val:.{decimals}f}%"


def compact(val: Optional[Number]) -> str:
    """
    Formats counts in compact notation (K, M, B) or standard integer with commas.
    Example: 86527 -> 86.5K; 1250000 -> 1.3M; None -> —
    """
    if not is_valid_number(val):
        return "—"

    assert val is not None
    sign = "-" if val < 0 else ""
    abs_val = abs(val)

    if abs_val >= 1e9:
        return f"{sign}{abs_val / 1e9:.1f}B"
    elif abs_val >= 1e6:
        return f"{sign}{abs_val / 1e6:.1f}M"
    elif abs_val >= 1e3:
        return f"{sign}{abs_val / 1e3:.1f}K"
    else:
        if isinstance(val, int) or val.is_integer():
            return f"{int(val):,}"
        return f"{val:g}"
