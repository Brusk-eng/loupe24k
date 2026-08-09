"""
Unit tests for Fine Gold Ledger Entry controller.

Tests the core fine-gold calculation:
    fine_wt = gross_wt × touch (rounded to 3 dp)
"""
import unittest

from loupe24k.loupe_24k.doctype.fine_gold_ledger_entry.fine_gold_ledger_entry import (
    TOUCH_FACTORS,
    FineGoldLedgerEntry,
)


def _doc(**kwargs):
    """Instantiate FineGoldLedgerEntry without triggering Frappe's Document.__init__."""
    d = FineGoldLedgerEntry.__new__(FineGoldLedgerEntry)
    d.__dict__.update(kwargs)
    return d


class TestTouchFactors(unittest.TestCase):
    def test_touch_constants(self):
        self.assertEqual(TOUCH_FACTORS["24K"], 1.0000)
        self.assertAlmostEqual(TOUCH_FACTORS["22K"], 0.9167, places=4)
        self.assertEqual(TOUCH_FACTORS["18K"], 0.7500)

    def test_unknown_karat_defaults_to_one(self):
        doc = _doc(karat="21K", gross_wt=10.0)
        doc.validate()
        self.assertEqual(doc.touch, 1.0)


class TestFineWeightCalculation(unittest.TestCase):
    def test_24k_full_touch(self):
        doc = _doc(karat="24K", gross_wt=55.0)
        doc.validate()
        self.assertEqual(doc.touch, 1.0)
        self.assertEqual(doc.fine_wt, 55.0)

    def test_22k_touch(self):
        # Spec scenario A: 59.70 g grain × 0.9167 = 54.727 g fine → rounds to 54.727
        doc = _doc(karat="22K", gross_wt=59.70)
        doc.validate()
        self.assertAlmostEqual(doc.touch, 0.9167, places=4)
        self.assertAlmostEqual(doc.fine_wt, 54.727, places=3)

    def test_18k_touch(self):
        doc = _doc(karat="18K", gross_wt=40.0)
        doc.validate()
        self.assertEqual(doc.touch, 0.75)
        self.assertEqual(doc.fine_wt, 30.0)

    def test_rounding_to_three_decimal_places(self):
        # 10.001 g × 0.9167 = 9.1680167 → rounds to 9.168
        doc = _doc(karat="22K", gross_wt=10.001)
        doc.validate()
        self.assertEqual(doc.fine_wt, round(10.001 * 0.9167, 3))

    def test_none_gross_wt_treated_as_zero(self):
        doc = _doc(karat="22K", gross_wt=None)
        doc.validate()
        self.assertEqual(doc.fine_wt, 0.0)

    def test_zero_gross_wt(self):
        doc = _doc(karat="24K", gross_wt=0)
        doc.validate()
        self.assertEqual(doc.fine_wt, 0.0)

    def test_fine_wt_never_exceeds_gross_wt(self):
        for karat in ("24K", "22K", "18K"):
            with self.subTest(karat=karat):
                doc = _doc(karat=karat, gross_wt=100.0)
                doc.validate()
                self.assertLessEqual(doc.fine_wt, doc.gross_wt)

    def test_validate_sets_both_touch_and_fine_wt(self):
        doc = _doc(karat="22K", gross_wt=38.5)
        doc.validate()
        self.assertTrue(hasattr(doc, "touch"))
        self.assertTrue(hasattr(doc, "fine_wt"))
        # touch and fine_wt must be consistent
        self.assertAlmostEqual(doc.fine_wt, round(doc.gross_wt * doc.touch, 3), places=3)


class TestDemoScenarioWeights(unittest.TestCase):
    """Verify the spec's exact demo numbers from section 3.1 pass through correctly."""

    def test_scenario_a_alloying_output(self):
        # 59.70 g of 22K grain → 54.727 g fine gold
        doc = _doc(karat="22K", gross_wt=59.70)
        doc.validate()
        self.assertAlmostEqual(doc.fine_wt, 54.727, places=3)

    def test_scenario_d_finished_rings(self):
        # 37.00 g finished rings 22K → 33.918 g fine
        doc = _doc(karat="22K", gross_wt=37.0)
        doc.validate()
        self.assertAlmostEqual(doc.fine_wt, round(37.0 * 0.9167, 3), places=3)

    def test_24k_contrast_ring(self):
        # 24K plain band: fine_wt == gross_wt
        doc = _doc(karat="24K", gross_wt=8.5)
        doc.validate()
        self.assertEqual(doc.fine_wt, 8.5)
