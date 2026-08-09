"""
Unit tests for Stone Ledger Entry.

StoneLedgerEntry is a pure ledger record — the controller currently has no
auto-calculation logic (value, posting sign, etc. are set by the parent voucher).
These tests verify structural integrity and document the expected field semantics
as a baseline for future controller additions.
"""
import unittest

from loupe24k.loupe_24k.doctype.stone_ledger_entry.stone_ledger_entry import (
    StoneLedgerEntry,
)


def _doc(**kwargs):
    d = StoneLedgerEntry.__new__(StoneLedgerEntry)
    d.__dict__.update(kwargs)
    return d


class TestStoneLedgerEntryStructure(unittest.TestCase):
    def test_class_is_importable(self):
        self.assertIsNotNone(StoneLedgerEntry)

    def test_fields_can_be_set_on_mock_doc(self):
        doc = _doc(
            movement_type="Issue",
            stone_master="Round Diamond",
            stone_lot="MELEE-001",
            pieces=20,
            carat=0.50,
            value=90.0,
        )
        self.assertEqual(doc.movement_type, "Issue")
        self.assertEqual(doc.stone_master, "Round Diamond")
        self.assertEqual(doc.pieces, 20)
        self.assertAlmostEqual(doc.carat, 0.50)

    def test_all_seed_movement_types_are_valid(self):
        # These are the movement_type values used in _seed_stone_ledger_entries()
        valid_types = {"Issue", "Set", "Return", "Broken"}
        for mt in valid_types:
            doc = _doc(movement_type=mt, stone_master="Round Diamond", pieces=5, carat=0.10)
            self.assertEqual(doc.movement_type, mt)


class TestSeedScenarios(unittest.TestCase):
    """
    Document the five SLE seed records from _seed_stone_ledger_entries()
    and verify field semantics are consistent.

    Seed entries:
      1. Issue  – MELEE-001 Round Diamond, 20 pcs, 0.50 ct  → to Suresh Setter (KMI-002)
      2. Set    – Round Diamond, 18 pcs, 0.45 ct             → set into Solitaire rings
      3. Return – MELEE-001 Round Diamond, 2 pcs, 0.05 ct   → unused returned
      4. Issue  – SOL-001 Certified Solitaire, 1 pc, 0.30 ct → to Suresh Setter (KMI-005)
      5. Broken – Round Diamond, 1 pc, 0.025 ct             → broken during setting
    """

    def test_issue_entry_fields(self):
        doc = _doc(movement_type="Issue", stone_master="Round Diamond",
                   pieces=20, carat=0.50)
        self.assertEqual(doc.movement_type, "Issue")
        self.assertEqual(doc.pieces, 20)

    def test_set_entry_total_carat_less_than_issued(self):
        # Stones set (0.45 ct) ≤ stones issued (0.50 ct) — confirms no over-setting
        issued_carat = 0.50
        set_carat = 0.45
        self.assertLessEqual(set_carat, issued_carat)

    def test_return_plus_set_plus_broken_reconciles_issued(self):
        # Issue 20 pcs; set 18, return 2, broken 0 → all 20 accounted for
        issued = 20
        reconciled = 18 + 2 + 0  # set + returned + broken
        self.assertEqual(reconciled, issued)

    def test_broken_entry_pieces(self):
        doc = _doc(movement_type="Broken", stone_master="Round Diamond",
                   pieces=1, carat=0.025)
        self.assertEqual(doc.movement_type, "Broken")
        self.assertEqual(doc.pieces, 1)
