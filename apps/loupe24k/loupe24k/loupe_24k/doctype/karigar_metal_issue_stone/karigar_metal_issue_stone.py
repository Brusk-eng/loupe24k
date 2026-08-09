from frappe.model.document import Document


class KarigarMetalIssueStone(Document):
    def validate(self):
        if self.rate_per_ct and self.carat:
            self.value = round(self.rate_per_ct * self.carat, 2)
