"""
Unit tests for Metal Rate controller.

Rules under test:
  - Touch factor is set from the karat
  - When derived_from_24k=True and karat != 24K, rate is pulled from the 24K
    record for the same date and multiplied by touch
  - 24K records are never auto-derived even if the flag is set
  - When no 24K record exists the rate is left unchanged
"""
import unittest
from unittest.mock import patch

from loupe24k.loupe_24k.doctype.metal_rate.metal_rate import (
    TOUCH_FACTORS,
    MetalRate,
)


def _doc(**kwargs):
    d = MetalRate.__new__(MetalRate)
    d.__dict__.update(kwargs)
    return d


class TestTouchFactorAssignment(unittest.TestCase):
    def test_24k_touch(self):
        doc = _doc(karat="24K", gross_wt=0, derived_from_24k=False, date="2026-08-08", rate_per_g=6200)
        doc.validate()
        self.assertEqual(doc.touch, 1.0)

    def test_22k_touch(self):
        doc = _doc(karat="22K", derived_from_24k=False, date="2026-08-08", rate_per_g=5683)
        doc.validate()
        self.assertAlmostEqual(doc.touch, 0.9167, places=4)

    def test_18k_touch(self):
        doc = _doc(karat="18K", derived_from_24k=False, date="2026-08-08", rate_per_g=4650)
        doc.validate()
        self.assertEqual(doc.touch, 0.75)


class TestRateDerivation(unittest.TestCase):
    def test_22k_derived_from_24k(self):
        doc = _doc(karat="22K", derived_from_24k=True, date="2026-08-08", rate_per_g=0)
        with patch("loupe24k.loupe_24k.doctype.metal_rate.metal_rate.frappe.db.get_value",
                   return_value=6200) as mock_get:
            doc.validate()
            mock_get.assert_called_once_with(
                "Metal Rate", {"date": "2026-08-08", "karat": "24K"}, "rate_per_g"
            )
        # 6200 × 0.9167 = 5683.54
        self.assertAlmostEqual(doc.rate_per_g, round(6200 * 0.9167, 2), places=2)

    def test_18k_derived_from_24k(self):
        doc = _doc(karat="18K", derived_from_24k=True, date="2026-08-08", rate_per_g=0)
        with patch("loupe24k.loupe_24k.doctype.metal_rate.metal_rate.frappe.db.get_value",
                   return_value=6200):
            doc.validate()
        self.assertAlmostEqual(doc.rate_per_g, round(6200 * 0.75, 2), places=2)

    def test_24k_never_derived_even_if_flag_set(self):
        original_rate = 6200
        doc = _doc(karat="24K", derived_from_24k=True, date="2026-08-08", rate_per_g=original_rate)
        with patch("loupe24k.loupe_24k.doctype.metal_rate.metal_rate.frappe.db.get_value") as mock_get:
            doc.validate()
            mock_get.assert_not_called()
        self.assertEqual(doc.rate_per_g, original_rate)

    def test_flag_off_rate_unchanged(self):
        doc = _doc(karat="22K", derived_from_24k=False, date="2026-08-08", rate_per_g=5500)
        with patch("loupe24k.loupe_24k.doctype.metal_rate.metal_rate.frappe.db.get_value") as mock_get:
            doc.validate()
            mock_get.assert_not_called()
        self.assertEqual(doc.rate_per_g, 5500)

    def test_no_24k_record_leaves_rate_unchanged(self):
        original_rate = 5500
        doc = _doc(karat="22K", derived_from_24k=True, date="2026-08-08", rate_per_g=original_rate)
        with patch("loupe24k.loupe_24k.doctype.metal_rate.metal_rate.frappe.db.get_value",
                   return_value=None):
            doc.validate()
        self.assertEqual(doc.rate_per_g, original_rate)

    def test_derived_rate_rounded_to_two_dp(self):
        # 6201 × 0.9167 = 5684.4567 → should be 5684.46
        doc = _doc(karat="22K", derived_from_24k=True, date="2026-08-08", rate_per_g=0)
        with patch("loupe24k.loupe_24k.doctype.metal_rate.metal_rate.frappe.db.get_value",
                   return_value=6201):
            doc.validate()
        self.assertEqual(doc.rate_per_g, round(6201 * 0.9167, 2))
