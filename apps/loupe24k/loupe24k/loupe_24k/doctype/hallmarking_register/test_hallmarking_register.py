"""
Unit tests for Hallmarking Register controller.

Rules under test:
  - net_wt = gross_wt - stone_wt  (rounded to 3 dp)
  - None stone_wt treated as 0 (plain metal rings have no stone weight)
  - None gross_wt treated as 0
"""
import unittest

from loupe24k.loupe_24k.doctype.hallmarking_register.hallmarking_register import (
    HallmarkingRegister,
)


def _doc(**kwargs):
    d = HallmarkingRegister.__new__(HallmarkingRegister)
    defaults = {"gross_wt": 0.0, "stone_wt": None}
    defaults.update(kwargs)
    d.__dict__.update(defaults)
    return d


class TestNetWeightCalculation(unittest.TestCase):
    def test_plain_ring_none_stone_wt(self):
        # Plain band 22K: no stone, net == gross
        doc = _doc(gross_wt=4.5, stone_wt=None)
        doc.validate()
        self.assertEqual(doc.net_wt, 4.5)

    def test_plain_ring_zero_stone_wt(self):
        doc = _doc(gross_wt=4.5, stone_wt=0.0)
        doc.validate()
        self.assertEqual(doc.net_wt, 4.5)

    def test_solitaire_ring_with_stone(self):
        # 5.2g gross, 0.15g stone weight → 5.05g net
        doc = _doc(gross_wt=5.2, stone_wt=0.15)
        doc.validate()
        self.assertAlmostEqual(doc.net_wt, 5.05, places=3)

    def test_rounding_to_three_decimal_places(self):
        doc = _doc(gross_wt=5.2345, stone_wt=0.1234)
        doc.validate()
        self.assertEqual(doc.net_wt, round(5.2345 - 0.1234, 3))

    def test_none_gross_wt_treated_as_zero(self):
        doc = _doc(gross_wt=None, stone_wt=None)
        doc.validate()
        self.assertEqual(doc.net_wt, 0.0)

    def test_net_wt_always_non_negative_for_valid_data(self):
        # Stone weight should never exceed gross weight in practice
        for gross, stone in [(5.0, 0.5), (4.0, 0.0), (3.5, 0.2)]:
            with self.subTest(gross=gross, stone=stone):
                doc = _doc(gross_wt=gross, stone_wt=stone)
                doc.validate()
                self.assertGreaterEqual(doc.net_wt, 0)

    def test_validate_always_sets_net_wt(self):
        doc = _doc(gross_wt=6.0, stone_wt=0.3)
        doc.validate()
        self.assertTrue(hasattr(doc, "net_wt"))


class TestSeedScenarios(unittest.TestCase):
    """
    Verify that each hallmarking seed entry produces the correct net weight.
    These match _seed_hallmarking_entries() in data/seed_data.py.
    """

    def test_hmr_seed_1_plain_band_22k(self):
        # 4.5g gross, no stone → net 4.5g
        doc = _doc(gross_wt=4.5, stone_wt=None)
        doc.validate()
        self.assertEqual(doc.net_wt, 4.5)

    def test_hmr_seed_2_solitaire_22k(self):
        # 5.2g gross, 0.15g stone → 5.05g net
        doc = _doc(gross_wt=5.2, stone_wt=0.15)
        doc.validate()
        self.assertAlmostEqual(doc.net_wt, 5.05, places=3)

    def test_hmr_seed_3_plain_band_24k(self):
        # 4.0g gross, no stone → net 4.0g
        doc = _doc(gross_wt=4.0, stone_wt=None)
        doc.validate()
        self.assertEqual(doc.net_wt, 4.0)

    def test_hmr_seed_4_plain_band_22k(self):
        # 4.8g gross, no stone → net 4.8g
        doc = _doc(gross_wt=4.8, stone_wt=None)
        doc.validate()
        self.assertEqual(doc.net_wt, 4.8)

    def test_hmr_seed_5_solitaire_22k(self):
        # 5.5g gross, 0.20g stone → 5.3g net
        doc = _doc(gross_wt=5.5, stone_wt=0.20)
        doc.validate()
        self.assertAlmostEqual(doc.net_wt, 5.3, places=3)
