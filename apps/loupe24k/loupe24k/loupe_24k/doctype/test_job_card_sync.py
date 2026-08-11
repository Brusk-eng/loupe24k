import unittest
from types import SimpleNamespace
from unittest.mock import patch

from loupe24k.loupe_24k.doctype import job_card_sync


class _FakeRow:
    def __init__(self, backend, doctype, name=None, data=None, is_new=True):
        self._backend = backend
        self.doctype = doctype
        self.name = name
        self.docstatus = 0
        self._is_new = is_new
        if data:
            self.__dict__.update(data)

    def is_new(self):
        return self._is_new

    def append(self, fieldname, value):
        current = getattr(self, fieldname, None) or []
        current.append(value)
        setattr(self, fieldname, current)

    def insert(self, ignore_permissions=True):
        self._backend.insert(self)
        self._is_new = False
        return self

    def save(self, ignore_permissions=True):
        self._backend.save(self)
        return self

    def cancel(self):
        self.docstatus = 2


class _FakeDB:
    def __init__(self, backend):
        self.backend = backend

    def get_value(self, doctype, filters, fieldname):
        if doctype == "Stone Master":
            return self.backend.default_stone_master
        matches = self.backend.filter_docs(doctype, filters)
        if not matches:
            return None
        return getattr(matches[0], fieldname, None)


class _FakeBackend:
    def __init__(self):
        self.db = _FakeDB(self)
        self.utils = SimpleNamespace(today=lambda: "2026-08-11")
        self._logger = SimpleNamespace(warning=lambda *args, **kwargs: None)
        self.default_stone_master = "Round Diamond"
        self._counter = 1
        self._docs = {
            "Fine Gold Ledger Entry": {},
            "Stone Ledger Entry": {},
            "Scrap Recovery Entry": {},
        }

    def logger(self):
        return self._logger

    def insert(self, row):
        if not row.name:
            row.name = f"{row.doctype}-{self._counter:04d}"
            self._counter += 1
        self._docs[row.doctype][row.name] = row

    def save(self, row):
        self._docs[row.doctype][row.name] = row

    def get_doc(self, arg1, arg2=None):
        if isinstance(arg1, dict):
            return _FakeRow(self, arg1["doctype"], data=arg1, is_new=True)
        return self._docs[arg1][arg2]

    def get_all(self, doctype, filters=None, pluck=None):
        matches = self.filter_docs(doctype, filters or {})
        if pluck == "name":
            return [d.name for d in matches]
        return matches

    def delete_doc(self, doctype, name, ignore_permissions=True, force=1):
        self._docs[doctype].pop(name, None)

    def get_cached_doc(self, doctype, name):
        if doctype == "Work Order":
            return SimpleNamespace(name=name, karat="22K", production_item="22K Gold Grain")
        return None

    def filter_docs(self, doctype, filters):
        rows = list(self._docs.get(doctype, {}).values())
        result = []
        for row in rows:
            ok = True
            for fieldname, expected in filters.items():
                if isinstance(expected, list) and expected and expected[0] == "!=":
                    if getattr(row, fieldname, None) == expected[1]:
                        ok = False
                        break
                elif getattr(row, fieldname, None) != expected:
                    ok = False
                    break
            if ok:
                result.append(row)
        return result


class _JobCard(SimpleNamespace):
    def __init__(self, changed_fields=None, **kwargs):
        super().__init__(**kwargs)
        self._changed_fields = set(changed_fields or [])

    def has_value_changed(self, fieldname):
        return fieldname in self._changed_fields


class TestJobCardLedgerSync(unittest.TestCase):
    def setUp(self):
        self.fake_frappe = _FakeBackend()
        self.job_card = _JobCard(
            name="JC-0001",
            work_order="WO-0001",
            weight_in=10,
            weight_out=9,
            scrap_wt=0.75,
            loss_wt=0.25,
            stone_in=0,
            stone_set=0,
            stone_broken=0,
            changed_fields={"weight_out"},
        )

    def _count(self, doctype):
        return len(self.fake_frappe._docs[doctype])

    def test_submit_creates_linked_entries(self):
        with patch.object(job_card_sync, "frappe", self.fake_frappe):
            job_card_sync.sync_job_card_ledgers(self.job_card, event="on_submit")

        self.assertEqual(self._count("Fine Gold Ledger Entry"), 1)
        self.assertEqual(self._count("Scrap Recovery Entry"), 1)
        self.assertEqual(self._count("Stone Ledger Entry"), 0)

    def test_save_without_tracked_changes_does_not_write(self):
        with patch.object(job_card_sync, "frappe", self.fake_frappe):
            job_card_sync.sync_job_card_ledgers(self.job_card, event="on_submit")
            existing_fgl = next(iter(self.fake_frappe._docs["Fine Gold Ledger Entry"].values()))
            existing_name = existing_fgl.name

            unchanged = _JobCard(
                name="JC-0001",
                work_order="WO-0001",
                weight_in=10,
                weight_out=9,
                scrap_wt=0.75,
                loss_wt=0.25,
                stone_in=0,
                stone_set=0,
                stone_broken=0,
                changed_fields=set(),
            )
            job_card_sync.sync_job_card_ledgers(unchanged, event="on_update_after_submit")

        self.assertEqual(self._count("Fine Gold Ledger Entry"), 1)
        current = next(iter(self.fake_frappe._docs["Fine Gold Ledger Entry"].values()))
        self.assertEqual(current.name, existing_name)

    def test_weight_update_updates_existing_row(self):
        with patch.object(job_card_sync, "frappe", self.fake_frappe):
            job_card_sync.sync_job_card_ledgers(self.job_card, event="on_submit")
            fgl = next(iter(self.fake_frappe._docs["Fine Gold Ledger Entry"].values()))
            before_name = fgl.name
            before_gross = fgl.gross_wt

            self.job_card.weight_out = 8.5
            self.job_card._changed_fields = {"weight_out"}
            job_card_sync.sync_job_card_ledgers(self.job_card, event="on_update_after_submit")

        self.assertEqual(self._count("Fine Gold Ledger Entry"), 1)
        fgl = next(iter(self.fake_frappe._docs["Fine Gold Ledger Entry"].values()))
        self.assertEqual(fgl.name, before_name)
        self.assertNotEqual(fgl.gross_wt, before_gross)
        self.assertEqual(fgl.gross_wt, 8.5)

    def test_cancel_cleans_up_linked_rows(self):
        with patch.object(job_card_sync, "frappe", self.fake_frappe):
            job_card_sync.sync_job_card_ledgers(self.job_card, event="on_submit")
            job_card_sync.sync_job_card_ledgers(self.job_card, event="on_cancel")

        self.assertEqual(self._count("Fine Gold Ledger Entry"), 0)
        self.assertEqual(self._count("Scrap Recovery Entry"), 0)
        self.assertEqual(self._count("Stone Ledger Entry"), 0)

    def test_idempotent_resync_does_not_duplicate_rows(self):
        with patch.object(job_card_sync, "frappe", self.fake_frappe):
            job_card_sync.sync_job_card_ledgers(self.job_card, event="on_submit")
            job_card_sync.sync_job_card_ledgers(self.job_card, event="on_submit")
            job_card_sync.sync_job_card_ledgers(self.job_card, event="on_submit")

        self.assertEqual(self._count("Fine Gold Ledger Entry"), 1)
        self.assertEqual(self._count("Scrap Recovery Entry"), 1)

    def test_tc03_non_tracked_field_update_no_ledger_rewrite(self):
        with patch.object(job_card_sync, "frappe", self.fake_frappe):
            job_card_sync.sync_job_card_ledgers(self.job_card, event="on_submit")
            before_fgl = next(iter(self.fake_frappe._docs["Fine Gold Ledger Entry"].values()))
            before_gross = before_fgl.gross_wt
            before_name = before_fgl.name

            unchanged = _JobCard(
                name="JC-0001",
                work_order="WO-0001",
                remarks="new remarks only",
                weight_in=10,
                weight_out=9,
                scrap_wt=0.75,
                loss_wt=0.25,
                stone_in=0,
                stone_set=0,
                stone_broken=0,
                changed_fields={"remarks"},
            )
            job_card_sync.sync_job_card_ledgers(unchanged, event="on_update_after_submit")

        after_fgl = next(iter(self.fake_frappe._docs["Fine Gold Ledger Entry"].values()))
        self.assertEqual(after_fgl.name, before_name)
        self.assertEqual(after_fgl.gross_wt, before_gross)

    def test_tc04_weight_in_update_propagates(self):
        with patch.object(job_card_sync, "frappe", self.fake_frappe):
            job_card_sync.sync_job_card_ledgers(self.job_card, event="on_submit")
            self.job_card.weight_in = 12.5
            self.job_card._changed_fields = {"weight_in"}
            job_card_sync.sync_job_card_ledgers(self.job_card, event="on_update_after_submit")

        fgl = next(iter(self.fake_frappe._docs["Fine Gold Ledger Entry"].values()))
        self.assertEqual(fgl.voucher_type, "Job Card")
        self.assertEqual(fgl.voucher_no, "JC-0001")

    def test_tc06_scrap_and_loss_update_propagates(self):
        with patch.object(job_card_sync, "frappe", self.fake_frappe):
            job_card_sync.sync_job_card_ledgers(self.job_card, event="on_submit")
            self.job_card.scrap_wt = 1.5
            self.job_card.loss_wt = 0.5
            self.job_card._changed_fields = {"scrap_wt", "loss_wt"}
            job_card_sync.sync_job_card_ledgers(self.job_card, event="on_update_after_submit")

        sre = next(iter(self.fake_frappe._docs["Scrap Recovery Entry"].values()))
        self.assertEqual(len(sre.scrap_items), 1)
        self.assertEqual(sre.scrap_items[0]["gross_wt"], 1.5)
        self.assertEqual(sre.voucher_type, "Job Card")
        self.assertEqual(sre.voucher_no, "JC-0001")

    def test_tc09_missing_optional_stone_fields_safe(self):
        with patch.object(job_card_sync, "frappe", self.fake_frappe):
            self.fake_frappe.default_stone_master = None
            with_stones = _JobCard(
                name="JC-0002",
                work_order="WO-0001",
                weight_in=10,
                weight_out=9,
                scrap_wt=0.5,
                loss_wt=0.1,
                stone_in=10,
                stone_set=8,
                stone_broken=1,
                changed_fields={"stone_set"},
            )
            job_card_sync.sync_job_card_ledgers(with_stones, event="on_submit")

        self.assertEqual(self._count("Stone Ledger Entry"), 0)
        self.assertEqual(self._count("Fine Gold Ledger Entry"), 1)
        self.assertEqual(self._count("Scrap Recovery Entry"), 1)

    def test_tc10_field_change_gate_works(self):
        with patch.object(job_card_sync, "frappe", self.fake_frappe):
            job_card_sync.sync_job_card_ledgers(self.job_card, event="on_submit")
            before_fgl = next(iter(self.fake_frappe._docs["Fine Gold Ledger Entry"].values()))
            before_gross = before_fgl.gross_wt

            unchanged = _JobCard(
                name="JC-0001",
                work_order="WO-0001",
                weight_in=10,
                weight_out=9,
                scrap_wt=0.75,
                loss_wt=0.25,
                changed_fields=set(),
            )
            job_card_sync.sync_job_card_ledgers(unchanged, event="on_update_after_submit")
            middle_fgl = next(iter(self.fake_frappe._docs["Fine Gold Ledger Entry"].values()))
            self.assertEqual(middle_fgl.gross_wt, before_gross)

            self.job_card.weight_out = 8
            self.job_card._changed_fields = {"weight_out"}
            job_card_sync.sync_job_card_ledgers(self.job_card, event="on_update_after_submit")

        after_fgl = next(iter(self.fake_frappe._docs["Fine Gold Ledger Entry"].values()))
        self.assertEqual(after_fgl.gross_wt, 8)

    def test_update_after_submit_keeps_voucher_fields_for_all_synced_ledgers(self):
        with patch.object(job_card_sync, "frappe", self.fake_frappe):
            with_stones = _JobCard(
                name="JC-0003",
                work_order="WO-0001",
                weight_in=10,
                weight_out=9,
                scrap_wt=0.75,
                loss_wt=0.25,
                stone_in=2,
                stone_set=2,
                stone_broken=0,
                changed_fields={"weight_out"},
            )
            job_card_sync.sync_job_card_ledgers(with_stones, event="on_submit")
            with_stones.weight_out = 8.5
            with_stones._changed_fields = {"weight_out"}
            job_card_sync.sync_job_card_ledgers(with_stones, event="on_update_after_submit")

        for doctype in ("Fine Gold Ledger Entry", "Scrap Recovery Entry", "Stone Ledger Entry"):
            self.assertEqual(len(self.fake_frappe._docs[doctype]), 1)
            row = next(iter(self.fake_frappe._docs[doctype].values()))
            self.assertEqual(row.voucher_type, "Job Card")
            self.assertEqual(row.voucher_no, "JC-0003")


if __name__ == "__main__":
    unittest.main()
