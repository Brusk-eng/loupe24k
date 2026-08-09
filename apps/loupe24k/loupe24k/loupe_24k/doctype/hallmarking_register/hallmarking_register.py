from frappe.model.document import Document


class HallmarkingRegister(Document):
    def validate(self):
        # Net weight = gross weight minus any stone/setting weight
        self.net_wt = round((self.gross_wt or 0) - (self.stone_wt or 0), 3)
