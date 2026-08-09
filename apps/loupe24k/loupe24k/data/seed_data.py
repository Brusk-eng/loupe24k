import frappe


# Seed company used when the ERPNext setup wizard never ran.
_COMPANY_NAME = "Loupe 24K"
_COMPANY_ABBR = "L24K"
_COMPANY_COUNTRY = "United States"
_COMPANY_CURRENCY = "USD"


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

    _seed_routings()
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] Routings done")

    _seed_items(company)
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] Items done")

    _seed_boms(company)
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] BOMs done")

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

    kmi_names = _seed_karigar_metal_issues()
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] Karigar Metal Issues done")

    _seed_karigar_reconciliations(kmi_names)
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] Karigar Reconciliations done")

    _seed_scrap_recovery_entries()
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] Scrap Recovery Entries done")

    _seed_fine_gold_ledger_entries()
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] Fine Gold Ledger Entries done")

    _seed_stone_ledger_entries()
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] Stone Ledger Entries done")

    _seed_hallmarking_entries()
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] Hallmarking Entries done")

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
    """Create the current US FY (Jan–Dec) if no FY covers today."""
    today = frappe.utils.today()
    if frappe.db.exists(
        "Fiscal Year",
        {"year_start_date": ["<=", today], "year_end_date": [">=", today]},
    ):
        return

    today_date = frappe.utils.getdate(today)
    year = today_date.year
    year_name = str(year)
    if frappe.db.exists("Fiscal Year", year_name):
        return

    frappe.get_doc({
        "doctype": "Fiscal Year",
        "year": year_name,
        "year_start_date": f"{year}-01-01",
        "year_end_date": f"{year}-12-31",
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


# ── Routings ──────────────────────────────────────────────────────────────────

def _seed_routings():
    """Create manufacturing routings (sequences of operations) for the jewellery workflow.

    Flow: raw gold → [Alloying] → 22K grain → [Casting] → ring blank → [Finishing] → finished ring
    """
    routings = [
        {
            "routing_name": "Alloying",
            "operations": [
                {"operation": "Alloying", "workstation": "Melting Furnace", "time_in_mins": 60},
            ],
        },
        {
            "routing_name": "Casting",
            "operations": [
                {"operation": "Casting", "workstation": "Casting Station", "time_in_mins": 45},
            ],
        },
        {
            "routing_name": "Jewellery Finishing",
            "operations": [
                {"operation": "Filing",        "workstation": "Filing Bench",        "time_in_mins": 30},
                {"operation": "Polishing",     "workstation": "Polishing Wheel",     "time_in_mins": 20},
                {"operation": "QC Inspection", "workstation": "QC Bench",            "time_in_mins": 15},
                {"operation": "Hallmarking",   "workstation": "Hallmarking Station", "time_in_mins": 10},
            ],
        },
        {
            "routing_name": "Stone Setting Finish",
            "operations": [
                {"operation": "Filing",        "workstation": "Filing Bench",        "time_in_mins": 30},
                {"operation": "Stone Setting", "workstation": "Stone Setting Bench", "time_in_mins": 60},
                {"operation": "Polishing",     "workstation": "Polishing Wheel",     "time_in_mins": 20},
                {"operation": "QC Inspection", "workstation": "QC Bench",            "time_in_mins": 15},
                {"operation": "Hallmarking",   "workstation": "Hallmarking Station", "time_in_mins": 10},
            ],
        },
        {
            # 24K rings skip the grain prep step — cast directly from pure gold
            "routing_name": "Cast & Finish",
            "operations": [
                {"operation": "Casting",       "workstation": "Casting Station",     "time_in_mins": 45},
                {"operation": "Filing",        "workstation": "Filing Bench",        "time_in_mins": 30},
                {"operation": "Polishing",     "workstation": "Polishing Wheel",     "time_in_mins": 20},
                {"operation": "QC Inspection", "workstation": "QC Bench",            "time_in_mins": 15},
                {"operation": "Hallmarking",   "workstation": "Hallmarking Station", "time_in_mins": 10},
            ],
        },
    ]

    for r in routings:
        if not frappe.db.exists("Routing", r["routing_name"]):
            doc = frappe.get_doc({
                "doctype": "Routing",
                "routing_name": r["routing_name"],
                "operations": [
                    {
                        "operation":    op["operation"],
                        "workstation":  op["workstation"],
                        "time_in_mins": op["time_in_mins"],
                        "hour_rate":    0,
                    }
                    for op in r["operations"]
                ],
            })
            doc.insert(ignore_permissions=True)


# ── BOMs ───────────────────────────────────────────────────────────────────────

def _seed_boms(company):
    """Create and submit default BOMs for manufactured items.

    Manufacturing chain:
      Pure Gold 24K + Silver Alloy → 22K Gold Grain (Alloying)
      22K Gold Grain                → Ring Blank 22K (Casting)
      Ring Blank 22K                → Ring - Plain Band 22K (Jewellery Finishing)
      Ring Blank 22K                → Ring - Solitaire 22K  (Stone Setting Finish)
      Pure Gold 24K                 → Ring - Plain Band 24K (Cast & Finish)
    """
    boms = [
        {
            # 100 g batch: 91.67 g pure gold + 8.33 g silver → 100 g 22K grain.
            # 0.5% melt loss assumed; wastage noted on BOM custom field.
            "item": "22K Gold Grain",
            "quantity": 100,
            "routing": "Alloying",
            "items": [
                {"item_code": "Pure Gold 24K", "qty": 91.67},
                {"item_code": "Silver Alloy",  "qty": 8.33},
                {"item_code": "Borax Flux",    "qty": 5.0},
            ],
            "custom": {
                "target_touch": "22K",
                "wastage_pct": 0.5,
            },
        },
        {
            # Single ring blank (~5 g).  Extra input covers casting sprue;
            # sprue is recovered as Sprue/Button Scrap 22K via Stock Entry.
            "item": "Ring Blank 22K",
            "quantity": 5,
            "routing": "Casting",
            "items": [
                {"item_code": "22K Gold Grain", "qty": 5.5},
                {"item_code": "Borax Flux",     "qty": 2.0},
            ],
            "custom": {
                "target_touch": "22K",
                "wastage_pct": 5.0,
                "scrap_by_products": "Sprue/Button Scrap 22K",
            },
        },
        {
            # Plain band: file and polish a blank down to finished weight.
            # Filing + polishing dust tracked as scrap on the Stock Entry.
            "item": "Ring - Plain Band 22K",
            "quantity": 4.5,
            "routing": "Jewellery Finishing",
            "items": [
                {"item_code": "Ring Blank 22K", "qty": 5.0},
            ],
            "custom": {
                "target_touch": "22K",
                "wastage_pct": 1.5,
                "scrap_by_products": "Filing Scrap 22K, Polishing Dust 22K",
            },
        },
        {
            # Solitaire ring: same blank, but stone setting added to the route.
            # expected_setting_loss_pct covers broken/lost melee during setting.
            "item": "Ring - Solitaire 22K",
            "quantity": 5,
            "routing": "Stone Setting Finish",
            "items": [
                {"item_code": "Ring Blank 22K", "qty": 5.0},
            ],
            "custom": {
                "target_touch": "22K",
                "wastage_pct": 1.5,
                "expected_setting_loss_pct": 2.0,
                "scrap_by_products": "Filing Scrap 22K, Polishing Dust 22K",
            },
        },
        {
            # 24K ring: cast directly from pure gold — no alloying step needed.
            "item": "Ring - Plain Band 24K",
            "quantity": 4,
            "routing": "Cast & Finish",
            "items": [
                {"item_code": "Pure Gold 24K", "qty": 4.5},
                {"item_code": "Borax Flux",    "qty": 2.0},
            ],
            "custom": {
                "target_touch": "24K",
                "wastage_pct": 2.0,
            },
        },
    ]

    for bom_data in boms:
        # Skip if any non-cancelled BOM already exists for this item
        if frappe.db.get_value("BOM", {"item": bom_data["item"], "docstatus": ["!=", 2]}, "name"):
            continue

        doc = frappe.get_doc({
            "doctype": "BOM",
            "item": bom_data["item"],
            "quantity": bom_data["quantity"],
            "uom": "Gram",
            "company": company,
            "is_default": 1,
            "is_active": 1,
            "with_operations": 1,
            "routing": bom_data["routing"],
            "items": [
                {
                    "item_code":  row["item_code"],
                    "qty":        row["qty"],
                    "uom":        "Gram",
                    "stock_uom":  "Gram",
                }
                for row in bom_data["items"]
            ],
        })
        doc.insert(ignore_permissions=True)

        for field, val in bom_data["custom"].items():
            try:
                doc.db_set(field, val)
            except Exception:
                pass

        try:
            doc.submit()
        except Exception as e:
            frappe.logger().warning(
                f"[loupe24k seed] BOM submit failed for {bom_data['item']}: {e}"
            )


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
            "rate_per_ct": 180,
        },
        {
            "lot_name": "SOL-001",
            "stone_master": "Certified Solitaire Diamond",
            "tracking_type": "Serial",
            "total_pieces": 1,
            "total_carat": 0.30,
            "cert_no": "GIA-123456",
            "cert_lab": "GIA",
            "rate_per_ct": 950,
        },
    ]
    for lot in lots:
        if not frappe.db.exists("Stone Lot", {"lot_name": lot["lot_name"]}):
            doc = frappe.get_doc({"doctype": "Stone Lot", **lot})
            doc.insert(ignore_permissions=True)


# ── Suppliers ─────────────────────────────────────────────────────────────────

def _seed_suppliers():
    suppliers = [
        {"supplier_name": "Ramesh Karigar", "is_karigar": 1, "wastage_allowance_pct": 2.0, "making_rate": 4},
        {"supplier_name": "Suresh Setter",  "is_karigar": 1, "breakage_allowance_pct": 5.0, "making_rate": 6},
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
            "rate_per_g": 100,
        })
        doc.insert(ignore_permissions=True)


# ── Transaction seed constants ────────────────────────────────────────────────

_SEED_REMARK = "[loupe24k-seed]"
_TOUCH = {"24K": 1.0000, "22K": 0.9167, "18K": 0.7500}


def _fine(gross_wt, karat):
    return round((gross_wt or 0) * _TOUCH.get(karat, 1.0), 3)


# ── Karigar Metal Issues ───────────────────────────────────────────────────────

def _seed_karigar_metal_issues():
    """Create and submit 5 Karigar Metal Issue challans covering each operation type.
    Returns a dict {challan_no: doc.name} for use by _seed_karigar_reconciliations().
    """
    today = frappe.utils.today()
    # Resolve stone lot names (autoname = SLOT-.YYYY.-.#####, not the lot_name)
    melee_lot = frappe.db.get_value("Stone Lot", {"lot_name": "MELEE-001"}, "name")
    sol_lot   = frappe.db.get_value("Stone Lot", {"lot_name": "SOL-001"},   "name")

    kmi_list = [
        {
            # Filing — ring blanks sent to Ramesh for filing
            "challan_no": "SEED/001",
            "karigar": "Ramesh Karigar",
            "dispatch_date": frappe.utils.add_months(today, -2),
            "operation": "Filing",
            "metal_items": [
                {"item_code": "Ring Blank 22K", "karat": "22K", "gross_wt": 50.0, "uom": "Gram"},
            ],
            "stone_items": [],
        },
        {
            # Setting — plain 22K rings + melee diamonds sent to Suresh for setting
            "challan_no": "SEED/002",
            "karigar": "Suresh Setter",
            "dispatch_date": frappe.utils.add_months(today, -2),
            "operation": "Setting",
            "metal_items": [
                {"item_code": "Ring - Plain Band 22K", "karat": "22K", "gross_wt": 45.0, "uom": "Gram"},
            ],
            "stone_items": [
                {"stone_master": "Round Diamond", "stone_lot": melee_lot,
                 "pieces": 20, "carat": 0.50, "rate_per_ct": 180},
            ] if melee_lot else [],
        },
        {
            # Casting — 22K grain sent to Ramesh for casting into ring blanks
            "challan_no": "SEED/003",
            "karigar": "Ramesh Karigar",
            "dispatch_date": frappe.utils.add_months(today, -3),
            "operation": "Casting",
            "metal_items": [
                {"item_code": "22K Gold Grain", "karat": "22K", "gross_wt": 100.0, "uom": "Gram"},
            ],
            "stone_items": [],
        },
        {
            # Polishing — 22K finished rings sent to Ramesh for polishing
            "challan_no": "SEED/004",
            "karigar": "Ramesh Karigar",
            "dispatch_date": frappe.utils.add_months(today, -1),
            "operation": "Polishing",
            "metal_items": [
                {"item_code": "Ring - Plain Band 22K", "karat": "22K", "gross_wt": 40.0, "uom": "Gram"},
            ],
            "stone_items": [],
        },
        {
            # Setting — 24K plain band + solitaire sent to Suresh for setting
            "challan_no": "SEED/005",
            "karigar": "Suresh Setter",
            "dispatch_date": frappe.utils.add_months(today, -1),
            "operation": "Setting",
            "metal_items": [
                {"item_code": "Ring - Plain Band 24K", "karat": "24K", "gross_wt": 20.0, "uom": "Gram"},
            ],
            "stone_items": [
                {"stone_master": "Certified Solitaire Diamond", "stone_lot": sol_lot,
                 "pieces": 1, "carat": 0.30, "rate_per_ct": 950},
            ] if sol_lot else [],
        },
    ]

    names = {}
    for kmi_def in kmi_list:
        existing = frappe.db.get_value(
            "Karigar Metal Issue", {"challan_no": kmi_def["challan_no"]}, "name"
        )
        if existing:
            names[kmi_def["challan_no"]] = existing
            continue

        doc = frappe.get_doc({
            "doctype": "Karigar Metal Issue",
            "challan_no": kmi_def["challan_no"],
            "karigar":    kmi_def["karigar"],
            "dispatch_date": kmi_def["dispatch_date"],
            "operation":  kmi_def["operation"],
            "remarks":    _SEED_REMARK,
            "metal_items": kmi_def["metal_items"],
            "stone_items": kmi_def["stone_items"],
        })
        doc.insert(ignore_permissions=True)
        try:
            doc.submit()
        except Exception as e:
            frappe.logger().warning(f"[loupe24k seed] KMI submit failed for {kmi_def['challan_no']}: {e}")
        names[kmi_def["challan_no"]] = doc.name

    return names


# ── Karigar Reconciliations ───────────────────────────────────────────────────

def _seed_karigar_reconciliations(kmi_names):
    """Settle all 5 seed KMIs, producing a mix of Pass / Warning / Fail verdicts.

    Verdict derivation (wastage_allowance_pct = 2% for both karigar):
      SEED/001 – Filing   Ramesh  – returned 48g + 1.0g scrap   → fine_loss 0.916 ≤ 0.917 → Pass
      SEED/002 – Setting  Suresh  – returned 43g + 1.5g scrap   → fine_loss 0.459 ≤ 0.825 → Pass
      SEED/003 – Casting  Ramesh  – returned 88.9g + 9.0g sprue → excess 0.090 ≤ 0.1      → Warning
      SEED/004 – Polishing Ramesh – returned 38.5g + 1.0g dust  → fine_loss 0.458 ≤ 0.733 → Pass
      SEED/005 – Setting  Suresh  – returned 18.5g 24K, 1 stone broken  → excess 1.1 > 0.1 → Fail
    """
    today = frappe.utils.today()

    krec_list = [
        {
            "challan_no": "SEED/001",
            "reconciliation_date": frappe.utils.add_months(today, -1),
            "returned_items": [
                {"item_code": "Ring - Plain Band 22K", "category": "Finished", "karat": "22K", "gross_wt": 48.0},
                {"item_code": "Filing Scrap 22K",      "category": "Scrap",    "karat": "22K", "gross_wt": 1.0},
            ],
            "stones_set": 0, "stones_returned": 0, "stones_broken": 0,
        },
        {
            "challan_no": "SEED/002",
            "reconciliation_date": frappe.utils.add_months(today, -1),
            "returned_items": [
                {"item_code": "Ring - Solitaire 22K", "category": "Finished", "karat": "22K", "gross_wt": 43.0},
                {"item_code": "Filing Scrap 22K",     "category": "Scrap",    "karat": "22K", "gross_wt": 1.5},
            ],
            "stones_set": 18, "stones_returned": 2, "stones_broken": 0,
        },
        {
            "challan_no": "SEED/003",
            "reconciliation_date": frappe.utils.add_months(today, -2),
            "returned_items": [
                {"item_code": "Ring Blank 22K",         "category": "Finished", "karat": "22K", "gross_wt": 88.9},
                {"item_code": "Sprue/Button Scrap 22K", "category": "Scrap",    "karat": "22K", "gross_wt": 9.0},
            ],
            "stones_set": 0, "stones_returned": 0, "stones_broken": 0,
        },
        {
            "challan_no": "SEED/004",
            "reconciliation_date": frappe.utils.add_days(today, -7),
            "returned_items": [
                {"item_code": "Ring - Plain Band 22K", "category": "Finished", "karat": "22K", "gross_wt": 38.5},
                {"item_code": "Polishing Dust 22K",    "category": "Scrap",    "karat": "22K", "gross_wt": 1.0},
            ],
            "stones_set": 0, "stones_returned": 0, "stones_broken": 0,
        },
        {
            # Fail: 1.5g fine loss on 20g 24K → excess 1.1g; 1 solitaire broken (0 allowed)
            "challan_no": "SEED/005",
            "reconciliation_date": frappe.utils.add_days(today, -14),
            "returned_items": [
                {"item_code": "Ring - Plain Band 24K", "category": "Finished", "karat": "24K", "gross_wt": 18.5},
            ],
            "stones_set": 1, "stones_returned": 0, "stones_broken": 1,
        },
    ]

    for krec_def in krec_list:
        issue_ref = kmi_names.get(krec_def["challan_no"])
        if not issue_ref:
            continue
        if frappe.db.get_value("Karigar Reconciliation", {"issue_ref": issue_ref}, "name"):
            continue

        doc = frappe.get_doc({
            "doctype": "Karigar Reconciliation",
            "issue_ref": issue_ref,
            "reconciliation_date": krec_def["reconciliation_date"],
            "remarks": _SEED_REMARK,
            "returned_items": krec_def["returned_items"],
            "stones_set":      krec_def["stones_set"],
            "stones_returned": krec_def["stones_returned"],
            "stones_broken":   krec_def["stones_broken"],
        })
        doc.insert(ignore_permissions=True)
        try:
            doc.submit()
        except Exception as e:
            frappe.logger().warning(f"[loupe24k seed] KREC submit failed for {issue_ref}: {e}")


# ── Scrap Recovery Entries ────────────────────────────────────────────────────

def _seed_scrap_recovery_entries():
    """Create 5 submitted Scrap Recovery Entries covering Remelt and Refining types."""
    if frappe.db.count("Scrap Recovery Entry",
                        {"remarks": _SEED_REMARK, "docstatus": ["!=", 2]}) >= 5:
        return

    today = frappe.utils.today()
    sre_list = [
        {
            "entry_date": frappe.utils.add_months(today, -3),
            "refiner": "Anand Refinery",
            "recovery_type": "Remelt",
            "scrap_items": [
                {"item_code": "Sprue/Button Scrap 22K", "scrap_type": "Sprue/Button",
                 "gross_wt": 8.0, "karat": "22K"},
            ],
            "recovery_pct": 95,
            "credit_posting": 1,
        },
        {
            "entry_date": frappe.utils.add_months(today, -2),
            "refiner": "Anand Refinery",
            "recovery_type": "Refining",
            "scrap_items": [
                {"item_code": "Filing Scrap 22K", "scrap_type": "Filing Scrap",
                 "gross_wt": 5.0, "karat": "22K"},
            ],
            "recovery_pct": 88,
            "credit_posting": 0,
        },
        {
            "entry_date": frappe.utils.add_months(today, -1),
            "refiner": "Anand Refinery",
            "recovery_type": "Remelt",
            "scrap_items": [
                {"item_code": "Sprue/Button Scrap 22K", "scrap_type": "Sprue/Button",
                 "gross_wt": 4.0, "karat": "22K"},
                {"item_code": "Filing Scrap 22K",       "scrap_type": "Filing Scrap",
                 "gross_wt": 2.0, "karat": "22K"},
            ],
            "recovery_pct": 95,
            "credit_posting": 1,
        },
        {
            "entry_date": frappe.utils.add_days(today, -21),
            "refiner": "Anand Refinery",
            "recovery_type": "Refining",
            "scrap_items": [
                {"item_code": "Polishing Dust 22K", "scrap_type": "Polishing Dust",
                 "gross_wt": 3.0, "karat": "22K"},
            ],
            "recovery_pct": 75,
            "credit_posting": 0,
        },
        {
            "entry_date": frappe.utils.add_days(today, -7),
            "refiner": "Anand Refinery",
            "recovery_type": "Remelt",
            "scrap_items": [
                {"item_code": "Sprue/Button Scrap 22K", "scrap_type": "Sprue/Button",
                 "gross_wt": 12.0, "karat": "22K"},
                {"item_code": "Filing Scrap 22K",       "scrap_type": "Filing Scrap",
                 "gross_wt": 4.5, "karat": "22K"},
                {"item_code": "Polishing Dust 22K",     "scrap_type": "Polishing Dust",
                 "gross_wt": 1.5, "karat": "22K"},
            ],
            "recovery_pct": 92,
            "credit_posting": 1,
        },
    ]

    for sre_def in sre_list:
        doc = frappe.get_doc({
            "doctype": "Scrap Recovery Entry",
            "entry_date":    sre_def["entry_date"],
            "refiner":       sre_def["refiner"],
            "recovery_type": sre_def["recovery_type"],
            "recovery_pct":  sre_def["recovery_pct"],
            "credit_posting": sre_def["credit_posting"],
            "remarks":       _SEED_REMARK,
            "scrap_items":   sre_def["scrap_items"],
        })
        doc.insert(ignore_permissions=True)
        try:
            doc.submit()
        except Exception as e:
            frappe.logger().warning(f"[loupe24k seed] SRE submit failed: {e}")


# ── Fine Gold Ledger Entries ──────────────────────────────────────────────────

def _seed_fine_gold_ledger_entries():
    """Create 5 submitted Fine Gold Ledger Entries covering all entry types."""
    if frappe.db.count("Fine Gold Ledger Entry",
                        {"remarks": _SEED_REMARK, "docstatus": ["!=", 2]}) >= 5:
        return

    today = frappe.utils.today()
    fgl_list = [
        {
            # Metal issued to karigar — corresponds to KMI-003 grain challan
            "entry_type": "Issue",
            "posting_date": frappe.utils.add_months(today, -3),
            "party_type": "Supplier", "party": "Ramesh Karigar",
            "item": "22K Gold Grain", "karat": "22K", "gross_wt": 100.0,
        },
        {
            # Ring blanks received back after casting (KREC-003 settlement)
            "entry_type": "Receipt",
            "posting_date": frappe.utils.add_months(today, -2),
            "party_type": "Supplier", "party": "Ramesh Karigar",
            "item": "Ring Blank 22K", "karat": "22K", "gross_wt": 88.9,
        },
        {
            # Casting sprue sent to refiner
            "entry_type": "Scrap",
            "posting_date": frappe.utils.add_months(today, -2),
            "party_type": "Supplier", "party": "Anand Refinery",
            "item": "Sprue/Button Scrap 22K", "karat": "22K", "gross_wt": 9.0,
        },
        {
            # Fine gold credited after refining recovery
            "entry_type": "Recovery",
            "posting_date": frappe.utils.add_months(today, -1),
            "party_type": "Supplier", "party": "Anand Refinery",
            "item": "Pure Gold 24K", "karat": "24K", "gross_wt": 7.5,
        },
        {
            # Unaccounted melt loss recorded
            "entry_type": "Loss",
            "posting_date": frappe.utils.add_days(today, -14),
            "item": "22K Gold Grain", "karat": "22K", "gross_wt": 0.5,
        },
    ]

    for fgl_def in fgl_list:
        doc = frappe.get_doc({
            "doctype": "Fine Gold Ledger Entry",
            "entry_type":   fgl_def["entry_type"],
            "posting_date": fgl_def["posting_date"],
            "party_type":   fgl_def.get("party_type", ""),
            "party":        fgl_def.get("party", ""),
            "item":         fgl_def["item"],
            "karat":        fgl_def["karat"],
            "gross_wt":     fgl_def["gross_wt"],
            "remarks":      _SEED_REMARK,
        })
        doc.insert(ignore_permissions=True)
        try:
            doc.submit()
        except Exception as e:
            frappe.logger().warning(f"[loupe24k seed] FGL submit failed ({fgl_def['entry_type']}): {e}")


# ── Stone Ledger Entries ──────────────────────────────────────────────────────

def _seed_stone_ledger_entries():
    """Create 5 submitted Stone Ledger Entries covering all movement types."""
    if frappe.db.count("Stone Ledger Entry",
                        {"remarks": _SEED_REMARK, "docstatus": ["!=", 2]}) >= 5:
        return

    today = frappe.utils.today()
    melee_lot = frappe.db.get_value("Stone Lot", {"lot_name": "MELEE-001"}, "name")
    sol_lot   = frappe.db.get_value("Stone Lot", {"lot_name": "SOL-001"},   "name")

    sle_list = [
        {
            # Melee diamonds issued to Suresh for setting (matches KMI-002)
            "movement_type": "Issue",
            "posting_date": frappe.utils.add_months(today, -2),
            "party_type": "Supplier", "party": "Suresh Setter",
            "stone_master": "Round Diamond", "stone_lot": melee_lot,
            "pieces": 20, "carat": 0.50, "value": round(0.50 * 180, 2),
        },
        {
            # 18 of those diamonds set into solitaire rings
            "movement_type": "Set",
            "posting_date": frappe.utils.add_months(today, -1),
            "stone_master": "Round Diamond",
            "pieces": 18, "carat": 0.45,
        },
        {
            # Remaining 2 diamonds returned unused
            "movement_type": "Return",
            "posting_date": frappe.utils.add_months(today, -1),
            "party_type": "Supplier", "party": "Suresh Setter",
            "stone_master": "Round Diamond", "stone_lot": melee_lot,
            "pieces": 2, "carat": 0.05, "value": round(0.05 * 180, 2),
        },
        {
            # Certified solitaire issued to Suresh (matches KMI-005)
            "movement_type": "Issue",
            "posting_date": frappe.utils.add_months(today, -1),
            "party_type": "Supplier", "party": "Suresh Setter",
            "stone_master": "Certified Solitaire Diamond", "stone_lot": sol_lot,
            "pieces": 1, "carat": 0.30, "value": round(0.30 * 950, 2),
        },
        {
            # 1 melee stone broken during setting (KREC-005 records this)
            "movement_type": "Broken",
            "posting_date": frappe.utils.add_days(today, -14),
            "stone_master": "Round Diamond",
            "pieces": 1, "carat": 0.025,
        },
    ]

    for sle_def in sle_list:
        doc = frappe.get_doc({
            "doctype": "Stone Ledger Entry",
            "movement_type": sle_def["movement_type"],
            "posting_date":  sle_def["posting_date"],
            "party_type":    sle_def.get("party_type", ""),
            "party":         sle_def.get("party", ""),
            "stone_master":  sle_def["stone_master"],
            "stone_lot":     sle_def.get("stone_lot") or "",
            "pieces":        sle_def["pieces"],
            "carat":         sle_def["carat"],
            "value":         sle_def.get("value", 0),
            "remarks":       _SEED_REMARK,
        })
        doc.insert(ignore_permissions=True)
        try:
            doc.submit()
        except Exception as e:
            frappe.logger().warning(
                f"[loupe24k seed] SLE submit failed ({sle_def['movement_type']}): {e}"
            )


# ── Hallmarking Register ──────────────────────────────────────────────────────

def _seed_hallmarking_entries():
    """Create 5 submitted Hallmarking Register entries for finished rings."""
    if frappe.db.count("Hallmarking Register",
                        {"remarks": _SEED_REMARK, "docstatus": ["!=", 2]}) >= 5:
        return

    today = frappe.utils.today()
    hmr_list = [
        {
            "hallmark_date": frappe.utils.add_days(today, -21),
            "bis_centre": "BIS Hallmark Centre",
            "item_code": "Ring - Plain Band 22K",
            "huid": "AA1001", "purity": "22K (916)",
            "gross_wt": 4.5, "stone_wt": None,
        },
        {
            "hallmark_date": frappe.utils.add_days(today, -21),
            "bis_centre": "BIS Hallmark Centre",
            "item_code": "Ring - Solitaire 22K",
            "huid": "AA1002", "purity": "22K (916)",
            "gross_wt": 5.2, "stone_wt": 0.15,
        },
        {
            "hallmark_date": frappe.utils.add_days(today, -14),
            "bis_centre": "BIS Hallmark Centre",
            "item_code": "Ring - Plain Band 24K",
            "huid": "AA1003", "purity": "24K (999)",
            "gross_wt": 4.0, "stone_wt": None,
        },
        {
            "hallmark_date": frappe.utils.add_days(today, -7),
            "bis_centre": "BIS Hallmark Centre",
            "item_code": "Ring - Plain Band 22K",
            "huid": "AA1004", "purity": "22K (916)",
            "gross_wt": 4.8, "stone_wt": None,
        },
        {
            "hallmark_date": frappe.utils.add_days(today, -3),
            "bis_centre": "BIS Hallmark Centre",
            "item_code": "Ring - Solitaire 22K",
            "huid": "AA1005", "purity": "22K (916)",
            "gross_wt": 5.5, "stone_wt": 0.20,
        },
    ]

    for hmr_def in hmr_list:
        doc = frappe.get_doc({
            "doctype": "Hallmarking Register",
            "hallmark_date": hmr_def["hallmark_date"],
            "bis_centre":    hmr_def["bis_centre"],
            "item_code":     hmr_def["item_code"],
            "huid":          hmr_def["huid"],
            "purity":        hmr_def["purity"],
            "gross_wt":      hmr_def["gross_wt"],
            "stone_wt":      hmr_def.get("stone_wt") or 0,
            "remarks":       _SEED_REMARK,
        })
        doc.insert(ignore_permissions=True)
        try:
            doc.submit()
        except Exception as e:
            frappe.logger().warning(
                f"[loupe24k seed] HMR submit failed ({hmr_def['huid']}): {e}"
            )


# ── Workspace ─────────────────────────────────────────────────────────────────

def _seed_workspace():
    """Create (or replace) the Loupe 24K workspace with all DocTypes, then hide others."""
    import json as _json
    ws_label = "Loupe 24K"

    # Delete stale copy so re-runs always reflect the latest layout.
    # Workspace.autoname = field:label, so name == label.
    if frappe.db.exists("Workspace", ws_label):
        frappe.delete_doc("Workspace", ws_label, ignore_permissions=True, force=True)

    shortcuts = [
        # ── Masters ───────────────────────────────────────────────────────────
        {"type": "DocType", "label": "Metal Rate",             "link_to": "Metal Rate",             "color": "#FFB300"},
        {"type": "DocType", "label": "Stone Master",           "link_to": "Stone Master",           "color": "#EC407A"},
        {"type": "DocType", "label": "Stone Lot",              "link_to": "Stone Lot",              "color": "#26A69A"},
        {"type": "DocType", "label": "Item",                   "link_to": "Item",                   "color": "#66BB6A"},
        {"type": "DocType", "label": "Supplier",               "link_to": "Supplier",               "color": "#8D6E63"},
        # ── Karigar Operations ────────────────────────────────────────────────
        {"type": "DocType", "label": "Karigar Metal Issue",    "link_to": "Karigar Metal Issue",    "color": "#FF7043"},
        {"type": "DocType", "label": "Karigar Reconciliation", "link_to": "Karigar Reconciliation", "color": "#7E57C2"},
        # ── Manufacturing ─────────────────────────────────────────────────────
        {"type": "DocType", "label": "BOM",                    "link_to": "BOM",                    "color": "#29B6F6"},
        {"type": "DocType", "label": "Work Order",             "link_to": "Work Order",             "color": "#1E88E5"},
        {"type": "DocType", "label": "Stock Entry",            "link_to": "Stock Entry",            "color": "#AB47BC"},
        {"type": "DocType", "label": "Job Card",               "link_to": "Job Card",               "color": "#F06292"},
        {"type": "DocType", "label": "Serial No",              "link_to": "Serial No",              "color": "#4DB6AC"},
        # ── Sales ─────────────────────────────────────────────────────────────
        {"type": "DocType", "label": "Quotation",              "link_to": "Quotation",              "color": "#9CCC65"},
        {"type": "DocType", "label": "Sales Invoice",          "link_to": "Sales Invoice",          "color": "#EF5350"},
        # ── Scrap & Hallmarking ───────────────────────────────────────────────
        {"type": "DocType", "label": "Scrap Recovery Entry",   "link_to": "Scrap Recovery Entry",   "color": "#78909C"},
        {"type": "DocType", "label": "Hallmarking Register",   "link_to": "Hallmarking Register",   "color": "#5C6BC0"},
        # ── Ledgers ───────────────────────────────────────────────────────────
        {"type": "DocType", "label": "Fine Gold Ledger Entry", "link_to": "Fine Gold Ledger Entry", "color": "#FF8F00"},
        {"type": "DocType", "label": "Stone Ledger Entry",     "link_to": "Stone Ledger Entry",     "color": "#00BCD4"},
    ]

    links = [
        # ── Masters card ──────────────────────────────────────────────────────
        {"type": "Card Break", "label": "Masters"},
        {"type": "Link", "label": "Metal Rate",   "link_to": "Metal Rate",   "link_type": "DocType", "onboard": 1},
        {"type": "Link", "label": "Stone Master", "link_to": "Stone Master", "link_type": "DocType", "onboard": 1},
        {"type": "Link", "label": "Stone Lot",    "link_to": "Stone Lot",    "link_type": "DocType", "onboard": 1},
        {"type": "Link", "label": "Item",         "link_to": "Item",         "link_type": "DocType", "onboard": 1},
        {"type": "Link", "label": "Supplier",     "link_to": "Supplier",     "link_type": "DocType", "onboard": 1},

        # ── Karigar Operations card ───────────────────────────────────────────
        {"type": "Card Break", "label": "Karigar Operations"},
        {"type": "Link", "label": "Karigar Metal Issue",    "link_to": "Karigar Metal Issue",    "link_type": "DocType", "onboard": 1},
        {"type": "Link", "label": "Karigar Reconciliation", "link_to": "Karigar Reconciliation", "link_type": "DocType", "onboard": 1},

        # ── Manufacturing card ────────────────────────────────────────────────
        {"type": "Card Break", "label": "Manufacturing"},
        {"type": "Link", "label": "BOM",        "link_to": "BOM",        "link_type": "DocType", "onboard": 1},
        {"type": "Link", "label": "Work Order", "link_to": "Work Order", "link_type": "DocType", "onboard": 1},
        {"type": "Link", "label": "Stock Entry","link_to": "Stock Entry","link_type": "DocType", "onboard": 0},
        {"type": "Link", "label": "Job Card",   "link_to": "Job Card",   "link_type": "DocType", "onboard": 0},
        {"type": "Link", "label": "Serial No",  "link_to": "Serial No",  "link_type": "DocType", "onboard": 0},

        # ── Sales card ────────────────────────────────────────────────────────
        {"type": "Card Break", "label": "Sales"},
        {"type": "Link", "label": "Quotation",     "link_to": "Quotation",     "link_type": "DocType", "onboard": 1},
        {"type": "Link", "label": "Sales Invoice", "link_to": "Sales Invoice", "link_type": "DocType", "onboard": 1},

        # ── Scrap & Hallmarking card ──────────────────────────────────────────
        {"type": "Card Break", "label": "Scrap & Hallmarking"},
        {"type": "Link", "label": "Scrap Recovery Entry", "link_to": "Scrap Recovery Entry", "link_type": "DocType", "onboard": 1},
        {"type": "Link", "label": "Hallmarking Register", "link_to": "Hallmarking Register", "link_type": "DocType", "onboard": 1},

        # ── Ledgers card ──────────────────────────────────────────────────────
        {"type": "Card Break", "label": "Ledgers"},
        {"type": "Link", "label": "Fine Gold Ledger Entry", "link_to": "Fine Gold Ledger Entry", "link_type": "DocType", "onboard": 0},
        {"type": "Link", "label": "Stone Ledger Entry",     "link_to": "Stone Ledger Entry",     "link_type": "DocType", "onboard": 0},
    ]

    # content tells Frappe v15 how to lay out the cards on the workspace page.
    # Each entry's card_name must match the label of a Card Break entry in links.
    content = _json.dumps([
        {"id": "l24k-masters",        "type": "card", "data": {"card_name": "Masters",             "col": 4}},
        {"id": "l24k-karigar-ops",    "type": "card", "data": {"card_name": "Karigar Operations",  "col": 4}},
        {"id": "l24k-manufacturing",  "type": "card", "data": {"card_name": "Manufacturing",        "col": 4}},
        {"id": "l24k-sales",          "type": "card", "data": {"card_name": "Sales",               "col": 4}},
        {"id": "l24k-scrap-hall",     "type": "card", "data": {"card_name": "Scrap & Hallmarking", "col": 4}},
        {"id": "l24k-ledgers",        "type": "card", "data": {"card_name": "Ledgers",             "col": 4}},
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

    # Hide every other workspace so only Loupe 24K is visible in the sidebar.
    from loupe24k.setup.install import _hide_other_workspaces
    _hide_other_workspaces()
