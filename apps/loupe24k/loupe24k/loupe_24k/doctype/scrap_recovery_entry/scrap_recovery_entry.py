from frappe.model.document import Document


class ScrapRecoveryEntry(Document):
    def validate(self):
        self.total_gross_wt = sum(r.gross_wt or 0 for r in self.scrap_items)
        self.total_est_fine_wt = sum(r.fine_wt or 0 for r in self.scrap_items)
        self.fine_recovered = round(
            self.total_est_fine_wt * (self.recovery_pct or 100) / 100, 3
        )
