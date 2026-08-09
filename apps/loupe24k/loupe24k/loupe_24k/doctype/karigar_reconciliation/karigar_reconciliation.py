import frappe
from frappe.model.document import Document


class KarigarReconciliation(Document):
    def validate(self):
        self._pull_issue_data()
        self._calc_metal_reconciliation()
        self._calc_stone_reconciliation()
        self._set_verdict()

    def _pull_issue_data(self):
        if self.issue_ref:
            doc = frappe.get_doc("Karigar Metal Issue", self.issue_ref)
            self.issued_gross_wt = doc.total_gross_wt
            self.issued_fine_wt = doc.total_fine_wt
            self.issued_stone_pieces = doc.total_stone_pieces
            self.issued_stone_carat = doc.total_stone_carat
            if not self.wastage_allowance_pct:
                self.wastage_allowance_pct = frappe.db.get_value(
                    "Supplier", doc.karigar, "wastage_allowance_pct"
                ) or 2.0
            if not self.stone_breakage_allowance_pct:
                self.stone_breakage_allowance_pct = frappe.db.get_value(
                    "Supplier", doc.karigar, "breakage_allowance_pct"
                ) or 5.0

    def _calc_metal_reconciliation(self):
        self.returned_fine_wt = sum(r.fine_wt or 0 for r in self.returned_items)
        self.fine_loss = round((self.issued_fine_wt or 0) - self.returned_fine_wt, 3)
        self.allowed_fine_loss = round(
            (self.issued_fine_wt or 0) * (self.wastage_allowance_pct or 0) / 100, 3
        )
        self.excess_fine_loss = max(0, round(self.fine_loss - self.allowed_fine_loss, 3))

    def _calc_stone_reconciliation(self):
        allowed_broken = int(
            (self.issued_stone_pieces or 0) * (self.stone_breakage_allowance_pct or 0) / 100
        )
        self.excess_broken = max(0, (self.stones_broken or 0) - allowed_broken)

    def _set_verdict(self):
        if self.excess_fine_loss > 0 or self.excess_broken > 0:
            self.verdict = "Fail" if self.excess_fine_loss > 0.1 else "Warning"
        else:
            self.verdict = "Pass"
