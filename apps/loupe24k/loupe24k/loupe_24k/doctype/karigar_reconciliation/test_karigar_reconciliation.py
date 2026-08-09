"""
Unit tests for Karigar Reconciliation controller.

This is the most business-critical DocType — it enforces the wastage allowance
and stone breakage allowance, and sets the Pass / Warning / Fail verdict.

Rules under test:
  - returned_fine_wt = sum of returned_items.fine_wt
  - fine_loss = issued_fine_wt - returned_fine_wt
  - allowed_fine_loss = issued_fine_wt × wastage_allowance_pct / 100
  - excess_fine_loss = max(0, fine_loss - allowed_fine_loss)  [never negative]
  - excess_broken = max(0, stones_broken - allowed_broken)   [never negative]
  - verdict = "Pass"    when no excess
  - verdict = "Warning" when 0 < excess_fine_loss <= 0.1 (or excess_broken with no metal excess)
  - verdict = "Fail"    when excess_fine_loss > 0.1
"""
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from loupe24k.loupe_24k.doctype.karigar_reconciliation.karigar_reconciliation import (
    KarigarReconciliation,
)


def _doc(**kwargs):
    d = KarigarReconciliation.__new__(KarigarReconciliation)
    defaults = {
        "issue_ref": None,
        "issued_gross_wt": 0,
        "issued_fine_wt": 0,
        "issued_stone_pieces": 0,
        "issued_stone_carat": 0,
        "returned_items": [],
        "wastage_allowance_pct": 2.0,
        "stone_breakage_allowance_pct": 5.0,
        "stones_set": 0,
        "stones_returned": 0,
        "stones_broken": 0,
        "excess_fine_loss": 0,
        "excess_broken": 0,
    }
    defaults.update(kwargs)
    d.__dict__.update(defaults)
    return d


def _returned_row(fine_wt):
    return SimpleNamespace(fine_wt=fine_wt)


class TestMetalReconciliation(unittest.TestCase):
    def test_returned_fine_wt_sums_rows(self):
        doc = _doc(
            issued_fine_wt=54.727,
            returned_items=[_returned_row(33.918), _returned_row(18.334)],
        )
        doc._calc_metal_reconciliation()
        self.assertAlmostEqual(doc.returned_fine_wt, 52.252, places=3)

    def test_fine_loss_calculation(self):
        doc = _doc(issued_fine_wt=54.727, returned_items=[_returned_row(53.400)])
        doc._calc_metal_reconciliation()
        self.assertAlmostEqual(doc.fine_loss, 1.327, places=3)

    def test_allowed_fine_loss_at_two_percent(self):
        # 54.727 g issued × 2% = 1.095 g allowed
        doc = _doc(issued_fine_wt=54.727, wastage_allowance_pct=2.0,
                   returned_items=[_returned_row(54.727)])
        doc._calc_metal_reconciliation()
        self.assertAlmostEqual(doc.allowed_fine_loss, round(54.727 * 0.02, 3), places=3)

    def test_excess_fine_loss_is_max_zero(self):
        # Return exactly what was issued → no excess
        doc = _doc(issued_fine_wt=50.0, wastage_allowance_pct=2.0,
                   returned_items=[_returned_row(50.0)])
        doc._calc_metal_reconciliation()
        self.assertEqual(doc.excess_fine_loss, 0)

    def test_excess_fine_loss_never_negative(self):
        # Return more than issued (over-recovery) → excess must be 0 not negative
        doc = _doc(issued_fine_wt=50.0, wastage_allowance_pct=2.0,
                   returned_items=[_returned_row(51.0)])
        doc._calc_metal_reconciliation()
        self.assertGreaterEqual(doc.excess_fine_loss, 0)

    def test_excess_when_loss_exceeds_allowance(self):
        # Issued 54.727 g, returned 53.000 g → loss 1.727 g, allowed 1.095 g, excess 0.632 g
        doc = _doc(
            issued_fine_wt=54.727,
            wastage_allowance_pct=2.0,
            returned_items=[_returned_row(53.000)],
        )
        doc._calc_metal_reconciliation()
        expected_loss = round(54.727 - 53.000, 3)
        expected_allowed = round(54.727 * 0.02, 3)
        expected_excess = round(expected_loss - expected_allowed, 3)
        self.assertAlmostEqual(doc.excess_fine_loss, expected_excess, places=3)

    def test_empty_returned_items(self):
        doc = _doc(issued_fine_wt=54.727, wastage_allowance_pct=2.0, returned_items=[])
        doc._calc_metal_reconciliation()
        self.assertEqual(doc.returned_fine_wt, 0)
        self.assertAlmostEqual(doc.fine_loss, 54.727, places=3)


class TestStoneReconciliation(unittest.TestCase):
    def test_no_excess_within_allowance(self):
        # 30 pieces issued, 5% allowance = 1 allowed broken, 1 actually broken → no excess
        doc = _doc(issued_stone_pieces=30, stone_breakage_allowance_pct=5.0, stones_broken=1)
        doc._calc_stone_reconciliation()
        self.assertEqual(doc.excess_broken, 0)

    def test_excess_broken_above_allowance(self):
        # 30 pieces, 5% = 1 allowed, 3 broken → excess 2
        doc = _doc(issued_stone_pieces=30, stone_breakage_allowance_pct=5.0, stones_broken=3)
        doc._calc_stone_reconciliation()
        self.assertEqual(doc.excess_broken, 2)

    def test_excess_broken_never_negative(self):
        # 0 broken, allowance is 1 → should be 0 not -1
        doc = _doc(issued_stone_pieces=30, stone_breakage_allowance_pct=5.0, stones_broken=0)
        doc._calc_stone_reconciliation()
        self.assertGreaterEqual(doc.excess_broken, 0)

    def test_allowed_broken_truncates_to_int(self):
        # 7 pieces × 5% = 0.35 → int(0.35) = 0 allowed; 1 broken → excess 1
        doc = _doc(issued_stone_pieces=7, stone_breakage_allowance_pct=5.0, stones_broken=1)
        doc._calc_stone_reconciliation()
        self.assertEqual(doc.excess_broken, 1)

    def test_zero_stone_issues(self):
        doc = _doc(issued_stone_pieces=0, stone_breakage_allowance_pct=5.0, stones_broken=0)
        doc._calc_stone_reconciliation()
        self.assertEqual(doc.excess_broken, 0)


class TestVerdict(unittest.TestCase):
    def test_pass_when_no_excess(self):
        doc = _doc(excess_fine_loss=0, excess_broken=0)
        doc._set_verdict()
        self.assertEqual(doc.verdict, "Pass")

    def test_warning_when_small_metal_excess(self):
        # 0 < excess_fine_loss <= 0.1 → Warning
        doc = _doc(excess_fine_loss=0.05, excess_broken=0)
        doc._set_verdict()
        self.assertEqual(doc.verdict, "Warning")

    def test_warning_at_boundary_0_1(self):
        doc = _doc(excess_fine_loss=0.1, excess_broken=0)
        doc._set_verdict()
        self.assertEqual(doc.verdict, "Warning")

    def test_fail_when_excess_metal_large(self):
        doc = _doc(excess_fine_loss=0.101, excess_broken=0)
        doc._set_verdict()
        self.assertEqual(doc.verdict, "Fail")

    def test_warning_when_only_stone_excess(self):
        # excess_broken but no metal issue → Warning (fine_loss <= 0.1)
        doc = _doc(excess_fine_loss=0, excess_broken=2)
        doc._set_verdict()
        self.assertEqual(doc.verdict, "Warning")

    def test_fail_when_both_excesses(self):
        doc = _doc(excess_fine_loss=0.5, excess_broken=2)
        doc._set_verdict()
        self.assertEqual(doc.verdict, "Fail")


class TestDemoScenario(unittest.TestCase):
    """
    End-to-end reconciliation using the spec's demo numbers.

    Scenario C/D: Ramesh issues 42.00 g blanks (22K), returns 37.00 g finished
    rings + 3.50 g filing scrap + 1.10 g polishing dust.
    Actual loss = 42.00 - 37.00 - 3.50 - 1.10 = 0.40 g gross
    In fine: 42.00 × 0.9167 = 38.501 g issued
             returned fine = (37.00 + 3.50 + 1.10) × 0.9167 = 37.917 g
             fine loss = 38.501 - 37.917 = 0.584 g
             2% allowance = 38.501 × 0.02 = 0.770 g
             excess = max(0, 0.584 - 0.770) = 0 → Pass
    """

    def test_ramesh_filing_polishing_scenario(self):
        issued_fine = round(42.00 * 0.9167, 3)  # 38.501
        returned_fine = round((37.00 + 3.50 + 1.10) * 0.9167, 3)  # 37.967

        doc = _doc(
            issued_fine_wt=issued_fine,
            wastage_allowance_pct=2.0,
            returned_items=[_returned_row(returned_fine)],
            issued_stone_pieces=0,
            stone_breakage_allowance_pct=5.0,
            stones_broken=0,
            excess_fine_loss=0,
            excess_broken=0,
        )
        doc._calc_metal_reconciliation()
        doc._calc_stone_reconciliation()
        doc._set_verdict()

        fine_loss = round(issued_fine - returned_fine, 3)
        allowed = round(issued_fine * 0.02, 3)

        self.assertAlmostEqual(doc.fine_loss, fine_loss, places=3)
        self.assertAlmostEqual(doc.allowed_fine_loss, allowed, places=3)
        # Loss should be within allowance → Pass
        self.assertEqual(doc.excess_fine_loss, max(0, round(fine_loss - allowed, 3)))
        if fine_loss <= allowed:
            self.assertEqual(doc.verdict, "Pass")
