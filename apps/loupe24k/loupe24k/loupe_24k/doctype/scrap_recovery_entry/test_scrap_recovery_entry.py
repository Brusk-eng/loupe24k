"""
Unit tests for Scrap Recovery Entry controller.

Rules under test:
  - total_gross_wt = sum of scrap_items.gross_wt
  - total_est_fine_wt = sum of scrap_items.fine_wt
  - fine_recovered = total_est_fine_wt × recovery_pct / 100 (rounded to 3 dp)
  - None recovery_pct defaults to 100
"""
import unittest
from types import SimpleNamespace

from loupe24k.loupe_24k.doctype.scrap_recovery_entry.scrap_recovery_entry import (
    ScrapRecoveryEntry,
)


def _doc(**kwargs):
    d = ScrapRecoveryEntry.__new__(ScrapRecoveryEntry)
    defaults = {"scrap_items": [], "recovery_pct": 100}
    defaults.update(kwargs)
    d.__dict__.update(defaults)
    return d


def _scrap_row(gross_wt, fine_wt):
    return SimpleNamespace(gross_wt=gross_wt, fine_wt=fine_wt)


class TestScrapTotals(unittest.TestCase):
    def test_empty_items(self):
        doc = _doc()
        doc.validate()
        self.assertEqual(doc.total_gross_wt, 0)
        self.assertEqual(doc.total_est_fine_wt, 0)
        self.assertEqual(doc.fine_recovered, 0)

    def test_single_scrap_item(self):
        # Sprue/button 22K: 17.40 g gross, 17.40 × 0.9167 = 15.950 g fine
        doc = _doc(scrap_items=[_scrap_row(17.40, round(17.40 * 0.9167, 3))])
        doc.validate()
        self.assertAlmostEqual(doc.total_gross_wt, 17.40)
        self.assertAlmostEqual(doc.total_est_fine_wt, round(17.40 * 0.9167, 3))

    def test_multiple_scrap_items(self):
        # Filing scrap 3.50 g + polishing dust 1.10 g, both 22K
        items = [
            _scrap_row(3.50, round(3.50 * 0.9167, 3)),
            _scrap_row(1.10, round(1.10 * 0.9167, 3)),
        ]
        doc = _doc(scrap_items=items)
        doc.validate()
        self.assertAlmostEqual(doc.total_gross_wt, 4.60, places=3)

    def test_none_values_treated_as_zero(self):
        doc = _doc(scrap_items=[_scrap_row(None, None), _scrap_row(5.0, 4.584)])
        doc.validate()
        self.assertAlmostEqual(doc.total_gross_wt, 5.0)
        self.assertAlmostEqual(doc.total_est_fine_wt, 4.584)


class TestFineRecovered(unittest.TestCase):
    def test_full_recovery_at_100_pct(self):
        doc = _doc(scrap_items=[_scrap_row(17.40, 15.950)], recovery_pct=100)
        doc.validate()
        self.assertAlmostEqual(doc.fine_recovered, 15.950, places=3)

    def test_refinery_at_88_pct(self):
        # Spec: polishing dust goes to refiner at 88% recovery
        doc = _doc(scrap_items=[_scrap_row(1.10, round(1.10 * 0.9167, 3))], recovery_pct=88)
        doc.validate()
        expected = round(round(1.10 * 0.9167, 3) * 0.88, 3)
        self.assertAlmostEqual(doc.fine_recovered, expected, places=3)

    def test_partial_recovery(self):
        doc = _doc(scrap_items=[_scrap_row(10.0, 9.167)], recovery_pct=95)
        doc.validate()
        self.assertAlmostEqual(doc.fine_recovered, round(9.167 * 0.95, 3), places=3)

    def test_none_recovery_pct_defaults_to_100(self):
        doc = _doc(scrap_items=[_scrap_row(10.0, 9.167)], recovery_pct=None)
        doc.validate()
        self.assertAlmostEqual(doc.fine_recovered, round(9.167 * 1.0, 3), places=3)

    def test_rounding_to_three_decimal_places(self):
        # 9.001 g fine × 88% = 7.92088 → rounds to 7.921
        doc = _doc(scrap_items=[_scrap_row(10.0, 9.001)], recovery_pct=88)
        doc.validate()
        self.assertEqual(doc.fine_recovered, round(9.001 * 0.88, 3))

    def test_fine_recovered_never_exceeds_est_fine_wt(self):
        doc = _doc(scrap_items=[_scrap_row(20.0, 18.334)], recovery_pct=100)
        doc.validate()
        self.assertLessEqual(doc.fine_recovered, doc.total_est_fine_wt)


class TestVoucherLinkFields(unittest.TestCase):
    def test_voucher_fields_can_be_set_without_affecting_recovery_math(self):
        doc = _doc(
            voucher_type="Job Card",
            voucher_no="JC-0001",
            scrap_items=[_scrap_row(10.0, 9.167)],
            recovery_pct=95,
        )
        doc.validate()
        self.assertEqual(doc.voucher_type, "Job Card")
        self.assertEqual(doc.voucher_no, "JC-0001")
        self.assertAlmostEqual(doc.fine_recovered, round(9.167 * 0.95, 3), places=3)
