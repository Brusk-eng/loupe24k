import frappe


def after_install():
    _create_custom_fields()
    _hide_other_workspaces()


def after_migrate():
    _create_custom_fields()
    _hide_other_workspaces()


def _hide_other_workspaces():
    """Hide all standard ERPNext workspaces so only Loupe 24K is visible."""
    others = frappe.get_all(
        "Workspace",
        filters={"name": ["!=", "Loupe 24K"]},
        pluck="name",
    )
    for ws in others:
        frappe.db.set_value("Workspace", ws, "is_hidden", 1)
    if others:
        frappe.db.commit()


def _create_custom_fields():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    create_custom_fields(CUSTOM_FIELDS, ignore_validate=True)


CUSTOM_FIELDS = {
    "Item": [
        {
            "fieldname": "loupe_section",
            "fieldtype": "Section Break",
            "label": "Jewellery Details",
            "insert_after": "last_purchase_rate",
        },
        {
            "fieldname": "metal_type",
            "fieldtype": "Select",
            "label": "Metal Type",
            "options": "\nGold\nSilver\nPlatinum\nAlloy",
            "insert_after": "loupe_section",
        },
        {
            "fieldname": "karat",
            "fieldtype": "Select",
            "label": "Karat",
            "options": "\n24K\n22K\n18K",
            "insert_after": "metal_type",
        },
        {
            "fieldname": "touch",
            "fieldtype": "Float",
            "label": "Touch Factor",
            "precision": "4",
            "read_only": 1,
            "insert_after": "karat",
        },
        {
            "fieldname": "loupe_col_break_1",
            "fieldtype": "Column Break",
            "insert_after": "touch",
        },
        {
            "fieldname": "is_stone",
            "fieldtype": "Check",
            "label": "Is Stone Item",
            "insert_after": "loupe_col_break_1",
        },
        {
            "fieldname": "carat_wt",
            "fieldtype": "Float",
            "label": "Carat Weight",
            "precision": "3",
            "insert_after": "is_stone",
            "depends_on": "eval:doc.is_stone",
        },
        {
            "fieldname": "cert_no",
            "fieldtype": "Data",
            "label": "Certificate No",
            "insert_after": "carat_wt",
            "depends_on": "eval:doc.is_stone",
        },
        {
            "fieldname": "fine_wt",
            "fieldtype": "Float",
            "label": "Fine Weight (g)",
            "precision": "3",
            "read_only": 1,
            "insert_after": "cert_no",
            "description": "Auto-calculated: gross weight \u00d7 touch",
        },
    ],
    "BOM": [
        {
            "fieldname": "loupe_section",
            "fieldtype": "Section Break",
            "label": "Jewellery Details",
            "insert_after": "with_operations",
        },
        {
            "fieldname": "target_touch",
            "fieldtype": "Select",
            "label": "Target Karat / Touch",
            "options": "\n24K\n22K\n18K",
            "insert_after": "loupe_section",
        },
        {
            "fieldname": "wastage_pct",
            "fieldtype": "Float",
            "label": "Wastage %",
            "precision": "2",
            "insert_after": "target_touch",
        },
        {
            "fieldname": "loupe_col_1",
            "fieldtype": "Column Break",
            "insert_after": "wastage_pct",
        },
        {
            "fieldname": "expected_setting_loss_pct",
            "fieldtype": "Float",
            "label": "Expected Stone Setting Loss %",
            "precision": "2",
            "insert_after": "loupe_col_1",
        },
        {
            "fieldname": "scrap_by_products",
            "fieldtype": "Small Text",
            "label": "Scrap By-products Notes",
            "insert_after": "expected_setting_loss_pct",
        },
    ],
    "Work Order": [
        {
            "fieldname": "loupe_section",
            "fieldtype": "Section Break",
            "label": "Metal Details",
            "insert_after": "description",
        },
        {
            "fieldname": "karat",
            "fieldtype": "Select",
            "label": "Karat",
            "options": "\n24K\n22K\n18K",
            "insert_after": "loupe_section",
        },
        {
            "fieldname": "expected_metal_in",
            "fieldtype": "Float",
            "label": "Expected Metal In (g)",
            "precision": "3",
            "insert_after": "karat",
        },
        {
            "fieldname": "loupe_col_1",
            "fieldtype": "Column Break",
            "insert_after": "expected_metal_in",
        },
        {
            "fieldname": "expected_fine_gold",
            "fieldtype": "Float",
            "label": "Expected Fine Gold (g)",
            "precision": "3",
            "read_only": 1,
            "insert_after": "loupe_col_1",
        },
    ],
    "Stock Entry": [
        {
            "fieldname": "loupe_section",
            "fieldtype": "Section Break",
            "label": "Weight Tracking",
            "insert_after": "remarks",
        },
        {
            "fieldname": "weight_in",
            "fieldtype": "Float",
            "label": "Weight In (g)",
            "precision": "3",
            "insert_after": "loupe_section",
        },
        {
            "fieldname": "weight_out",
            "fieldtype": "Float",
            "label": "Weight Out (g)",
            "precision": "3",
            "insert_after": "weight_in",
        },
        {
            "fieldname": "loupe_col_1",
            "fieldtype": "Column Break",
            "insert_after": "weight_out",
        },
        {
            "fieldname": "scrap_wt",
            "fieldtype": "Float",
            "label": "Scrap Weight (g)",
            "precision": "3",
            "insert_after": "loupe_col_1",
        },
        {
            "fieldname": "loss_wt",
            "fieldtype": "Float",
            "label": "Loss Weight (g)",
            "precision": "3",
            "insert_after": "scrap_wt",
        },
        {
            "fieldname": "karigar",
            "fieldtype": "Link",
            "label": "Karigar / Setter",
            "options": "Supplier",
            "insert_after": "loss_wt",
        },
        {
            "fieldname": "loupe_stone_section",
            "fieldtype": "Section Break",
            "label": "Stone Tracking",
            "insert_after": "karigar",
        },
        {
            "fieldname": "stone_in",
            "fieldtype": "Int",
            "label": "Stones In (pieces)",
            "insert_after": "loupe_stone_section",
        },
        {
            "fieldname": "stone_set",
            "fieldtype": "Int",
            "label": "Stones Set (pieces)",
            "insert_after": "stone_in",
        },
        {
            "fieldname": "loupe_col_2",
            "fieldtype": "Column Break",
            "insert_after": "stone_set",
        },
        {
            "fieldname": "stone_broken",
            "fieldtype": "Int",
            "label": "Stones Broken (pieces)",
            "insert_after": "loupe_col_2",
        },
    ],
    "Job Card": [
        {
            "fieldname": "loupe_section",
            "fieldtype": "Section Break",
            "label": "Weight Tracking",
            "insert_after": "remarks",
        },
        {
            "fieldname": "weight_in",
            "fieldtype": "Float",
            "label": "Weight In (g)",
            "precision": "3",
            "insert_after": "loupe_section",
        },
        {
            "fieldname": "weight_out",
            "fieldtype": "Float",
            "label": "Weight Out (g)",
            "precision": "3",
            "insert_after": "weight_in",
        },
        {
            "fieldname": "loupe_col_1",
            "fieldtype": "Column Break",
            "insert_after": "weight_out",
        },
        {
            "fieldname": "scrap_wt",
            "fieldtype": "Float",
            "label": "Scrap Weight (g)",
            "precision": "3",
            "insert_after": "loupe_col_1",
        },
        {
            "fieldname": "loss_wt",
            "fieldtype": "Float",
            "label": "Loss Weight (g)",
            "precision": "3",
            "insert_after": "scrap_wt",
        },
        {
            "fieldname": "karigar",
            "fieldtype": "Link",
            "label": "Karigar / Setter",
            "options": "Supplier",
            "insert_after": "loss_wt",
        },
        {
            "fieldname": "loupe_stone_section",
            "fieldtype": "Section Break",
            "label": "Stone Tracking",
            "insert_after": "karigar",
        },
        {
            "fieldname": "stone_in",
            "fieldtype": "Int",
            "label": "Stones In (pieces)",
            "insert_after": "loupe_stone_section",
        },
        {
            "fieldname": "stone_set",
            "fieldtype": "Int",
            "label": "Stones Set (pieces)",
            "insert_after": "stone_in",
        },
        {
            "fieldname": "loupe_col_2",
            "fieldtype": "Column Break",
            "insert_after": "stone_set",
        },
        {
            "fieldname": "stone_broken",
            "fieldtype": "Int",
            "label": "Stones Broken (pieces)",
            "insert_after": "loupe_col_2",
        },
    ],
    "Serial No": [
        {
            "fieldname": "loupe_section",
            "fieldtype": "Section Break",
            "label": "Hallmarking",
            "insert_after": "description",
        },
        {
            "fieldname": "huid",
            "fieldtype": "Data",
            "label": "HUID",
            "insert_after": "loupe_section",
        },
        {
            "fieldname": "gross_wt",
            "fieldtype": "Float",
            "label": "Gross Weight (g)",
            "precision": "3",
            "insert_after": "huid",
        },
        {
            "fieldname": "loupe_col_1",
            "fieldtype": "Column Break",
            "insert_after": "gross_wt",
        },
        {
            "fieldname": "purity",
            "fieldtype": "Select",
            "label": "Purity",
            "options": "\n24K (999)\n22K (916)\n18K (750)",
            "insert_after": "loupe_col_1",
        },
        {
            "fieldname": "hallmark_date",
            "fieldtype": "Date",
            "label": "Hallmark Date",
            "insert_after": "purity",
        },
    ],
    "Quotation Item": [
        {
            "fieldname": "loupe_section",
            "fieldtype": "Section Break",
            "label": "Jewellery Pricing",
            "insert_after": "description",
        },
        {
            "fieldname": "metal_value",
            "fieldtype": "Currency",
            "label": "Metal Value",
            "insert_after": "loupe_section",
        },
        {
            "fieldname": "making_charge",
            "fieldtype": "Currency",
            "label": "Making Charge",
            "insert_after": "metal_value",
        },
        {
            "fieldname": "loupe_col_1",
            "fieldtype": "Column Break",
            "insert_after": "making_charge",
        },
        {
            "fieldname": "wastage_charge",
            "fieldtype": "Currency",
            "label": "Wastage Charge",
            "insert_after": "loupe_col_1",
        },
        {
            "fieldname": "stone_value",
            "fieldtype": "Currency",
            "label": "Stone Value",
            "insert_after": "wastage_charge",
        },
        {
            "fieldname": "old_gold_adjustment",
            "fieldtype": "Currency",
            "label": "Old Gold Adjustment (\u2013)",
            "insert_after": "stone_value",
        },
    ],
    "Sales Invoice Item": [
        {
            "fieldname": "loupe_section",
            "fieldtype": "Section Break",
            "label": "Jewellery Pricing",
            "insert_after": "description",
        },
        {
            "fieldname": "metal_value",
            "fieldtype": "Currency",
            "label": "Metal Value",
            "insert_after": "loupe_section",
        },
        {
            "fieldname": "making_charge",
            "fieldtype": "Currency",
            "label": "Making Charge",
            "insert_after": "metal_value",
        },
        {
            "fieldname": "loupe_col_1",
            "fieldtype": "Column Break",
            "insert_after": "making_charge",
        },
        {
            "fieldname": "wastage_charge",
            "fieldtype": "Currency",
            "label": "Wastage Charge",
            "insert_after": "loupe_col_1",
        },
        {
            "fieldname": "stone_value",
            "fieldtype": "Currency",
            "label": "Stone Value",
            "insert_after": "wastage_charge",
        },
        {
            "fieldname": "old_gold_adjustment",
            "fieldtype": "Currency",
            "label": "Old Gold Adjustment (\u2013)",
            "insert_after": "stone_value",
        },
    ],
    "Supplier": [
        {
            "fieldname": "loupe_section",
            "fieldtype": "Section Break",
            "label": "Karigar / Setter Details",
            "insert_after": "supplier_details",
        },
        {
            "fieldname": "is_karigar",
            "fieldtype": "Check",
            "label": "Is Karigar / Setter",
            "insert_after": "loupe_section",
        },
        {
            "fieldname": "making_rate",
            "fieldtype": "Currency",
            "label": "Making Rate (per g)",
            "insert_after": "is_karigar",
            "depends_on": "eval:doc.is_karigar",
        },
        {
            "fieldname": "loupe_col_1",
            "fieldtype": "Column Break",
            "insert_after": "making_rate",
        },
        {
            "fieldname": "wastage_allowance_pct",
            "fieldtype": "Float",
            "label": "Wastage Allowance %",
            "precision": "2",
            "insert_after": "loupe_col_1",
            "depends_on": "eval:doc.is_karigar",
        },
        {
            "fieldname": "breakage_allowance_pct",
            "fieldtype": "Float",
            "label": "Stone Breakage Allowance %",
            "precision": "2",
            "insert_after": "wastage_allowance_pct",
            "depends_on": "eval:doc.is_karigar",
        },
        {
            "fieldname": "current_metal_balance",
            "fieldtype": "Float",
            "label": "Current Metal Balance (g fine)",
            "precision": "3",
            "read_only": 1,
            "insert_after": "breakage_allowance_pct",
        },
    ],
}
