import frappe
from frappe.model.document import Document


class KarigarMetalIssue(Document):
    def validate(self):
        self._calc_totals()
        if self.dispatch_date and not self.due_back_date:
            from datetime import date
            d = frappe.utils.getdate(self.dispatch_date)
            self.due_back_date = frappe.utils.add_years(d, 1)

    def _calc_totals(self):
        self.total_gross_wt = sum(r.gross_wt or 0 for r in self.metal_items)
        self.total_fine_wt = sum(r.fine_wt or 0 for r in self.metal_items)
        self.total_stone_pieces = sum(r.pieces or 0 for r in self.stone_items)
        self.total_stone_carat = sum(r.carat or 0 for r in self.stone_items)

    def on_submit(self):
        self.status = "Issued"
        self.db_set("status", "Issued")
