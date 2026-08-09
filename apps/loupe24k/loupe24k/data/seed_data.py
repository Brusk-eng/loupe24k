import frappe


# Seed company used when the ERPNext setup wizard never ran.
_COMPANY_NAME = "Loupe 24K"
_COMPANY_ABBR = "L24K"
_COMPANY_COUNTRY = "India"
_COMPANY_CURRENCY = "INR"


# ── Root-node helpers ─────────────────────────────────────────────────────────

# ERPNext NestedSet roots created by the setup wizard. Seed recreates them
# when the wizard never ran (fresh site with only `bench install-app`).
_TREE_ROOTS = {
    "Item Group": ("item_group_name", "parent_item_group", "All Item Groups"),
    "Supplier Group": ("supplier_group_name", "parent_supplier_group", "All Supplier Groups"),
    "Customer Group": ("customer_group_name", "parent_customer_group", "All Customer Groups"),
    "Territory": ("territory_name", "parent_territory", "All Territories"),
    "Warehouse": ("warehouse_name", "parent_warehouse", "All Warehouses"),
}


def _ensure_tree_root(doctype, company=None):
    """Return the NestedSet root, creating ERPNext's default if it is missing."""
    name_field, parent_field, fallback = _TREE_ROOTS[doctype]
    existing = frappe.db.get_value(doctype, {parent_field: ""}, "name")
    if existing:
        return existing

    root_name = fallback
    if doctype == "Warehouse":
        abbr = frappe.get_cached_value("Company", company, "abbr")
        root_name = f"{fallback} - {abbr}"

    if frappe.db.exists(doctype, root_name):
        return root_name

    payload = {
        "doctype": doctype,
        name_field: fallback,
        "is_group": 1,
        parent_field: "",
    }
    if doctype == "Warehouse":
        payload["company"] = company

    frappe.get_doc(payload).insert(ignore_permissions=True, ignore_mandatory=True)
    return frappe.db.get_value(doctype, {parent_field: ""}, "name") or root_name


def _ensure_tree_leaf(doctype, name, parent):
    """Create a non-group child under `parent` if it does not exist."""
    name_field, parent_field, _fallback = _TREE_ROOTS[doctype]
    if not frappe.db.exists(doctype, name):
        frappe.get_doc({
            "doctype": doctype,
            name_field: name,
            "is_group": 0,
            parent_field: parent,
        }).insert(ignore_permissions=True)
    return name


def seed():
    """Seed master data for Loupe 24K jewellery app. Idempotent — safe to re-run."""
    company = _ensure_company()
    frappe.db.commit()
    frappe.logger().info(f"[loupe24k seed] Company ready: {company}")

    _seed_uoms()
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] UOMs done")

    _seed_item_groups()
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] Item Groups done")

    _seed_item_attributes()
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] Item Attributes done")

    _seed_warehouses(company)
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] Warehouses done")

    _configure_stock_settings(company)
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] Stock Settings done")

    _seed_workstations()
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] Workstations done")

    _seed_operations()
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] Operations done")

    _seed_items(company)
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] Items done")

    _seed_stone_masters()
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] Stone Masters done")

    _seed_stone_lots()
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] Stone Lots done")

    _seed_suppliers()
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] Suppliers done")

    _seed_customers()
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] Customers done")

    _seed_metal_rates()
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] Metal Rates done")

    _seed_workspace()
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] Workspace done")

    frappe.logger().info("[loupe24k seed] All seed data complete.")


# ── Company / Fiscal Year / Settings ──────────────────────────────────────────

def _ensure_company():
    """Return the default company, creating Loupe 24K if the site has none."""
    _ensure_warehouse_types()

    company = frappe.defaults.get_global_default("company")
    if company and frappe.db.exists("Company", company):
        _ensure_fiscal_year()
        return company

    existing = (frappe.get_all("Company", pluck="name", limit=1) or [None])[0]
    if existing:
        _set_global_defaults(existing)
        _ensure_fiscal_year()
        return existing

    if frappe.db.exists("Currency", _COMPANY_CURRENCY):
        frappe.db.set_value("Currency", _COMPANY_CURRENCY, "enabled", 1)

    frappe.get_doc({
        "doctype": "Company",
        "company_name": _COMPANY_NAME,
        "abbr": _COMPANY_ABBR,
        "default_currency": _COMPANY_CURRENCY,
        "country": _COMPANY_COUNTRY,
        "create_chart_of_accounts_based_on": "Standard Template",
        "chart_of_accounts": "Standard",
        "enable_perpetual_inventory": 1,
        "valuation_method": "Moving Average",
    }).insert(ignore_permissions=True)

    _set_global_defaults(_COMPANY_NAME)
    _ensure_fiscal_year()
    _configure_party_settings()
    return _COMPANY_NAME


def _ensure_warehouse_types():
    """ERPNext Company.on_update creates Goods In Transit with type Transit."""
    if not frappe.db.exists("Warehouse Type", "Transit"):
        frappe.get_doc({
            "doctype": "Warehouse Type",
            "name": "Transit",
        }).insert(ignore_permissions=True)


def _set_global_defaults(company):
    gd = frappe.get_single("Global Defaults")
    gd.default_company = company
    gd.default_currency = _COMPANY_CURRENCY
    gd.country = _COMPANY_COUNTRY
    gd.flags.ignore_permissions = True
    gd.save()
    frappe.defaults.set_global_default("company", company)
    frappe.clear_cache()


def _ensure_fiscal_year():
    """Create the current Indian FY (Apr–Mar) if no FY covers today."""
    today = frappe.utils.today()
    if frappe.db.exists(
        "Fiscal Year",
        {"year_start_date": ["<=", today], "year_end_date": [">=", today]},
    ):
        return

    today_date = frappe.utils.getdate(today)
    start_year = today_date.year - 1 if today_date.month < 4 else today_date.year
    year_name = f"{start_year}-{start_year + 1}"
    if frappe.db.exists("Fiscal Year", year_name):
        return

    frappe.get_doc({
        "doctype": "Fiscal Year",
        "year": year_name,
        "year_start_date": f"{start_year}-04-01",
        "year_end_date": f"{start_year + 1}-03-31",
    }).insert(ignore_permissions=True)


def _configure_party_settings():
    selling = frappe.get_single("Selling Settings")
    if selling.cust_master_name != "Customer Name":
        selling.cust_master_name = "Customer Name"
        selling.flags.ignore_permissions = True
        selling.save()

    buying = frappe.get_single("Buying Settings")
    if buying.supp_master_name != "Supplier Name":
        buying.supp_master_name = "Supplier Name"
        buying.flags.ignore_permissions = True
        buying.save()


def _configure_stock_settings(company):
    abbr = frappe.get_cached_value("Company", company, "abbr")
    vault = f"Vault - {abbr}"
    default_wh = vault if frappe.db.exists("Warehouse", vault) else frappe.db.get_value(
        "Warehouse", {"warehouse_name": "Stores", "company": company},
    )

    ss = frappe.get_single("Stock Settings")
    changed = False
    if not ss.item_naming_by:
        ss.item_naming_by = "Item Code"
        changed = True
    if not ss.valuation_method:
        ss.valuation_method = "Moving Average"
        changed = True
    if not ss.default_warehouse and default_wh:
        ss.default_warehouse = default_wh
        changed = True
    if not ss.stock_uom and frappe.db.exists("UOM", "Gram"):
        ss.stock_uom = "Gram"
        changed = True
    if changed:
        ss.flags.ignore_permissions = True
        ss.save()


# ── UOMs ──────────────────────────────────────────────────────────────────────

def _seed_uoms():
    uoms = [
        {"uom_name": "Gram", "must_be_whole_number": 0, "conversion_factor": 1},
        {"uom_name": "Milligram", "must_be_whole_number": 0, "conversion_factor": 0.001},
        {"uom_name": "Carat", "must_be_whole_number": 0, "conversion_factor": 0.2},
        {"uom_name": "Piece", "must_be_whole_number": 1, "conversion_factor": 1},
        {"uom_name": "Cent", "must_be_whole_number": 0, "conversion_factor": 0.002},
    ]
    for uom in uoms:
        if not frappe.db.exists("UOM", uom["uom_name"]):
            doc = frappe.get_doc({"doctype": "UOM", **uom})
            doc.insert(ignore_permissions=True)


# ── Item Groups ───────────────────────────────────────────────────────────────

def _seed_item_groups():
    groups = [
        "Raw Metal",
        "WIP-Metal",
        "Finished Jewellery",
        "Stones",
        "Recoverable Scrap",
        "Refinable Scrap",
        "Consumables",
    ]
    root_group = _ensure_tree_root("Item Group")
    for group in groups:
        if not frappe.db.exists("Item Group", group):
            doc = frappe.get_doc({
                "doctype": "Item Group",
                "item_group_name": group,
                "parent_item_group": root_group,
            })
            doc.insert(ignore_permissions=True)


# ── Item Attributes ───────────────────────────────────────────────────────────

def _seed_item_attributes():
    attributes = [
        {
            "attribute_name": "Karat",
            "values": ["24K", "22K", "18K"],
        },
        {
            "attribute_name": "Ring Design",
            "values": ["Plain Band", "Solitaire", "Cluster", "Eternity", "Bangle"],
        },
        {
            "attribute_name": "Ring Size",
            "values": ["6", "7", "8", "9", "10", "11", "12"],
        },
        {
            "attribute_name": "Stone Shape",
            "values": ["Round", "Princess", "Oval", "Marquise", "Cushion"],
        },
        {
            "attribute_name": "Stone Quality",
            "values": ["FL", "VVS1", "VVS2", "VS1", "VS2", "SI1"],
        },
    ]
    for attr in attributes:
        if not frappe.db.exists("Item Attribute", attr["attribute_name"]):
            doc = frappe.get_doc({
                "doctype": "Item Attribute",
                "attribute_name": attr["attribute_name"],
                "item_attribute_values": [
                    {"attribute_value": v, "abbr": v}
                    for v in attr["values"]
                ],
            })
            doc.insert(ignore_permissions=True)


# ── Warehouses ────────────────────────────────────────────────────────────────

def _seed_warehouses(company):
    warehouses = [
        "Vault",
        "WIP - Casting",
        "WIP - Filing",
        "WIP - Polishing",
        "WIP - Setting",
        "Karigar - Ramesh",
        "Karigar - Suresh",
        "Hallmarking",
        "Finished Goods",
        "Stone Store",
        "Scrap Store",
    ]
    root_warehouse = _ensure_tree_root("Warehouse", company=company)
    for wh_name in warehouses:
        wh_full = f"{wh_name} - {frappe.get_cached_value('Company', company, 'abbr')}"
        if not frappe.db.exists("Warehouse", wh_full):
            doc = frappe.get_doc({
                "doctype": "Warehouse",
                "warehouse_name": wh_name,
                "parent_warehouse": root_warehouse,
                "company": company,
            })
            doc.insert(ignore_permissions=True)


# ── Workstations ──────────────────────────────────────────────────────────────

def _seed_workstations():
    workstations = [
        "Melting Furnace",
        "Casting Station",
        "Filing Bench",
        "Polishing Wheel",
        "Stone Setting Bench",
        "QC Bench",
        "Hallmarking Station",
    ]
    for ws in workstations:
        if not frappe.db.exists("Workstation", ws):
            doc = frappe.get_doc({
                "doctype": "Workstation",
                "workstation_name": ws,
            })
            doc.insert(ignore_permissions=True)


# ── Operations ────────────────────────────────────────────────────────────────

def _seed_operations():
    operations = [
        {"operation": "Alloying", "workstation": "Melting Furnace"},
        {"operation": "Casting", "workstation": "Casting Station"},
        {"operation": "Filing", "workstation": "Filing Bench"},
        {"operation": "Polishing", "workstation": "Polishing Wheel"},
        {"operation": "Stone Setting", "workstation": "Stone Setting Bench"},
        {"operation": "QC Inspection", "workstation": "QC Bench"},
        {"operation": "Hallmarking", "workstation": "Hallmarking Station"},
    ]
    for op in operations:
        if not frappe.db.exists("Operation", op["operation"]):
            doc = frappe.get_doc({
                "doctype": "Operation",
                "name": op["operation"],
                "workstation": op["workstation"],
            })
            doc.insert(ignore_permissions=True)


# ── Items ─────────────────────────────────────────────────────────────────────

def _seed_items(company):
    items = [
        {
            "item_code": "Pure Gold 24K",
            "item_name": "Pure Gold 24K",
            "item_group": "Raw Metal",
            "stock_uom": "Gram",
            "valuation_method": "Moving Average",
            "karat": "24K",
            "metal_type": "Gold",
            "touch": 1.0,
        },
        {
            "item_code": "Silver Alloy",
            "item_name": "Silver Alloy",
            "item_group": "Raw Metal",
            "stock_uom": "Gram",
            "valuation_method": "Moving Average",
            "metal_type": "Alloy",
        },
        {
            "item_code": "22K Gold Grain",
            "item_name": "22K Gold Grain",
            "item_group": "WIP-Metal",
            "stock_uom": "Gram",
            "valuation_method": "Moving Average",
            "karat": "22K",
            "metal_type": "Gold",
            "touch": 0.9167,
        },
        {
            "item_code": "Ring Blank 22K",
            "item_name": "Ring Blank 22K",
            "item_group": "WIP-Metal",
            "stock_uom": "Gram",
            "valuation_method": "Moving Average",
            "karat": "22K",
        },
        {
            "item_code": "Ring - Plain Band 22K",
            "item_name": "Ring - Plain Band 22K",
            "item_group": "Finished Jewellery",
            "stock_uom": "Gram",
            "valuation_method": "Moving Average",
            "karat": "22K",
        },
        {
            "item_code": "Ring - Solitaire 22K",
            "item_name": "Ring - Solitaire 22K",
            "item_group": "Finished Jewellery",
            "stock_uom": "Gram",
            "valuation_method": "Moving Average",
            "karat": "22K",
        },
        {
            "item_code": "Ring - Plain Band 24K",
            "item_name": "Ring - Plain Band 24K",
            "item_group": "Finished Jewellery",
            "stock_uom": "Gram",
            "valuation_method": "Moving Average",
            "karat": "24K",
        },
        {
            "item_code": "Sprue/Button Scrap 22K",
            "item_name": "Sprue/Button Scrap 22K",
            "item_group": "Recoverable Scrap",
            "stock_uom": "Gram",
            "valuation_method": "Moving Average",
            "karat": "22K",
        },
        {
            "item_code": "Filing Scrap 22K",
            "item_name": "Filing Scrap 22K",
            "item_group": "Recoverable Scrap",
            "stock_uom": "Gram",
            "valuation_method": "Moving Average",
            "karat": "22K",
        },
        {
            "item_code": "Polishing Dust 22K",
            "item_name": "Polishing Dust 22K",
            "item_group": "Refinable Scrap",
            "stock_uom": "Gram",
            "valuation_method": "Moving Average",
            "karat": "22K",
        },
        {
            "item_code": "Borax Flux",
            "item_name": "Borax Flux",
            "item_group": "Consumables",
            "stock_uom": "Gram",
            "valuation_method": "Moving Average",
        },
    ]

    # Custom fields that may not be present yet — use db_set after insert
    custom_fields = {"karat", "metal_type", "touch"}
    abbr = frappe.get_cached_value("Company", company, "abbr")
    default_wh = f"Vault - {abbr}"
    if not frappe.db.exists("Warehouse", default_wh):
        default_wh = frappe.db.get_value(
            "Warehouse", {"warehouse_name": "Stores", "company": company},
        )

    for item_data in items:
        if not frappe.db.exists("Item", item_data["item_code"]):
            payload = dict(item_data)
            custom_vals = {k: payload.pop(k) for k in custom_fields if k in payload}
            if default_wh:
                payload["item_defaults"] = [
                    {"company": company, "default_warehouse": default_wh},
                ]
            doc = frappe.get_doc({"doctype": "Item", **payload})
            doc.insert(ignore_permissions=True)
            # Set custom fields via db_set to avoid validation issues
            for field, val in custom_vals.items():
                try:
                    doc.db_set(field, val)
                except Exception:
                    pass


# ── Stone Masters ─────────────────────────────────────────────────────────────

def _seed_stone_masters():
    stones = [
        {
            "stone_name": "Round Diamond",
            "stone_type": "Diamond",
            "shape": "Round",
            "tracking_type": "Lot",
        },
        {
            "stone_name": "Certified Solitaire Diamond",
            "stone_type": "Diamond",
            "shape": "Round",
            "tracking_type": "Serial",
        },
    ]
    for stone in stones:
        if not frappe.db.exists("Stone Master", stone["stone_name"]):
            doc = frappe.get_doc({"doctype": "Stone Master", **stone})
            doc.insert(ignore_permissions=True)


# ── Stone Lots ────────────────────────────────────────────────────────────────

def _seed_stone_lots():
    lots = [
        {
            "lot_name": "MELEE-001",
            "stone_master": "Round Diamond",
            "tracking_type": "Lot",
            "total_pieces": 30,
            "total_carat": 0.75,
            "rate_per_ct": 15000,
        },
        {
            "lot_name": "SOL-001",
            "stone_master": "Certified Solitaire Diamond",
            "tracking_type": "Serial",
            "total_pieces": 1,
            "total_carat": 0.30,
            "cert_no": "GIA-123456",
            "cert_lab": "GIA",
            "rate_per_ct": 80000,
        },
    ]
    for lot in lots:
        if not frappe.db.exists("Stone Lot", {"lot_name": lot["lot_name"]}):
            doc = frappe.get_doc({"doctype": "Stone Lot", **lot})
            doc.insert(ignore_permissions=True)


# ── Suppliers ─────────────────────────────────────────────────────────────────

def _seed_suppliers():
    suppliers = [
        {"supplier_name": "Ramesh Karigar", "is_karigar": 1, "wastage_allowance_pct": 2.0, "making_rate": 350},
        {"supplier_name": "Suresh Setter",  "is_karigar": 1, "breakage_allowance_pct": 5.0, "making_rate": 500},
        {"supplier_name": "Anand Refinery",      "is_karigar": 0},
        {"supplier_name": "BIS Hallmark Centre", "is_karigar": 0},
        {"supplier_name": "Mumbai Bullion House", "is_karigar": 0},
    ]

    custom_fields = {"is_karigar", "wastage_allowance_pct", "making_rate", "breakage_allowance_pct"}
    root_supplier_group = _ensure_tree_root("Supplier Group")

    for supplier_data in suppliers:
        supplier_data["supplier_group"] = root_supplier_group
        if not frappe.db.exists("Supplier", supplier_data["supplier_name"]):
            custom_vals = {k: supplier_data.pop(k) for k in custom_fields if k in supplier_data}
            doc = frappe.get_doc({"doctype": "Supplier", **supplier_data})
            doc.insert(ignore_permissions=True)
            for field, val in custom_vals.items():
                try:
                    doc.db_set(field, val)
                except Exception:
                    pass


# ── Customers ─────────────────────────────────────────────────────────────────

def _seed_customers():
    customers = [
        {"customer_name": "Rajwadi Jewellers"},
    ]
    root_customer_group = _ensure_tree_root("Customer Group")
    root_territory = _ensure_tree_root("Territory")
    # Customer.validate rejects group-type Customer Group / Territory
    customer_group = _ensure_tree_leaf("Customer Group", "Commercial", root_customer_group)
    territory = _ensure_tree_leaf("Territory", "Rest Of The World", root_territory)

    for cust in customers:
        cust["customer_group"] = customer_group
        cust["territory"] = territory
        if not frappe.db.exists("Customer", cust["customer_name"]):
            doc = frappe.get_doc({"doctype": "Customer", **cust})
            doc.insert(ignore_permissions=True)


# ── Metal Rates ───────────────────────────────────────────────────────────────

def _seed_metal_rates():
    today = frappe.utils.today()
    if not frappe.db.exists("Metal Rate", {"date": today, "karat": "24K"}):
        doc = frappe.get_doc({
            "doctype": "Metal Rate",
            "date": today,
            "karat": "24K",
            "rate_per_g": 6200,
        })
        doc.insert(ignore_permissions=True)


# ── Workspace ─────────────────────────────────────────────────────────────────

def _seed_workspace():
    """Create (or replace) the Loupe 24K workspace with all standalone DocTypes."""
    import json as _json
    ws_label = "Loupe 24K"

    # Delete stale copy so re-runs always reflect the latest layout.
    # Workspace.autoname = field:label, so name == label.
    if frappe.db.exists("Workspace", ws_label):
        frappe.delete_doc("Workspace", ws_label, ignore_permissions=True, force=True)

    shortcuts = [
        {"type": "DocType", "label": "Metal Rate",             "link_to": "Metal Rate",             "color": "#FFB300"},
        {"type": "DocType", "label": "Karigar Metal Issue",    "link_to": "Karigar Metal Issue",    "color": "#FF7043"},
        {"type": "DocType", "label": "Karigar Reconciliation", "link_to": "Karigar Reconciliation", "color": "#7E57C2"},
        {"type": "DocType", "label": "Stone Lot",              "link_to": "Stone Lot",              "color": "#26A69A"},
    ]

    links = [
        # ── Masters card ──────────────────────────────────────────────────────
        {"type": "Card Break", "label": "Masters"},
        {"type": "Link", "label": "Metal Rate",   "link_to": "Metal Rate",   "link_type": "DocType", "onboard": 1},
        {"type": "Link", "label": "Stone Master", "link_to": "Stone Master", "link_type": "DocType", "onboard": 1},
        {"type": "Link", "label": "Stone Lot",    "link_to": "Stone Lot",    "link_type": "DocType", "onboard": 1},

        # ── Karigar Operations card ───────────────────────────────────────────
        {"type": "Card Break", "label": "Karigar Operations"},
        {"type": "Link", "label": "Karigar Metal Issue",    "link_to": "Karigar Metal Issue",    "link_type": "DocType", "onboard": 1},
        {"type": "Link", "label": "Karigar Reconciliation", "link_to": "Karigar Reconciliation", "link_type": "DocType", "onboard": 1},

        # ── Scrap & Hallmarking card ──────────────────────────────────────────
        {"type": "Card Break", "label": "Scrap & Hallmarking"},
        {"type": "Link", "label": "Scrap Recovery Entry", "link_to": "Scrap Recovery Entry", "link_type": "DocType", "onboard": 1},
        {"type": "Link", "label": "Hallmarking Register", "link_to": "Hallmarking Register", "link_type": "DocType", "onboard": 1},

        # ── Ledgers card ──────────────────────────────────────────────────────
        {"type": "Card Break", "label": "Ledgers"},
        {"type": "Link", "label": "Stone Ledger Entry",     "link_to": "Stone Ledger Entry",     "link_type": "DocType", "onboard": 0},
        {"type": "Link", "label": "Fine Gold Ledger Entry", "link_to": "Fine Gold Ledger Entry", "link_type": "DocType", "onboard": 0},
    ]

    # content tells Frappe v15 how to lay out the cards on the workspace page.
    # Each entry's card_name must match the label of a Card Break entry in links.
    content = _json.dumps([
        {"id": "l24k-masters",     "type": "card", "data": {"card_name": "Masters",             "col": 4}},
        {"id": "l24k-karigar-ops", "type": "card", "data": {"card_name": "Karigar Operations",  "col": 4}},
        {"id": "l24k-scrap-hall",  "type": "card", "data": {"card_name": "Scrap & Hallmarking", "col": 4}},
        {"id": "l24k-ledgers",     "type": "card", "data": {"card_name": "Ledgers",             "col": 4}},
    ])

    doc = frappe.get_doc({
        "doctype": "Workspace",
        "label": ws_label,
        "title": ws_label,
        "module": "Loupe 24K",
        "icon": "💎",
        "is_standard": 0,
        "public": 1,
        "content": content,
        "shortcuts": shortcuts,
        "links": links,
    })
    doc.insert(ignore_permissions=True)
