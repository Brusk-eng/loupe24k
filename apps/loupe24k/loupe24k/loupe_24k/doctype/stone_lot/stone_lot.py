import frappe
from frappe.model.document import Document


class StoneLot(Document):
    def validate(self):
        if self.rate_per_ct and self.total_carat:
            self.total_value = round(self.rate_per_ct * self.total_carat, 2)
