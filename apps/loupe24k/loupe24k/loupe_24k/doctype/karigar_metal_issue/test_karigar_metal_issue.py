"""
Unit tests for Karigar Metal Issue controller.

Rules under test:
  - _calc_totals sums gross_wt, fine_wt from metal_items
  - _calc_totals sums pieces, carat from stone_items
  - Empty child tables produce zero totals
  - due_back_date is auto-set to dispatch_date + 1 year when not provided
  - due_back_date is NOT overwritten when already set
  - status is set to "Issued" on submit
"""
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from loupe24k.loupe_24k.doctype.karigar_metal_issue.karigar_metal_issue import (
    KarigarMetalIssue,
)


def _doc(**kwargs):
    d = KarigarMetalIssue.__new__(KarigarMetalIssue)
    defaults = {
        "metal_items": [],
        "stone_items": [],
        "dispatch_date": None,
        "due_back_date": None,
    }
    defaults.update(kwargs)
    d.__dict__.update(defaults)
    return d


def _metal_row(gross_wt, fine_wt):
    return SimpleNamespace(gross_wt=gross_wt, fine_wt=fine_wt)


def _stone_row(pieces, carat):
    return SimpleNamespace(pieces=pieces, carat=carat)


class TestCalcTotals(unittest.TestCase):
    def test_empty_tables_give_zero_totals(self):
        doc = _doc()
        doc._calc_totals()
        self.assertEqual(doc.total_gross_wt, 0)
        self.assertEqual(doc.total_fine_wt, 0)
        self.assertEqual(doc.total_stone_pieces, 0)
        self.assertAlmostEqual(doc.total_stone_carat, 0)

    def test_single_metal_row(self):
        doc = _doc(metal_items=[_metal_row(59.70, 54.727)])
        doc._calc_totals()
        self.assertAlmostEqual(doc.total_gross_wt, 59.70)
        self.assertAlmostEqual(doc.total_fine_wt, 54.727)

    def test_multiple_metal_rows(self):
        # Spec scenario: after filing (38.5g) and polishing (37.0g) separately issued
        doc = _doc(metal_items=[
            _metal_row(38.5, round(38.5 * 0.9167, 3)),
            _metal_row(37.0, round(37.0 * 0.9167, 3)),
        ])
        doc._calc_totals()
        self.assertAlmostEqual(doc.total_gross_wt, 75.5, places=3)
        self.assertAlmostEqual(doc.total_fine_wt, round(38.5 * 0.9167 + 37.0 * 0.9167, 3), places=3)

    def test_none_values_in_metal_row_treated_as_zero(self):
        doc = _doc(metal_items=[_metal_row(None, None), _metal_row(10.0, 9.167)])
        doc._calc_totals()
        self.assertAlmostEqual(doc.total_gross_wt, 10.0)
        self.assertAlmostEqual(doc.total_fine_wt, 9.167)

    def test_stone_totals(self):
        # Melee parcel: 30 pieces, 0.75 ct; solitaire: 1 piece, 0.30 ct
        doc = _doc(stone_items=[
            _stone_row(30, 0.75),
            _stone_row(1, 0.30),
        ])
        doc._calc_totals()
        self.assertEqual(doc.total_stone_pieces, 31)
        self.assertAlmostEqual(doc.total_stone_carat, 1.05, places=3)

    def test_none_stone_values_treated_as_zero(self):
        doc = _doc(stone_items=[_stone_row(None, None), _stone_row(5, 0.25)])
        doc._calc_totals()
        self.assertEqual(doc.total_stone_pieces, 5)
        self.assertAlmostEqual(doc.total_stone_carat, 0.25)


class TestDueBackDate(unittest.TestCase):
    def test_due_back_date_auto_set_one_year_forward(self):
        doc = _doc(dispatch_date="2026-01-15", due_back_date=None)
        with patch("loupe24k.loupe_24k.doctype.karigar_metal_issue.karigar_metal_issue.frappe") as mock_frappe:
            mock_frappe.utils.getdate.return_value = __import__("datetime").date(2026, 1, 15)
            mock_frappe.utils.add_years.return_value = "2027-01-15"
            doc.validate()
            mock_frappe.utils.add_years.assert_called_once()
        self.assertEqual(doc.due_back_date, "2027-01-15")

    def test_existing_due_back_date_not_overwritten(self):
        doc = _doc(dispatch_date="2026-01-15", due_back_date="2026-06-30")
        with patch("loupe24k.loupe_24k.doctype.karigar_metal_issue.karigar_metal_issue.frappe") as mock_frappe:
            mock_frappe.utils.getdate.return_value = __import__("datetime").date(2026, 1, 15)
            doc.validate()
            mock_frappe.utils.add_years.assert_not_called()
        self.assertEqual(doc.due_back_date, "2026-06-30")

    def test_no_dispatch_date_skips_due_date(self):
        doc = _doc(dispatch_date=None, due_back_date=None)
        with patch("loupe24k.loupe_24k.doctype.karigar_metal_issue.karigar_metal_issue.frappe") as mock_frappe:
            doc.validate()
            mock_frappe.utils.add_years.assert_not_called()
        self.assertIsNone(doc.due_back_date)


class TestOnSubmit(unittest.TestCase):
    def test_status_set_to_issued_on_submit(self):
        doc = _doc()
        doc.db_set = MagicMock()
        doc.on_submit()
        self.assertEqual(doc.status, "Issued")
        doc.db_set.assert_called_once_with("status", "Issued")


class TestSeedScenarios(unittest.TestCase):
    """
    Verify _calc_totals() output for the five KMI seed scenarios defined in
    data/seed_data.py _seed_karigar_metal_issues().
    """

    def test_seed_001_filing_ramesh(self):
        # Ring Blank 22K: 50g → fine = 45.835g; no stones
        doc = _doc(
            metal_items=[_metal_row(50.0, round(50.0 * 0.9167, 3))],
            stone_items=[],
        )
        doc._calc_totals()
        self.assertAlmostEqual(doc.total_gross_wt, 50.0)
        self.assertAlmostEqual(doc.total_fine_wt, round(50.0 * 0.9167, 3))
        self.assertEqual(doc.total_stone_pieces, 0)

    def test_seed_002_setting_suresh_with_stones(self):
        # Plain Band 22K: 45g + Round Diamond 20 pcs, 0.50 ct
        doc = _doc(
            metal_items=[_metal_row(45.0, round(45.0 * 0.9167, 3))],
            stone_items=[_stone_row(20, 0.50)],
        )
        doc._calc_totals()
        self.assertAlmostEqual(doc.total_gross_wt, 45.0)
        self.assertAlmostEqual(doc.total_fine_wt, round(45.0 * 0.9167, 3))
        self.assertEqual(doc.total_stone_pieces, 20)
        self.assertAlmostEqual(doc.total_stone_carat, 0.50)

    def test_seed_003_casting_ramesh(self):
        # 22K Gold Grain: 100g → fine = 91.670g; no stones
        doc = _doc(
            metal_items=[_metal_row(100.0, round(100.0 * 0.9167, 3))],
            stone_items=[],
        )
        doc._calc_totals()
        self.assertAlmostEqual(doc.total_gross_wt, 100.0)
        self.assertAlmostEqual(doc.total_fine_wt, round(100.0 * 0.9167, 3))

    def test_seed_004_polishing_ramesh(self):
        # Plain Band 22K: 40g → fine = 36.668g; no stones
        doc = _doc(
            metal_items=[_metal_row(40.0, round(40.0 * 0.9167, 3))],
            stone_items=[],
        )
        doc._calc_totals()
        self.assertAlmostEqual(doc.total_gross_wt, 40.0)
        self.assertAlmostEqual(doc.total_fine_wt, round(40.0 * 0.9167, 3))

    def test_seed_005_setting_suresh_24k_with_solitaire(self):
        # Plain Band 24K: 20g (touch = 1.0) + Certified Solitaire 1 pc, 0.30 ct
        doc = _doc(
            metal_items=[_metal_row(20.0, 20.0)],   # 24K touch = 1.0
            stone_items=[_stone_row(1, 0.30)],
        )
        doc._calc_totals()
        self.assertAlmostEqual(doc.total_gross_wt, 20.0)
        self.assertAlmostEqual(doc.total_fine_wt, 20.0)
        self.assertEqual(doc.total_stone_pieces, 1)
        self.assertAlmostEqual(doc.total_stone_carat, 0.30)
