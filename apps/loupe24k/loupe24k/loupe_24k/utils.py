import frappe
from frappe.twofactor import get_qr_svg_code


@frappe.whitelist()
def get_qr_code(doctype, docname):
    """Return a base64 SVG data URI QR code linking to the given document.

    Used by custom print formats (e.g. the Work Order traveler) to embed a
    scannable QR code that opens the record directly in the desk.
    """
    url = frappe.utils.get_url_to_form(doctype, docname)
    svg_b64 = get_qr_svg_code(url).decode()
    return f"data:image/svg+xml;base64,{svg_b64}"
