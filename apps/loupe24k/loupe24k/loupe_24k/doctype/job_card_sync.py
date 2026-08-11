import frappe


TRACKED_FIELDS = ("weight_in", "weight_out", "scrap_wt", "loss_wt")
TOUCH_FACTORS = {"24K": 1.0, "22K": 0.9167, "18K": 0.75}
LINKED_DOCTYPES = (
    "Fine Gold Ledger Entry",
    "Stone Ledger Entry",
    "Scrap Recovery Entry",
)


def on_submit(doc, method=None):
    sync_job_card_ledgers(doc, event="on_submit")


def on_update_after_submit(doc, method=None):
    sync_job_card_ledgers(doc, event="on_update_after_submit")


def on_cancel(doc, method=None):
    sync_job_card_ledgers(doc, event="on_cancel")


def sync_job_card_ledgers(doc, event):
    if event == "on_update_after_submit" and not _tracked_fields_changed(doc):
        return

    if event == "on_cancel" or getattr(doc, "docstatus", 0) == 2:
        _cleanup_linked_entries(doc)
        return

    item_code = _resolve_item_code(doc)
    karat = _resolve_karat(doc)
    posting_date = _resolve_posting_date(doc)

    _upsert_fine_gold_ledger(doc, posting_date, item_code, karat)
    _upsert_scrap_recovery_entry(doc, posting_date, item_code, karat)
    _upsert_stone_ledger_entry(doc, posting_date)


def _tracked_fields_changed(doc):
    checker = getattr(doc, "has_value_changed", None)
    if not callable(checker):
        return True
    return any(checker(field) for field in TRACKED_FIELDS)


def _resolve_work_order(doc):
    work_order = getattr(doc, "work_order", None)
    if not work_order:
        return None
    return frappe.get_cached_doc("Work Order", work_order)


def _resolve_item_code(doc):
    for fieldname in ("item_code", "production_item"):
        value = getattr(doc, fieldname, None)
        if value:
            return value

    wo = _resolve_work_order(doc)
    if wo:
        for fieldname in ("production_item", "item_code"):
            value = getattr(wo, fieldname, None)
            if value:
                return value
    return None


def _resolve_karat(doc):
    karat = getattr(doc, "karat", None)
    if karat:
        return karat

    wo = _resolve_work_order(doc)
    if wo and getattr(wo, "karat", None):
        return wo.karat
    return "22K"


def _resolve_posting_date(doc):
    for fieldname in ("posting_date", "manufacturing_date"):
        value = getattr(doc, fieldname, None)
        if value:
            return value
    return frappe.utils.today()


def _upsert_fine_gold_ledger(doc, posting_date, item_code, karat):
    row = _get_or_create_linked_entry("Fine Gold Ledger Entry", doc)
    row.voucher_type = "Job Card"
    row.voucher_no = doc.name
    row.entry_type = "Receipt"
    row.posting_date = posting_date
    row.item = item_code
    row.karat = karat
    row.gross_wt = round(getattr(doc, "weight_out", 0) or 0, 3)
    row.remarks = (
        f"Auto-synced from Job Card {doc.name} "
        f"(weight_in={getattr(doc, 'weight_in', 0) or 0}, "
        f"weight_out={getattr(doc, 'weight_out', 0) or 0}, "
        f"scrap={getattr(doc, 'scrap_wt', 0) or 0}, "
        f"loss={getattr(doc, 'loss_wt', 0) or 0})"
    )
    _save_or_insert(row)


def _upsert_scrap_recovery_entry(doc, posting_date, item_code, karat):
    row = _get_or_create_linked_entry("Scrap Recovery Entry", doc)
    row.voucher_type = "Job Card"
    row.voucher_no = doc.name
    row.entry_date = posting_date
    row.recovery_type = "Remelt"
    row.recovery_pct = 100
    row.credit_posting = 1
    row.scrap_items = []
    scrap_wt = round(getattr(doc, "scrap_wt", 0) or 0, 3)
    if scrap_wt > 0 and item_code:
        row.append(
            "scrap_items",
            {
                "item_code": item_code,
                "scrap_type": "Other",
                "gross_wt": scrap_wt,
                "karat": karat,
                "touch": TOUCH_FACTORS.get(karat, 1.0),
                "fine_wt": round(scrap_wt * TOUCH_FACTORS.get(karat, 1.0), 3),
            },
        )
    row.remarks = f"Auto-synced from Job Card {doc.name}"
    _save_or_insert(row)


def _upsert_stone_ledger_entry(doc, posting_date):
    stone_in = int(getattr(doc, "stone_in", 0) or 0)
    stone_set = int(getattr(doc, "stone_set", 0) or 0)
    stone_broken = int(getattr(doc, "stone_broken", 0) or 0)
    if stone_in <= 0 and stone_set <= 0 and stone_broken <= 0:
        _delete_linked_entries("Stone Ledger Entry", doc)
        return

    stone_master = _resolve_stone_master()
    if not stone_master:
        frappe.logger().warning(
            f"[loupe24k] Skipping Stone Ledger Entry sync for Job Card {doc.name}: "
            "no Stone Master available."
        )
        return

    row = _get_or_create_linked_entry("Stone Ledger Entry", doc)
    row.voucher_type = "Job Card"
    row.voucher_no = doc.name
    row.movement_type = "Set"
    row.posting_date = posting_date
    row.stone_master = stone_master
    row.pieces = max(stone_set, stone_in)
    row.carat = 0
    row.remarks = (
        f"Auto-synced from Job Card {doc.name} "
        f"(stone_in={stone_in}, stone_set={stone_set}, stone_broken={stone_broken})"
    )
    _save_or_insert(row)


def _resolve_stone_master():
    return frappe.db.get_value("Stone Master", {}, "name")


def _get_or_create_linked_entry(doctype, job_card):
    existing_name = frappe.db.get_value(
        doctype,
        {
            "voucher_type": "Job Card",
            "voucher_no": job_card.name,
            "docstatus": ["!=", 2],
        },
        "name",
    )
    if existing_name:
        return frappe.get_doc(doctype, existing_name)

    return frappe.get_doc(
        {
            "doctype": doctype,
            "voucher_type": "Job Card",
            "voucher_no": job_card.name,
        }
    )


def _save_or_insert(row):
    if row.is_new():
        row.insert(ignore_permissions=True)
    else:
        row.save(ignore_permissions=True)


def _delete_linked_entries(doctype, job_card):
    names = frappe.get_all(
        doctype,
        filters={
            "voucher_type": "Job Card",
            "voucher_no": job_card.name,
            "docstatus": ["!=", 2],
        },
        pluck="name",
    )
    for name in names:
        row = frappe.get_doc(doctype, name)
        if row.docstatus == 1:
            row.cancel()
        frappe.delete_doc(doctype, name, ignore_permissions=True, force=1)


def _cleanup_linked_entries(job_card):
    for doctype in LINKED_DOCTYPES:
        _delete_linked_entries(doctype, job_card)
