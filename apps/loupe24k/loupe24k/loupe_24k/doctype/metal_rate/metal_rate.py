import frappe
from frappe.model.document import Document

TOUCH_FACTORS = {"24K": 1.0000, "22K": 0.9167, "18K": 0.7500}


class MetalRate(Document):
    def validate(self):
        self.touch = TOUCH_FACTORS.get(self.karat, 1.0)
        if self.derived_from_24k and self.karat != "24K":
            rate_24k = frappe.db.get_value(
                "Metal Rate",
                {"date": self.date, "karat": "24K"},
                "rate_per_g"
            )
            if rate_24k:
                self.rate_per_g = round(rate_24k * self.touch, 2)
