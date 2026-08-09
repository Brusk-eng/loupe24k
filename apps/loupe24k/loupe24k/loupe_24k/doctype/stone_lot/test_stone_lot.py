"""
Unit tests for Stone Lot controller.

Rules under test:
  - total_value = rate_per_ct × total_carat, rounded to 2 dp
  - If either rate_per_ct or total_carat is falsy, total_value is not calculated
"""
import unittest

from loupe24k.loupe_24k.doctype.stone_lot.stone_lot import StoneLot


def _doc(**kwargs):
    d = StoneLot.__new__(StoneLot)
    d.__dict__.update(kwargs)
    return d


class TestTotalValueCalculation(unittest.TestCase):
    def test_standard_calculation(self):
        # 0.75 ct melee parcel at ₹15,000/ct = ₹11,250.00
        doc = _doc(rate_per_ct=15000, total_carat=0.75)
        doc.validate()
        self.assertEqual(doc.total_value, 11250.00)

    def test_solitaire_calculation(self):
        # 0.30 ct solitaire at ₹80,000/ct = ₹24,000.00
        doc = _doc(rate_per_ct=80000, total_carat=0.30)
        doc.validate()
        self.assertEqual(doc.total_value, 24000.00)

    def test_rounding_to_two_decimal_places(self):
        # 0.333 ct × ₹10,001/ct = ₹3,330.333 → ₹3,330.33
        doc = _doc(rate_per_ct=10001, total_carat=0.333)
        doc.validate()
        self.assertEqual(doc.total_value, round(10001 * 0.333, 2))

    def test_no_rate_skips_calculation(self):
        doc = _doc(rate_per_ct=None, total_carat=0.75, total_value=999)
        doc.validate()
        self.assertEqual(doc.total_value, 999)  # unchanged

    def test_zero_rate_skips_calculation(self):
        doc = _doc(rate_per_ct=0, total_carat=0.75, total_value=999)
        doc.validate()
        self.assertEqual(doc.total_value, 999)

    def test_no_carat_skips_calculation(self):
        doc = _doc(rate_per_ct=15000, total_carat=None, total_value=999)
        doc.validate()
        self.assertEqual(doc.total_value, 999)

    def test_zero_carat_skips_calculation(self):
        doc = _doc(rate_per_ct=15000, total_carat=0, total_value=999)
        doc.validate()
        self.assertEqual(doc.total_value, 999)

    def test_fractional_result(self):
        doc = _doc(rate_per_ct=100, total_carat=0.333)
        doc.validate()
        self.assertEqual(doc.total_value, 33.30)
