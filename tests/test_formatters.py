import math
import pytest
from frontend.components.formatters import inr, lakh_crore, pct, compact


def test_inr_formatting():
    assert inr(1234567) == "₹12,34,567"
    assert inr(500) == "₹500"
    assert inr(100000) == "₹1,00,000"
    assert inr(10000000) == "₹1,00,00,000"
    assert inr(0) == "₹0"
    assert inr(-1234567) == "-₹12,34,567"
    assert inr(1234567.89, decimals=2) == "₹12,34,567.89"
    assert inr(None) == "—"
    assert inr(float("nan")) == "—"
    assert inr(float("inf")) == "—"


def test_lakh_crore_formatting():
    assert lakh_crore(54200000) == "₹5.42 Cr"
    assert lakh_crore(1250000) == "₹12.50 L"
    assert lakh_crore(50000) == "₹50,000"
    assert lakh_crore(0) == "₹0"
    assert lakh_crore(-54200000) == "-₹5.42 Cr"
    assert lakh_crore(None) == "—"
    assert lakh_crore(float("nan")) == "—"


def test_pct_formatting():
    assert pct(84.52) == "84.5%"
    assert pct(84.52, decimals=2) == "84.52%"
    assert pct(0.8452, decimals=1, is_ratio=True) == "84.5%"
    assert pct(0.0) == "0.0%"
    assert pct(None) == "—"
    assert pct(float("nan")) == "—"


def test_compact_formatting():
    assert compact(86527) == "86.5K"
    assert compact(1250000) == "1.2M"
    assert compact(2500000000) == "2.5B"
    assert compact(543) == "543"
    assert compact(0) == "0"
    assert compact(None) == "—"
    assert compact(float("nan")) == "—"
