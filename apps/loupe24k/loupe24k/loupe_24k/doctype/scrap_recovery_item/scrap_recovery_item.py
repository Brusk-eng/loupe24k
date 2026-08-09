from frappe.model.document import Document

TOUCH_FACTORS = {"24K": 1.0000, "22K": 0.9167, "18K": 0.7500}


class ScrapRecoveryItem(Document):
    def validate(self):
        self.touch = TOUCH_FACTORS.get(self.karat, 1.0)
        self.fine_wt = round((self.gross_wt or 0) * self.touch, 3)
