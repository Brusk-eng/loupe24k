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

    _seed_departments_and_designations(company)
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] Departments/Designations done")

    _seed_employees(company)
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] Employees done")

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

    lead_names = _seed_crm_leads()
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] CRM Leads done")

    _seed_crm_opportunities(lead_names)
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] CRM Opportunities done")

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

    _seed_sales_orders()
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] Sales Orders done")

    _seed_quotations()
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] Quotations done")

    _seed_print_formats()
    frappe.db.commit()
    frappe.logger().info("[loupe24k seed] Print Formats done")

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


# ── Employees ─────────────────────────────────────────────────────────────────

def _seed_departments_and_designations(company):
    departments = ["Manufacturing"]
    for department in departments:
        if not frappe.db.exists(
            "Department",
            {"department_name": department, "company": company},
        ):
            frappe.get_doc({
                "doctype": "Department",
                "department_name": department,
                "company": company,
            }).insert(ignore_permissions=True)

    designations = [
        "Bench Jeweler",
        "Stone Setter",
        "Polisher",
        "Quality Inspector",
    ]
    for designation in designations:
        if not frappe.db.exists("Designation", designation):
            frappe.get_doc({
                "doctype": "Designation",
                "designation_name": designation,
            }).insert(ignore_permissions=True)

    genders = ["Male", "Female"]
    for gender in genders:
        if not frappe.db.exists("Gender", gender):
            frappe.get_doc({
                "doctype": "Gender",
                "gender": gender,
            }).insert(ignore_permissions=True)


def _seed_employees(company):
    """Create a small set of production-ready employees for MFG assignments."""
    manufacturing_department = frappe.db.get_value(
        "Department",
        {"department_name": "Manufacturing", "company": company},
        "name",
    ) or "Manufacturing"

    employees = [
        {
            "employee_number": "L24K-EMP-001",
            "first_name": "Ramesh",
            "last_name": "Soni",
            "employee_name": "Ramesh Soni",
            "designation": "Bench Jeweler",
            "department": "Manufacturing",
            "gender": "Male",
            "date_of_birth": "1990-06-12",
            "cell_number": "+1 555 0101",
            "date_of_joining": "2024-01-15",
            "status": "Active",
        },
        {
            "employee_number": "L24K-EMP-002",
            "first_name": "Suresh",
            "last_name": "Patel",
            "employee_name": "Suresh Patel",
            "designation": "Stone Setter",
            "department": "Manufacturing",
            "gender": "Male",
            "date_of_birth": "1992-03-08",
            "cell_number": "+1 555 0102",
            "date_of_joining": "2024-02-10",
            "status": "Active",
        },
        {
            "employee_number": "L24K-EMP-003",
            "first_name": "Anjali",
            "last_name": "Shah",
            "employee_name": "Anjali Shah",
            "designation": "Polisher",
            "department": "Manufacturing",
            "gender": "Female",
            "date_of_birth": "1994-11-21",
            "cell_number": "+1 555 0103",
            "date_of_joining": "2024-03-05",
            "status": "Active",
        },
        {
            "employee_number": "L24K-EMP-004",
            "first_name": "Meera",
            "last_name": "Kapoor",
            "employee_name": "Meera Kapoor",
            "designation": "Quality Inspector",
            "department": "Manufacturing",
            "gender": "Female",
            "date_of_birth": "1991-09-15",
            "cell_number": "+1 555 0104",
            "date_of_joining": "2024-04-01",
            "status": "Active",
        },
    ]

    for emp in employees:
        existing = frappe.db.get_value(
            "Employee",
            {"employee_number": emp["employee_number"]},
            "name",
        ) or frappe.db.get_value(
            "Employee",
            {"employee_name": emp["employee_name"], "company": company},
            "name",
        )
        if existing:
            continue

        # ERPNext stores Department names with company suffixes (e.g. "X - ABBR").
        emp_data = {**emp, "department": manufacturing_department}
        doc = frappe.get_doc({
            "doctype": "Employee",
            "company": company,
            **emp_data,
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
      Ring Blank 22K                → Ring - Plain Band 22K  (Jewellery Finishing)
      Ring Blank 22K                → Ring - Melee Band 22K  (Stone Setting Finish)
      Ring Blank 22K                → Ring - Solitaire 22K   (Stone Setting Finish)
      Pure Gold 24K                 → Ring - Plain Band 24K  (Cast & Finish)
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
            # Melee band: file, pavé-set scattered small diamonds, then polish.
            # Many small stones → slightly higher setting loss than a plain band
            # but lower than a solitaire (no single large stone to seat precisely).
            "item": "Ring - Melee Band 22K",
            "quantity": 4.5,
            "routing": "Stone Setting Finish",
            "items": [
                {"item_code": "Ring Blank 22K", "qty": 5.0},
            ],
            "custom": {
                "target_touch": "22K",
                "wastage_pct": 1.5,
                "expected_setting_loss_pct": 1.5,
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
        {
            # Pavé / channel-set band with scattered melee diamonds — distinct
            # from Ring - Plain Band 22K (no stones) and Ring - Solitaire 22K
            # (single large center stone).
            "item_code": "Ring - Melee Band 22K",
            "item_name": "Ring - Melee Band 22K",
            "item_group": "Finished Jewellery",
            "stock_uom": "Gram",
            "valuation_method": "Moving Average",
            "karat": "22K",
        },
        # ── Finished jewellery pieces sold by unit (Piece UOM) ───────────────
        # These items represent the retail product line shown on customer invoices.
        # stock_uom=Piece because retail qty is always in units, not grams.
        # Actual gold weight is captured via the gross_wt custom field per sale line.
        {
            "item_code": "Bangle - Floral 22K",
            "item_name": "Bangle - Floral 22K",
            "item_group": "Finished Jewellery",
            "stock_uom": "Piece",
            "valuation_method": "Moving Average",
            "karat": "22K",
            "metal_type": "Gold",
        },
        {
            "item_code": "Necklace - Traditional 22K",
            "item_name": "Necklace - Traditional 22K",
            "item_group": "Finished Jewellery",
            "stock_uom": "Piece",
            "valuation_method": "Moving Average",
            "karat": "22K",
            "metal_type": "Gold",
        },
        {
            "item_code": "Earrings - Stud 22K",
            "item_name": "Earrings - Stud 22K",
            "item_group": "Finished Jewellery",
            "stock_uom": "Piece",
            "valuation_method": "Moving Average",
            "karat": "22K",
            "metal_type": "Gold",
        },
        {
            # 18K is standard for diamond jewellery — harder alloy holds stone settings better.
            "item_code": "Ring - Diamond 18K",
            "item_name": "Ring - Diamond 18K",
            "item_group": "Finished Jewellery",
            "stock_uom": "Piece",
            "valuation_method": "Moving Average",
            "karat": "18K",
            "metal_type": "Gold",
            "touch": 0.7500,
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
        {
            # CZ / Synthetic stones used in necklaces and budget jewellery
            "stone_name": "CZ Synthetic Stone",
            "stone_type": "Other",
            "shape": "Round",
            "tracking_type": "Lot",
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
        {"customer_name": "Goldfield Exports Pvt Ltd"},
        {"customer_name": "Premium Jewels Mumbai"},
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
    """Seed today's gold rates for all three karats.

    22K and 18K are derived from the 24K base rate (100 USD/g):
      22K = 100 × 0.9167 = 91.67 USD/g
      18K = 100 × 0.7500 = 75.00 USD/g
    """
    today = frappe.utils.today()
    rates = [
        {"karat": "24K", "rate_per_g": 100.00},
        {"karat": "22K", "rate_per_g":  91.67, "derived_from_24k": 1},
        {"karat": "18K", "rate_per_g":  75.00, "derived_from_24k": 1},
    ]
    for r in rates:
        if not frappe.db.exists("Metal Rate", {"date": today, "karat": r["karat"]}):
            doc = frappe.get_doc({"doctype": "Metal Rate", "date": today, **r})
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

    # Demonstrate voucher linkage when Job Card records are available.
    job_card_name = None
    if frappe.db.exists("DocType", "Job Card"):
        job_card_name = frappe.db.get_value("Job Card", {}, "name")
    if job_card_name and sre_list:
        sre_list[0]["voucher_type"] = "Job Card"
        sre_list[0]["voucher_no"] = job_card_name

    for sre_def in sre_list:
        doc = frappe.get_doc({
            "doctype": "Scrap Recovery Entry",
            "entry_date":    sre_def["entry_date"],
            "refiner":       sre_def["refiner"],
            "recovery_type": sre_def["recovery_type"],
            "voucher_type":  sre_def.get("voucher_type", ""),
            "voucher_no":    sre_def.get("voucher_no", ""),
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


# ── CRM Leads ─────────────────────────────────────────────────────────────────

def _seed_lead_sources():
    """Ensure the Lead Source records used by seed leads exist."""
    sources = ["Word of Mouth", "Trade Show", "Website"]
    for src in sources:
        if not frappe.db.exists("Lead Source", src):
            frappe.get_doc({
                "doctype": "Lead Source",
                "source_name": src,
            }).insert(ignore_permissions=True)


def _seed_crm_leads():
    """Create sample CRM Leads representing prospective jewellery buyers.

    Returns a dict {email_id: doc.name} so _seed_crm_opportunities can link
    to the correct Lead document names.
    """
    _seed_lead_sources()

    leads = [
        {
            # Individual customer — wedding jewellery inquiry, already quoted
            "lead_name": "Nisha Agarwal",
            "email_id": "nisha.agarwal@gmail.com",
            "mobile_no": "+91 98765 11111",
            "status": "Opportunity",
            "source": "Word of Mouth",
        },
        {
            # B2B contact — bulk export inquiry, quotation in progress
            "lead_name": "Rahul Verma",
            "company_name": "Goldfield Exports Pvt Ltd",
            "email_id": "rahul.verma@goldfield-exports.com",
            "mobile_no": "+91 22 6789 0000",
            "status": "Quotation",
            "source": "Trade Show",
        },
        {
            # Individual — custom solitaire, early stage
            "lead_name": "Divya Mehta",
            "email_id": "divya.mehta@outlook.com",
            "mobile_no": "+91 99887 22222",
            "status": "Open",
            "source": "Website",
        },
    ]

    lead_names = {}
    for lead_data in leads:
        existing = frappe.db.get_value("Lead", {"email_id": lead_data["email_id"]}, "name")
        if existing:
            lead_names[lead_data["email_id"]] = existing
            continue
        doc = frappe.get_doc({"doctype": "Lead", **lead_data})
        doc.insert(ignore_permissions=True)
        lead_names[lead_data["email_id"]] = doc.name

    return lead_names


# ── CRM Opportunities ──────────────────────────────────────────────────────────

def _seed_crm_opportunities(lead_names):
    """Create CRM Opportunities linked to the seeded Leads."""
    today = frappe.utils.today()

    opportunities = [
        {
            "opportunity_from": "Lead",
            "party_name": lead_names.get("nisha.agarwal@gmail.com"),
            "opportunity_type": "Sales",
            "status": "Quotation",
            "expected_closing": frappe.utils.add_days(today, 30),
            # title / detail fields vary across ERPNext versions — use notes
        },
        {
            "opportunity_from": "Lead",
            "party_name": lead_names.get("rahul.verma@goldfield-exports.com"),
            "opportunity_type": "Sales",
            "status": "Open",
            "expected_closing": frappe.utils.add_days(today, 45),
        },
    ]

    for opp_data in opportunities:
        if not opp_data["party_name"]:
            continue
        if frappe.db.get_value(
            "Opportunity",
            {"party_name": opp_data["party_name"], "opportunity_type": "Sales"},
            "name",
        ):
            continue
        doc = frappe.get_doc({"doctype": "Opportunity", **opp_data})
        try:
            doc.insert(ignore_permissions=True, ignore_links=True)
        except Exception as e:
            frappe.logger().warning(
                f"[loupe24k seed] Opportunity insert failed for {opp_data['party_name']}: {e}"
            )


# ── Sales Orders ───────────────────────────────────────────────────────────────

def _ensure_price_lists():
    """Create standard selling/buying price lists if the setup wizard never ran."""
    if not frappe.db.exists("Price List", "Standard Selling"):
        frappe.get_doc({
            "doctype": "Price List",
            "price_list_name": "Standard Selling",
            "currency": _COMPANY_CURRENCY,
            "selling": 1,
            "buying": 0,
            "enabled": 1,
        }).insert(ignore_permissions=True)
    if not frappe.db.exists("Price List", "Standard Buying"):
        frappe.get_doc({
            "doctype": "Price List",
            "price_list_name": "Standard Buying",
            "currency": _COMPANY_CURRENCY,
            "selling": 0,
            "buying": 1,
            "enabled": 1,
        }).insert(ignore_permissions=True)


def _seed_sales_orders():
    """Create a demo Sales Order: 5 Melee Bands + 1 Solitaire for Rajwadi Jewellers.

    Jewellery pricing breakdown (22K @ $91.67/g):
      Ring - Melee Band 22K (qty=22.5g = 5 rings × 4.5g avg):
        gross_wt=22.5g, stone_wt=0.15g (5×0.15ct melee × 0.2g/ct), net=22.35g
        metal   = 22.35 × 91.67 = $2,048.82
        making  = 22.35 × 12.00 =   $268.20
        stones  = 0.75ct × $180 =   $135.00  →  line total $2,452.02

      Ring - Solitaire 22K (qty=5.0g = 1 ring):
        gross_wt=5.0g, stone_wt=0.20g (1ct × 0.2g/ct), net=4.80g
        metal   = 4.80 × 91.67  =  $440.02
        making  = 4.80 × 20.00  =   $96.00
        stones  = 1.0ct × $950  =  $950.00  →  line total $1,486.02
    """
    _ensure_price_lists()

    if frappe.db.exists("Sales Order", {"po_no": "DEMO-SO-001"}):
        # Backfill jewellery custom fields if they were added after initial seed
        _so_backfill_jewellery_fields()
    else:
        today = frappe.utils.today()
        delivery_date = frappe.utils.add_days(today, 30)

        price_list = (
            frappe.db.get_value("Price List", {"selling": 1, "enabled": 1}, "name")
            or "Standard Selling"
        )

        doc = frappe.get_doc({
            "doctype": "Sales Order",
            "customer": "Rajwadi Jewellers",
            "transaction_date": today,
            "delivery_date": delivery_date,
            "po_no": "DEMO-SO-001",
            "order_type": "Sales",
            "currency": _COMPANY_CURRENCY,
            "selling_price_list": price_list,
            "ignore_pricing_rule": 1,
            "remarks": _SEED_REMARK,
            "items": [
                {
                    "item_code": "Ring - Melee Band 22K",
                    "qty": 22.5,           # 5 rings × 4.5 g
                    "uom": "Gram",
                    "rate": 109.0,         # ≈ $2,452 / 22.5g
                    "delivery_date": delivery_date,
                    "description": "5 rings × 4.5 g avg — Melee Diamond Bands (22K)",
                },
                {
                    "item_code": "Ring - Solitaire 22K",
                    "qty": 5.0,            # 1 ring × 5.0 g
                    "uom": "Gram",
                    "rate": 297.20,        # ≈ $1,486 / 5.0g
                    "delivery_date": delivery_date,
                    "description": "1 ring × 5.0 g — Solitaire with 1 ct Diamond (22K)",
                },
            ],
        })
        doc.insert(ignore_permissions=True)
        try:
            doc.submit()
        except Exception as e:
            frappe.logger().warning(f"[loupe24k seed] Sales Order submit failed: {e}")

        _so_backfill_jewellery_fields(doc.name)
        _so_add_stone_details(doc.name)

    # ── Sales Order 2: Exhibition Display Stock (14 items) ───────────────────
    _SO2_ITEMS = [
        {
            "item_code": "Ring - Plain Band 22K",
            "qty": 22.5, "uom": "Gram", "rate": 103.67, "delivery_date": frappe.utils.add_days(frappe.utils.today(), 30),
            "description": "22K Plain Band Rings – 5 pieces × 4.5 g",
            "_jewellery": {
                "gross_wt": 22.50, "stone_wt": 0.00, "net_gold_wt": 22.50,
                "gold_rate": 91.67, "making_rate": 12.00,
                "metal_value": 2062.58, "making_charge": 270.00, "stone_value": 0.00,
            },
        },
        {
            "item_code": "Ring - Plain Band 22K",
            "qty": 13.5, "uom": "Gram", "rate": 103.67, "delivery_date": frappe.utils.add_days(frappe.utils.today(), 30),
            "description": "22K Plain Band Rings – 3 pieces × 4.5 g (petite)",
            "_jewellery": {
                "gross_wt": 13.50, "stone_wt": 0.00, "net_gold_wt": 13.50,
                "gold_rate": 91.67, "making_rate": 12.00,
                "metal_value": 1237.55, "making_charge": 162.00, "stone_value": 0.00,
            },
        },
        {
            "item_code": "Ring - Solitaire 22K",
            "qty": 11.0, "uom": "Gram", "rate": 193.97, "delivery_date": frappe.utils.add_days(frappe.utils.today(), 30),
            "description": "22K Solitaire Rings – 2 pieces × 5.5 g (0.5 ct each)",
            "_jewellery": {
                "gross_wt": 11.00, "stone_wt": 0.40, "net_gold_wt": 10.60,
                "gold_rate": 91.67, "making_rate": 20.00,
                "metal_value": 971.70, "making_charge": 212.00, "stone_value": 950.00,
            },
        },
        {
            "item_code": "Ring - Solitaire 22K",
            "qty": 16.5, "uom": "Gram", "rate": 193.97, "delivery_date": frappe.utils.add_days(frappe.utils.today(), 30),
            "description": "22K Solitaire Rings – 3 pieces × 5.5 g (larger stones)",
            "_jewellery": {
                "gross_wt": 16.50, "stone_wt": 0.60, "net_gold_wt": 15.90,
                "gold_rate": 91.67, "making_rate": 20.00,
                "metal_value": 1457.55, "making_charge": 318.00, "stone_value": 1425.00,
            },
        },
        {
            "item_code": "Ring - Melee Band 22K",
            "qty": 18.0, "uom": "Gram", "rate": 130.21, "delivery_date": frappe.utils.add_days(frappe.utils.today(), 30),
            "description": "22K Melee Diamond Bands – 4 pieces × 4.5 g",
            "_jewellery": {
                "gross_wt": 18.00, "stone_wt": 0.60, "net_gold_wt": 17.40,
                "gold_rate": 91.67, "making_rate": 12.00,
                "metal_value": 1595.06, "making_charge": 208.80, "stone_value": 540.00,
            },
        },
        {
            "item_code": "Ring - Melee Band 22K",
            "qty": 22.5, "uom": "Gram", "rate": 130.21, "delivery_date": frappe.utils.add_days(frappe.utils.today(), 30),
            "description": "22K Melee Diamond Bands – 5 pieces × 4.5 g (wide band)",
            "_jewellery": {
                "gross_wt": 22.50, "stone_wt": 0.75, "net_gold_wt": 21.75,
                "gold_rate": 91.67, "making_rate": 12.00,
                "metal_value": 1993.83, "making_charge": 261.00, "stone_value": 675.00,
            },
        },
        {
            "item_code": "Ring - Plain Band 24K",
            "qty": 8.0, "uom": "Gram", "rate": 110.00, "delivery_date": frappe.utils.add_days(frappe.utils.today(), 30),
            "description": "Pure 24K Gold Bands – 2 pieces × 4.0 g",
            "_jewellery": {
                "gross_wt": 8.00, "stone_wt": 0.00, "net_gold_wt": 8.00,
                "gold_rate": 100.00, "making_rate": 10.00,
                "metal_value": 800.00, "making_charge": 80.00, "stone_value": 0.00,
            },
        },
        {
            "item_code": "Bangle - Floral 22K",
            "qty": 4, "uom": "Piece", "rate": 1696.05, "delivery_date": frappe.utils.add_days(frappe.utils.today(), 30),
            "description": "22K Gold Floral Bangles – 4 pieces (2 pairs)",
            "_jewellery": {
                "gross_wt": 63.60, "stone_wt": 0.00, "net_gold_wt": 63.60,
                "gold_rate": 91.67, "making_rate": 15.00,
                "metal_value": 5830.21, "making_charge": 954.00, "stone_value": 0.00,
            },
        },
        {
            "item_code": "Bangle - Floral 22K",
            "qty": 2, "uom": "Piece", "rate": 1056.04, "delivery_date": frappe.utils.add_days(frappe.utils.today(), 30),
            "description": "22K Gold Slim Bangles – 2 pieces (1 pair)",
            "_jewellery": {
                "gross_wt": 19.80, "stone_wt": 0.00, "net_gold_wt": 19.80,
                "gold_rate": 91.67, "making_rate": 15.00,
                "metal_value": 1815.07, "making_charge": 297.00, "stone_value": 0.00,
            },
        },
        {
            "item_code": "Necklace - Traditional 22K",
            "qty": 1, "uom": "Piece", "rate": 8378.15, "delivery_date": frappe.utils.add_days(frappe.utils.today(), 30),
            "description": "22K Heavy Temple Necklace with CZ stones",
            "_jewellery": {
                "gross_wt": 78.50, "stone_wt": 3.20, "net_gold_wt": 75.30,
                "gold_rate": 91.67, "making_rate": 18.00,
                "metal_value": 6902.75, "making_charge": 1355.40, "stone_value": 120.00,
            },
        },
        {
            "item_code": "Necklace - Traditional 22K",
            "qty": 2, "uom": "Piece", "rate": 5168.86, "delivery_date": frappe.utils.add_days(frappe.utils.today(), 30),
            "description": "22K Lightweight Chain Necklaces – 2 pieces",
            "_jewellery": {
                "gross_wt": 94.00, "stone_wt": 2.50, "net_gold_wt": 91.50,
                "gold_rate": 91.67, "making_rate": 18.00,
                "metal_value": 8387.81, "making_charge": 1647.00, "stone_value": 70.00,
            },
        },
        {
            "item_code": "Earrings - Stud 22K",
            "qty": 3, "uom": "Piece", "rate": 1032.05, "delivery_date": frappe.utils.add_days(frappe.utils.today(), 30),
            "description": "22K Gold Stud Earrings – 3 pairs",
            "_jewellery": {
                "gross_wt": 29.58, "stone_wt": 0.00, "net_gold_wt": 29.58,
                "gold_rate": 91.67, "making_rate": 13.00,
                "metal_value": 2711.60, "making_charge": 384.54, "stone_value": 0.00,
            },
        },
        {
            "item_code": "Earrings - Stud 22K",
            "qty": 2, "uom": "Piece", "rate": 1867.19, "delivery_date": frappe.utils.add_days(frappe.utils.today(), 30),
            "description": "22K Gold Dangle Earrings with CZ – 2 pairs",
            "_jewellery": {
                "gross_wt": 36.80, "stone_wt": 1.60, "net_gold_wt": 35.20,
                "gold_rate": 91.67, "making_rate": 13.00,
                "metal_value": 3226.78, "making_charge": 457.60, "stone_value": 50.00,
            },
        },
        {
            "item_code": "Ring - Diamond 18K",
            "qty": 2, "uom": "Piece", "rate": 916.83, "delivery_date": frappe.utils.add_days(frappe.utils.today(), 30),
            "description": "18K Gold Diamond Rings – 2 pieces",
            "_jewellery": {
                "gross_wt": 16.48, "stone_wt": 1.70, "net_gold_wt": 14.78,
                "gold_rate": 75.00, "making_rate": 22.00,
                "metal_value": 1108.50, "making_charge": 325.16, "stone_value": 400.00,
            },
        },
    ]
    _create_sales_order(
        po_no="DEMO-SO-002",
        customer="Rajwadi Jewellers",
        price_list=frappe.db.get_value("Price List", {"selling": 1, "enabled": 1}, "name") or "Standard Selling",
        items=_SO2_ITEMS,
        summary={
            "total_gross_wt":      452.76,
            "total_stone_wt":       11.35,
            "total_net_gold_wt":   441.41,
            "total_gold_value":   40100.99,
            "total_making_charges": 6932.50,
            "total_stone_charges":  4210.00,
        },
        stones=[
            {"item_ref": "Ring - Solitaire 22K", "stone_type": "Certified Solitaire Diamond",
             "qty": 2, "weight": 0.40, "weight_unit": "ct", "rate_per_unit": 950.00, "amount": 950.00},
            {"item_ref": "Ring - Solitaire 22K", "stone_type": "Certified Solitaire Diamond",
             "qty": 3, "weight": 0.60, "weight_unit": "ct", "rate_per_unit": 950.00, "amount": 1425.00},
            {"item_ref": "Ring - Melee Band 22K", "stone_type": "Round Diamond",
             "qty": 60, "weight": 3.00, "weight_unit": "ct", "rate_per_unit": 180.00, "amount": 540.00},
            {"item_ref": "Ring - Melee Band 22K", "stone_type": "Round Diamond",
             "qty": 75, "weight": 3.75, "weight_unit": "ct", "rate_per_unit": 180.00, "amount": 675.00},
            {"item_ref": "Necklace - Traditional 22K", "stone_type": "CZ Synthetic Stone",
             "qty": 30, "weight": 3.20, "weight_unit": "g", "rate_per_unit": 3.75, "amount": 120.00},
            {"item_ref": "Necklace - Traditional 22K", "stone_type": "CZ Synthetic Stone",
             "qty": 25, "weight": 2.50, "weight_unit": "g", "rate_per_unit": 2.80, "amount": 70.00},
            {"item_ref": "Earrings - Stud 22K", "stone_type": "CZ Synthetic Stone",
             "qty": 16, "weight": 1.60, "weight_unit": "g", "rate_per_unit": 3.13, "amount": 50.00},
            {"item_ref": "Ring - Diamond 18K", "stone_type": "Round Diamond",
             "qty": 16, "weight": 1.70, "weight_unit": "ct", "rate_per_unit": 235.29, "amount": 400.00},
        ],
    )

    # ── Sales Order 3: Wholesale Regular Order (11 items) ────────────────────
    _SO3_ITEMS = [
        {
            "item_code": "Ring - Plain Band 22K",
            "qty": 67.5, "uom": "Gram", "rate": 103.67, "delivery_date": frappe.utils.add_days(frappe.utils.today(), 45),
            "description": "22K Plain Band Rings – 15 pieces × 4.5 g",
            "_jewellery": {
                "gross_wt": 67.50, "stone_wt": 0.00, "net_gold_wt": 67.50,
                "gold_rate": 91.67, "making_rate": 12.00,
                "metal_value": 6187.73, "making_charge": 810.00, "stone_value": 0.00,
            },
        },
        {
            "item_code": "Ring - Plain Band 22K",
            "qty": 45.0, "uom": "Gram", "rate": 103.67, "delivery_date": frappe.utils.add_days(frappe.utils.today(), 45),
            "description": "22K Plain Band Rings – 10 pieces × 4.5 g (slim)",
            "_jewellery": {
                "gross_wt": 45.00, "stone_wt": 0.00, "net_gold_wt": 45.00,
                "gold_rate": 91.67, "making_rate": 12.00,
                "metal_value": 4125.15, "making_charge": 540.00, "stone_value": 0.00,
            },
        },
        {
            "item_code": "Ring - Melee Band 22K",
            "qty": 31.5, "uom": "Gram", "rate": 130.21, "delivery_date": frappe.utils.add_days(frappe.utils.today(), 45),
            "description": "22K Melee Diamond Bands – 7 pieces × 4.5 g",
            "_jewellery": {
                "gross_wt": 31.50, "stone_wt": 1.05, "net_gold_wt": 30.45,
                "gold_rate": 91.67, "making_rate": 12.00,
                "metal_value": 2791.30, "making_charge": 365.40, "stone_value": 945.00,
            },
        },
        {
            "item_code": "Ring - Melee Band 22K",
            "qty": 22.5, "uom": "Gram", "rate": 130.21, "delivery_date": frappe.utils.add_days(frappe.utils.today(), 45),
            "description": "22K Melee Diamond Bands – 5 pieces × 4.5 g (wider)",
            "_jewellery": {
                "gross_wt": 22.50, "stone_wt": 0.75, "net_gold_wt": 21.75,
                "gold_rate": 91.67, "making_rate": 12.00,
                "metal_value": 1993.83, "making_charge": 261.00, "stone_value": 675.00,
            },
        },
        {
            "item_code": "Ring - Solitaire 22K",
            "qty": 20.0, "uom": "Gram", "rate": 193.97, "delivery_date": frappe.utils.add_days(frappe.utils.today(), 45),
            "description": "22K Solitaire Rings – 4 pieces × 5.0 g (0.5 ct each)",
            "_jewellery": {
                "gross_wt": 20.00, "stone_wt": 0.80, "net_gold_wt": 19.20,
                "gold_rate": 91.67, "making_rate": 20.00,
                "metal_value": 1760.06, "making_charge": 384.00, "stone_value": 1900.00,
            },
        },
        {
            "item_code": "Ring - Plain Band 24K",
            "qty": 16.0, "uom": "Gram", "rate": 110.00, "delivery_date": frappe.utils.add_days(frappe.utils.today(), 45),
            "description": "Pure 24K Gold Bands – 4 pieces × 4.0 g",
            "_jewellery": {
                "gross_wt": 16.00, "stone_wt": 0.00, "net_gold_wt": 16.00,
                "gold_rate": 100.00, "making_rate": 10.00,
                "metal_value": 1600.00, "making_charge": 160.00, "stone_value": 0.00,
            },
        },
        {
            "item_code": "Bangle - Floral 22K",
            "qty": 8, "uom": "Piece", "rate": 1674.72, "delivery_date": frappe.utils.add_days(frappe.utils.today(), 45),
            "description": "22K Gold Floral Bangles – 8 pieces",
            "_jewellery": {
                "gross_wt": 125.60, "stone_wt": 0.00, "net_gold_wt": 125.60,
                "gold_rate": 91.67, "making_rate": 15.00,
                "metal_value": 11513.75, "making_charge": 1884.00, "stone_value": 0.00,
            },
        },
        {
            "item_code": "Necklace - Traditional 22K",
            "qty": 4, "uom": "Piece", "rate": 5052.37, "delivery_date": frappe.utils.add_days(frappe.utils.today(), 45),
            "description": "22K Traditional Chain Necklaces – 4 pieces with CZ",
            "_jewellery": {
                "gross_wt": 188.00, "stone_wt": 5.00, "net_gold_wt": 183.00,
                "gold_rate": 91.67, "making_rate": 18.00,
                "metal_value": 16775.61, "making_charge": 3294.00, "stone_value": 140.00,
            },
        },
        {
            "item_code": "Necklace - Traditional 22K",
            "qty": 2, "uom": "Piece", "rate": 7906.57, "delivery_date": frappe.utils.add_days(frappe.utils.today(), 45),
            "description": "22K Heavy Temple Necklaces – 2 pieces with CZ",
            "_jewellery": {
                "gross_wt": 148.00, "stone_wt": 6.00, "net_gold_wt": 142.00,
                "gold_rate": 91.67, "making_rate": 18.00,
                "metal_value": 13017.14, "making_charge": 2556.00, "stone_value": 240.00,
            },
        },
        {
            "item_code": "Earrings - Stud 22K",
            "qty": 8, "uom": "Piece", "rate": 1032.05, "delivery_date": frappe.utils.add_days(frappe.utils.today(), 45),
            "description": "22K Gold Stud Earrings – 8 pairs",
            "_jewellery": {
                "gross_wt": 78.88, "stone_wt": 0.00, "net_gold_wt": 78.88,
                "gold_rate": 91.67, "making_rate": 13.00,
                "metal_value": 7230.93, "making_charge": 1025.44, "stone_value": 0.00,
            },
        },
        {
            "item_code": "Ring - Diamond 18K",
            "qty": 3, "uom": "Piece", "rate": 916.83, "delivery_date": frappe.utils.add_days(frappe.utils.today(), 45),
            "description": "18K Gold Diamond Cluster Rings – 3 pieces",
            "_jewellery": {
                "gross_wt": 24.72, "stone_wt": 2.55, "net_gold_wt": 22.17,
                "gold_rate": 75.00, "making_rate": 22.00,
                "metal_value": 1662.75, "making_charge": 487.74, "stone_value": 600.00,
            },
        },
    ]
    _create_sales_order(
        po_no="DEMO-SO-003",
        customer="Goldfield Exports Pvt Ltd",
        price_list=frappe.db.get_value("Price List", {"selling": 1, "enabled": 1}, "name") or "Standard Selling",
        items=_SO3_ITEMS,
        summary={
            "total_gross_wt":      777.20,
            "total_stone_wt":       16.15,
            "total_net_gold_wt":   761.05,
            "total_gold_value":   66658.25,
            "total_making_charges": 11766.58,
            "total_stone_charges":   4500.00,
        },
        stones=[
            {"item_ref": "Ring - Melee Band 22K", "stone_type": "Round Diamond",
             "qty": 53, "weight": 2.625, "weight_unit": "ct", "rate_per_unit": 180.00, "amount": 472.50},
            {"item_ref": "Ring - Melee Band 22K", "stone_type": "Round Diamond",
             "qty": 38, "weight": 1.875, "weight_unit": "ct", "rate_per_unit": 180.00, "amount": 337.50},
            {"item_ref": "Ring - Solitaire 22K", "stone_type": "Certified Solitaire Diamond",
             "qty": 4, "weight": 0.80, "weight_unit": "ct", "rate_per_unit": 950.00, "amount": 760.00},
            {"item_ref": "Necklace - Traditional 22K", "stone_type": "CZ Synthetic Stone",
             "qty": 100, "weight": 5.00, "weight_unit": "g", "rate_per_unit": 1.40, "amount": 140.00},
            {"item_ref": "Necklace - Traditional 22K", "stone_type": "CZ Synthetic Stone",
             "qty": 60, "weight": 6.00, "weight_unit": "g", "rate_per_unit": 4.00, "amount": 240.00},
            {"item_ref": "Ring - Diamond 18K", "stone_type": "Round Diamond",
             "qty": 24, "weight": 2.55, "weight_unit": "ct", "rate_per_unit": 235.29, "amount": 564.70},
        ],
    )


def _create_sales_order(po_no, customer, price_list, items, summary, stones=None):
    """Insert one Sales Order with jewellery pricing fields. Idempotent."""
    if frappe.db.exists("Sales Order", {"po_no": po_no}):
        return

    today = frappe.utils.today()
    delivery_date = frappe.utils.add_days(today, 30)

    std_items = []
    for it in items:
        row = {k: v for k, v in it.items() if k != "_jewellery"}
        if "delivery_date" not in row:
            row["delivery_date"] = delivery_date
        std_items.append(row)

    doc = frappe.get_doc({
        "doctype": "Sales Order",
        "customer": customer,
        "transaction_date": today,
        "delivery_date": delivery_date,
        "po_no": po_no,
        "order_type": "Sales",
        "currency": _COMPANY_CURRENCY,
        "selling_price_list": price_list,
        "ignore_pricing_rule": 1,
        "remarks": _SEED_REMARK,
        "items": std_items,
    })
    doc.insert(ignore_permissions=True)
    try:
        doc.submit()
    except Exception as e:
        frappe.logger().warning(f"[loupe24k seed] Sales Order {po_no} submit failed: {e}")

    # ── Jewellery custom fields on item rows (index-matched) ──────────────────
    rows = frappe.get_all(
        "Sales Order Item",
        filters={"parent": doc.name},
        fields=["name", "item_code", "idx"],
        order_by="idx asc",
    )
    for row in rows:
        pos = row["idx"] - 1
        jewellery = items[pos].get("_jewellery") if pos < len(items) else None
        if jewellery:
            try:
                frappe.db.set_value("Sales Order Item", row["name"], jewellery)
            except Exception:
                pass

    # ── Parent-level summary ──────────────────────────────────────────────────
    try:
        frappe.db.set_value("Sales Order", doc.name, summary)
    except Exception:
        pass

    # ── Stone detail rows ─────────────────────────────────────────────────────
    for idx, stone in enumerate(stones or [], start=1):
        try:
            frappe.get_doc({
                "doctype": "Jewellery Stone Detail",
                "parenttype": "Sales Order",
                "parent": doc.name,
                "parentfield": "jewellery_stones",
                "idx": idx,
                **stone,
            }).insert(ignore_permissions=True)
        except Exception:
            pass

    frappe.logger().info(
        f"[loupe24k seed] Sales Order {po_no} created for {customer}: {doc.name}"
    )


def _so_backfill_jewellery_fields(so_name=None):
    """Set jewellery custom fields on the demo Sales Order items and parent summary."""
    if not so_name:
        so_name = frappe.db.get_value("Sales Order", {"po_no": "DEMO-SO-001"}, "name")
    if not so_name:
        return

    # Item-level fields keyed by item_code
    item_fields = {
        "Ring - Melee Band 22K": {
            "gross_wt": 22.5, "stone_wt": 0.15, "net_gold_wt": 22.35,
            "gold_rate": 91.67, "making_rate": 12.00,
            "metal_value": 2048.82, "making_charge": 268.20, "stone_value": 135.00,
        },
        "Ring - Solitaire 22K": {
            "gross_wt": 5.0, "stone_wt": 0.20, "net_gold_wt": 4.80,
            "gold_rate": 91.67, "making_rate": 20.00,
            "metal_value": 440.02, "making_charge": 96.00, "stone_value": 950.00,
        },
    }
    rows = frappe.get_all(
        "Sales Order Item",
        filters={"parent": so_name},
        fields=["name", "item_code"],
    )
    for row in rows:
        fields = item_fields.get(row["item_code"])
        if fields:
            try:
                frappe.db.set_value("Sales Order Item", row["name"], fields)
            except Exception:
                pass

    try:
        frappe.db.set_value("Sales Order", so_name, {
            "total_gross_wt": 27.5,
            "total_stone_wt": 0.35,
            "total_net_gold_wt": 27.15,
            "total_gold_value": 2488.84,
            "total_making_charges": 364.20,
            "total_stone_charges": 1085.00,
        })
    except Exception:
        pass


def _so_add_stone_details(so_name):
    """Insert jewellery_stones child table rows for the demo Sales Order."""
    if frappe.db.count("Jewellery Stone Detail", {"parent": so_name}):
        return

    stones = [
        {
            "item_ref": "Ring - Melee Band 22K",
            "stone_type": "Round Diamond",
            "qty": 25, "weight": 0.75, "weight_unit": "ct",
            "rate_per_unit": 180.00, "amount": 135.00,
        },
        {
            "item_ref": "Ring - Solitaire 22K",
            "stone_type": "Certified Solitaire Diamond",
            "qty": 1, "weight": 1.00, "weight_unit": "ct",
            "rate_per_unit": 950.00, "amount": 950.00,
        },
    ]
    for idx, stone in enumerate(stones, start=1):
        try:
            frappe.get_doc({
                "doctype": "Jewellery Stone Detail",
                "parenttype": "Sales Order",
                "parent": so_name,
                "parentfield": "jewellery_stones",
                "idx": idx,
                **stone,
            }).insert(ignore_permissions=True)
        except Exception:
            pass


# ── Quotations ────────────────────────────────────────────────────────────────

def _seed_quotations():
    """Create two demo Quotations exercising the new jewellery pricing fields.

    Quotation 1 — Retail: 4-piece assortment for Rajwadi Jewellers
      Mirrors the sample invoice: bangle, necklace, 18K diamond ring, earrings.
      All items use stock_uom=Piece so qty = number of pieces.

    Quotation 2 — Wholesale: bulk plain bands + solitaires for Goldfield Exports
      Uses existing Gram-UOM ring items, qty = total grams.
    """
    _ensure_price_lists()

    price_list = (
        frappe.db.get_value("Price List", {"selling": 1, "enabled": 1}, "name")
        or "Standard Selling"
    )
    today = frappe.utils.today()
    valid_till = frappe.utils.add_days(today, 30)

    # ── Quotation 1: Retail assortment ────────────────────────────────────────
    # Pricing (22K @ $91.67/g, 18K @ $75.00/g):
    #
    #  Bangle ×2 (31.42g gross, no stones):
    #    metal   = 31.42 × 91.67 = $2,880.63
    #    making  = 31.42 × 15.00 =   $471.30  → line $3,351.93  → rate $1,675.97/pc
    #
    #  Necklace ×1 (46.85g gross, 1.25g CZ stones):
    #    net=45.60g; metal = 45.60 × 91.67 = $4,180.15
    #    making = 45.60 × 18.00 = $820.80; stones = $35.00 → line $5,035.95
    #
    #  18K Diamond Ring ×1 (8.24g gross, 0.85g stone):
    #    net=7.39g; metal = 7.39 × 75.00 = $554.25
    #    making = 7.39 × 22.00 = $162.58; stones = $200.00 → line $916.83
    #
    #  Earrings ×1 pair (9.86g gross, no stones):
    #    metal  = 9.86 × 91.67 = $903.87
    #    making = 9.86 × 13.00 = $128.18  → line $1,032.05
    #
    #  Grand total (ex-tax): $10,336.76
    _Q1_ITEMS = [
        {
            "item_code": "Bangle - Floral 22K",
            "qty": 2, "uom": "Piece",
            "rate": 1675.97,           # (2880.63 + 471.30) / 2
            "description": "22K Gold Bangle – Floral Pattern (pair)",
            "_jewellery": {
                "gross_wt": 31.420, "stone_wt": 0.000, "net_gold_wt": 31.420,
                "gold_rate": 91.67, "making_rate": 15.00,
                "metal_value": 2880.63, "making_charge": 471.30, "stone_value": 0.00,
            },
        },
        {
            "item_code": "Necklace - Traditional 22K",
            "qty": 1, "uom": "Piece",
            "rate": 5035.95,
            "description": "22K Gold Necklace – Traditional (with CZ stones)",
            "_jewellery": {
                "gross_wt": 46.850, "stone_wt": 1.250, "net_gold_wt": 45.600,
                "gold_rate": 91.67, "making_rate": 18.00,
                "metal_value": 4180.15, "making_charge": 820.80, "stone_value": 35.00,
            },
        },
        {
            "item_code": "Ring - Diamond 18K",
            "qty": 1, "uom": "Piece",
            "rate": 916.83,
            "description": "18K Gold Diamond Ring (natural diamonds)",
            "_jewellery": {
                "gross_wt": 8.240, "stone_wt": 0.850, "net_gold_wt": 7.390,
                "gold_rate": 75.00, "making_rate": 22.00,
                "metal_value": 554.25, "making_charge": 162.58, "stone_value": 200.00,
            },
        },
        {
            "item_code": "Earrings - Stud 22K",
            "qty": 1, "uom": "Piece",
            "rate": 1032.05,
            "description": "22K Gold Earrings – Stud Design (pair)",
            "_jewellery": {
                "gross_wt": 9.860, "stone_wt": 0.000, "net_gold_wt": 9.860,
                "gold_rate": 91.67, "making_rate": 13.00,
                "metal_value": 903.87, "making_charge": 128.18, "stone_value": 0.00,
            },
        },
    ]
    _Q1_STONES = [
        {
            "item_ref": "Necklace - Traditional 22K",
            "stone_type": "CZ Synthetic Stone",
            "qty": 24, "weight": 1.250, "weight_unit": "g",
            "rate_per_unit": 28.00, "amount": 35.00,
        },
        {
            "item_ref": "Ring - Diamond 18K",
            "stone_type": "Round Diamond",
            "qty": 8, "weight": 0.850, "weight_unit": "ct",
            "rate_per_unit": 235.29, "amount": 200.00,
        },
    ]
    _Q1_SUMMARY = {
        "total_gross_wt": 96.370,
        "total_stone_wt":  2.100,
        "total_net_gold_wt": 94.270,
        "total_gold_value": 8518.90,
        "total_making_charges": 1582.86,
        "total_stone_charges":   235.00,
    }

    _create_quotation(
        quotation_id="QUOT-SEED-001",
        customer="Rajwadi Jewellers",
        price_list=price_list,
        valid_till=valid_till,
        today=today,
        items=_Q1_ITEMS,
        stones=_Q1_STONES,
        summary=_Q1_SUMMARY,
    )

    # ── Quotation 2: Wholesale bulk order ────────────────────────────────────
    # Uses Gram-UOM items; qty = total grams across all pieces.
    #
    #  Plain Band 22K ×10 pieces (45.0g total, no stones):
    #    metal  = 45.00 × 91.67 = $4,125.15
    #    making = 45.00 × 12.00 =   $540.00  → line $4,665.15  → rate $466.52/pc
    #
    #  Solitaire 22K ×3 pieces (15.0g total, 0.45g stone):
    #    net=14.55g; metal = 14.55 × 91.67 = $1,333.80
    #    making = 14.55 × 20.00 = $291.00
    #    stones = 0.75ct × $180 = $135.00   → line $1,759.80  → rate $586.60/pc
    #
    #  Grand total (ex-tax): $6,424.95
    _Q2_ITEMS = [
        {
            "item_code": "Ring - Plain Band 22K",
            "qty": 45.0, "uom": "Gram",
            "rate": 103.67,            # ≈ $4,665 / 45g
            "description": "22K Plain Band Rings — 10 pieces × 4.5 g avg",
            "_jewellery": {
                "gross_wt": 45.000, "stone_wt": 0.000, "net_gold_wt": 45.000,
                "gold_rate": 91.67, "making_rate": 12.00,
                "metal_value": 4125.15, "making_charge": 540.00, "stone_value": 0.00,
            },
        },
        {
            "item_code": "Ring - Solitaire 22K",
            "qty": 15.0, "uom": "Gram",
            "rate": 117.32,            # ≈ $1,760 / 15g
            "description": "22K Solitaire Rings — 3 pieces × 5.0 g avg (0.25 ct melee each)",
            "_jewellery": {
                "gross_wt": 15.000, "stone_wt": 0.450, "net_gold_wt": 14.550,
                "gold_rate": 91.67, "making_rate": 20.00,
                "metal_value": 1333.80, "making_charge": 291.00, "stone_value": 135.00,
            },
        },
    ]
    _Q2_STONES = [
        {
            "item_ref": "Ring - Solitaire 22K",
            "stone_type": "Round Diamond",
            "qty": 9, "weight": 0.750, "weight_unit": "ct",
            "rate_per_unit": 180.00, "amount": 135.00,
        },
    ]
    _Q2_SUMMARY = {
        "total_gross_wt": 60.000,
        "total_stone_wt":  0.450,
        "total_net_gold_wt": 59.550,
        "total_gold_value": 5458.95,
        "total_making_charges": 831.00,
        "total_stone_charges":  135.00,
    }

    _create_quotation(
        quotation_id="QUOT-SEED-002",
        customer="Goldfield Exports Pvt Ltd",
        price_list=price_list,
        valid_till=valid_till,
        today=today,
        items=_Q2_ITEMS,
        stones=_Q2_STONES,
        summary=_Q2_SUMMARY,
    )

    # ── Quotation 3: Grand Bridal Collection (12 items) ───────────────────────
    # Rajwadi Jewellers; full bridal set across 12 line items to exercise
    # multi-page PDF layout.  22K @ $91.67/g, 18K @ $75.00/g, 24K @ $100/g.
    _Q3_ITEMS = [
        {
            "item_code": "Bangle - Floral 22K",
            "qty": 4, "uom": "Piece",
            "rate": 1696.05,
            "description": "22K Gold Bangle – Wide Bridal Pattern (2 pairs)",
            "_jewellery": {
                "gross_wt": 63.60, "stone_wt": 0.00, "net_gold_wt": 63.60,
                "gold_rate": 91.67, "making_rate": 15.00,
                "metal_value": 5830.21, "making_charge": 954.00, "stone_value": 0.00,
            },
        },
        {
            "item_code": "Bangle - Floral 22K",
            "qty": 2, "uom": "Piece",
            "rate": 1056.04,
            "description": "22K Gold Bangle – Slim Accent Pattern (1 pair)",
            "_jewellery": {
                "gross_wt": 19.80, "stone_wt": 0.00, "net_gold_wt": 19.80,
                "gold_rate": 91.67, "making_rate": 15.00,
                "metal_value": 1815.07, "making_charge": 297.00, "stone_value": 0.00,
            },
        },
        {
            "item_code": "Necklace - Traditional 22K",
            "qty": 1, "uom": "Piece",
            "rate": 8378.15,
            "description": "22K Heavy Bridal Necklace with CZ Stones",
            "_jewellery": {
                "gross_wt": 78.50, "stone_wt": 3.20, "net_gold_wt": 75.30,
                "gold_rate": 91.67, "making_rate": 18.00,
                "metal_value": 6902.75, "making_charge": 1355.40, "stone_value": 120.00,
            },
        },
        {
            "item_code": "Necklace - Traditional 22K",
            "qty": 1, "uom": "Piece",
            "rate": 5746.71,
            "description": "22K Gold Rope Chain Necklace",
            "_jewellery": {
                "gross_wt": 52.40, "stone_wt": 0.00, "net_gold_wt": 52.40,
                "gold_rate": 91.67, "making_rate": 18.00,
                "metal_value": 4803.51, "making_charge": 943.20, "stone_value": 0.00,
            },
        },
        {
            "item_code": "Earrings - Stud 22K",
            "qty": 2, "uom": "Piece",
            "rate": 1496.78,
            "description": "22K Gold Jhumka Earrings – Large (2 pairs)",
            "_jewellery": {
                "gross_wt": 28.60, "stone_wt": 0.00, "net_gold_wt": 28.60,
                "gold_rate": 91.67, "making_rate": 13.00,
                "metal_value": 2621.76, "making_charge": 371.80, "stone_value": 0.00,
            },
        },
        {
            "item_code": "Earrings - Stud 22K",
            "qty": 1, "uom": "Piece",
            "rate": 1867.19,
            "description": "22K Gold Chandbali Drop Earrings (1 pair) with CZ",
            "_jewellery": {
                "gross_wt": 18.40, "stone_wt": 0.80, "net_gold_wt": 17.60,
                "gold_rate": 91.67, "making_rate": 13.00,
                "metal_value": 1613.39, "making_charge": 228.80, "stone_value": 25.00,
            },
        },
        {
            "item_code": "Ring - Diamond 18K",
            "qty": 2, "uom": "Piece",
            "rate": 1065.70,
            "description": "18K Gold Diamond Cluster Rings (2 pcs)",
            "_jewellery": {
                "gross_wt": 18.40, "stone_wt": 2.20, "net_gold_wt": 16.20,
                "gold_rate": 75.00, "making_rate": 22.00,
                "metal_value": 1215.00, "making_charge": 356.40, "stone_value": 560.00,
            },
        },
        {
            "item_code": "Ring - Diamond 18K",
            "qty": 1, "uom": "Piece",
            "rate": 2254.80,
            "description": "18K Gold Solitaire Engagement Ring – 1.2 ct Natural Diamond",
            "_jewellery": {
                "gross_wt": 9.80, "stone_wt": 1.40, "net_gold_wt": 8.40,
                "gold_rate": 75.00, "making_rate": 22.00,
                "metal_value": 630.00, "making_charge": 184.80, "stone_value": 1440.00,
            },
        },
        {
            "item_code": "Ring - Melee Band 22K",
            "qty": 18.0, "uom": "Gram",
            "rate": 130.21,
            "description": "22K Melee Diamond Bands – 4 pieces × 4.5 g avg",
            "_jewellery": {
                "gross_wt": 18.00, "stone_wt": 0.60, "net_gold_wt": 17.40,
                "gold_rate": 91.67, "making_rate": 12.00,
                "metal_value": 1595.06, "making_charge": 208.80, "stone_value": 540.00,
            },
        },
        {
            "item_code": "Ring - Plain Band 22K",
            "qty": 22.5, "uom": "Gram",
            "rate": 103.67,
            "description": "22K Plain Band Rings – 5 pieces × 4.5 g avg",
            "_jewellery": {
                "gross_wt": 22.50, "stone_wt": 0.00, "net_gold_wt": 22.50,
                "gold_rate": 91.67, "making_rate": 12.00,
                "metal_value": 2062.58, "making_charge": 270.00, "stone_value": 0.00,
            },
        },
        {
            "item_code": "Ring - Solitaire 22K",
            "qty": 11.0, "uom": "Gram",
            "rate": 193.97,
            "description": "22K Solitaire Rings – 2 pieces × 5.5 g avg (0.5 ct each)",
            "_jewellery": {
                "gross_wt": 11.00, "stone_wt": 0.40, "net_gold_wt": 10.60,
                "gold_rate": 91.67, "making_rate": 20.00,
                "metal_value": 971.70, "making_charge": 212.00, "stone_value": 950.00,
            },
        },
        {
            "item_code": "Ring - Plain Band 24K",
            "qty": 8.0, "uom": "Gram",
            "rate": 110.00,
            "description": "Pure 24K Gold Bands – 2 pieces × 4.0 g avg",
            "_jewellery": {
                "gross_wt": 8.00, "stone_wt": 0.00, "net_gold_wt": 8.00,
                "gold_rate": 100.00, "making_rate": 10.00,
                "metal_value": 800.00, "making_charge": 80.00, "stone_value": 0.00,
            },
        },
    ]
    _Q3_STONES = [
        {
            "item_ref": "Necklace - Traditional 22K",
            "stone_type": "CZ Synthetic Stone",
            "qty": 30, "weight": 3.20, "weight_unit": "g",
            "rate_per_unit": 4.00, "amount": 120.00,
        },
        {
            "item_ref": "Earrings - Stud 22K",
            "stone_type": "CZ Synthetic Stone",
            "qty": 8, "weight": 0.80, "weight_unit": "g",
            "rate_per_unit": 3.13, "amount": 25.00,
        },
        {
            "item_ref": "Ring - Diamond 18K",
            "stone_type": "Round Diamond",
            "qty": 16, "weight": 2.20, "weight_unit": "ct",
            "rate_per_unit": 254.55, "amount": 560.00,
        },
        {
            "item_ref": "Ring - Diamond 18K",
            "stone_type": "Certified Solitaire Diamond",
            "qty": 1, "weight": 1.20, "weight_unit": "ct",
            "rate_per_unit": 1200.00, "amount": 1440.00,
        },
        {
            "item_ref": "Ring - Melee Band 22K",
            "stone_type": "Round Diamond",
            "qty": 60, "weight": 3.00, "weight_unit": "ct",
            "rate_per_unit": 180.00, "amount": 540.00,
        },
        {
            "item_ref": "Ring - Solitaire 22K",
            "stone_type": "Certified Solitaire Diamond",
            "qty": 2, "weight": 1.00, "weight_unit": "ct",
            "rate_per_unit": 475.00, "amount": 950.00,
        },
    ]
    _Q3_SUMMARY = {
        "total_gross_wt":      348.50,
        "total_stone_wt":        8.60,
        "total_net_gold_wt":   339.90,
        "total_gold_value":  30861.03,
        "total_making_charges": 5462.20,
        "total_stone_charges":  3635.00,
    }
    _create_quotation(
        quotation_id="QUOT-SEED-003",
        customer="Rajwadi Jewellers",
        price_list=price_list,
        valid_till=valid_till,
        today=today,
        items=_Q3_ITEMS,
        stones=_Q3_STONES,
        summary=_Q3_SUMMARY,
    )

    # ── Quotation 4: Export Collection Bulk Order (13 items) ──────────────────
    # Goldfield Exports; large wholesale order mixing gram and piece items.
    _Q4_ITEMS = [
        {
            "item_code": "Ring - Plain Band 22K",
            "qty": 90.0, "uom": "Gram",
            "rate": 103.67,
            "description": "22K Plain Band Rings – 20 pieces × 4.5 g avg",
            "_jewellery": {
                "gross_wt": 90.00, "stone_wt": 0.00, "net_gold_wt": 90.00,
                "gold_rate": 91.67, "making_rate": 12.00,
                "metal_value": 8250.30, "making_charge": 1080.00, "stone_value": 0.00,
            },
        },
        {
            "item_code": "Ring - Plain Band 22K",
            "qty": 45.0, "uom": "Gram",
            "rate": 103.67,
            "description": "22K Lightweight Plain Bands – 15 pieces × 3.0 g avg",
            "_jewellery": {
                "gross_wt": 45.00, "stone_wt": 0.00, "net_gold_wt": 45.00,
                "gold_rate": 91.67, "making_rate": 12.00,
                "metal_value": 4125.15, "making_charge": 540.00, "stone_value": 0.00,
            },
        },
        {
            "item_code": "Ring - Melee Band 22K",
            "qty": 45.0, "uom": "Gram",
            "rate": 130.21,
            "description": "22K Melee Diamond Bands – 10 pieces × 4.5 g avg",
            "_jewellery": {
                "gross_wt": 45.00, "stone_wt": 1.50, "net_gold_wt": 43.50,
                "gold_rate": 91.67, "making_rate": 12.00,
                "metal_value": 3987.65, "making_charge": 522.00, "stone_value": 1350.00,
            },
        },
        {
            "item_code": "Ring - Melee Band 22K",
            "qty": 22.5, "uom": "Gram",
            "rate": 130.21,
            "description": "22K Melee Diamond Bands – 5 pieces × 4.5 g avg (smaller stones)",
            "_jewellery": {
                "gross_wt": 22.50, "stone_wt": 0.75, "net_gold_wt": 21.75,
                "gold_rate": 91.67, "making_rate": 12.00,
                "metal_value": 1993.83, "making_charge": 261.00, "stone_value": 675.00,
            },
        },
        {
            "item_code": "Ring - Solitaire 22K",
            "qty": 25.0, "uom": "Gram",
            "rate": 202.21,
            "description": "22K Solitaire Rings – 5 pieces × 5.0 g avg (0.5 ct each)",
            "_jewellery": {
                "gross_wt": 25.00, "stone_wt": 1.00, "net_gold_wt": 24.00,
                "gold_rate": 91.67, "making_rate": 20.00,
                "metal_value": 2200.08, "making_charge": 480.00, "stone_value": 2375.00,
            },
        },
        {
            "item_code": "Ring - Solitaire 22K",
            "qty": 15.0, "uom": "Gram",
            "rate": 187.20,
            "description": "22K Solitaire Rings – 3 pieces × 5.0 g avg (smaller stones)",
            "_jewellery": {
                "gross_wt": 15.00, "stone_wt": 0.60, "net_gold_wt": 14.40,
                "gold_rate": 91.67, "making_rate": 20.00,
                "metal_value": 1320.05, "making_charge": 288.00, "stone_value": 1200.00,
            },
        },
        {
            "item_code": "Ring - Plain Band 24K",
            "qty": 20.0, "uom": "Gram",
            "rate": 110.00,
            "description": "Pure 24K Gold Bands – 5 pieces × 4.0 g avg",
            "_jewellery": {
                "gross_wt": 20.00, "stone_wt": 0.00, "net_gold_wt": 20.00,
                "gold_rate": 100.00, "making_rate": 10.00,
                "metal_value": 2000.00, "making_charge": 200.00, "stone_value": 0.00,
            },
        },
        {
            "item_code": "Bangle - Floral 22K",
            "qty": 10, "uom": "Piece",
            "rate": 1674.72,
            "description": "22K Gold Floral Bangles – 10 pieces",
            "_jewellery": {
                "gross_wt": 157.00, "stone_wt": 0.00, "net_gold_wt": 157.00,
                "gold_rate": 91.67, "making_rate": 15.00,
                "metal_value": 14392.19, "making_charge": 2355.00, "stone_value": 0.00,
            },
        },
        {
            "item_code": "Bangle - Floral 22K",
            "qty": 6, "uom": "Piece",
            "rate": 2026.73,
            "description": "22K Gold Wide Premium Bangles – 6 pieces",
            "_jewellery": {
                "gross_wt": 114.00, "stone_wt": 0.00, "net_gold_wt": 114.00,
                "gold_rate": 91.67, "making_rate": 15.00,
                "metal_value": 10450.38, "making_charge": 1710.00, "stone_value": 0.00,
            },
        },
        {
            "item_code": "Necklace - Traditional 22K",
            "qty": 5, "uom": "Piece",
            "rate": 5052.37,
            "description": "22K Traditional Chain Necklaces – 5 pieces with CZ",
            "_jewellery": {
                "gross_wt": 235.00, "stone_wt": 6.25, "net_gold_wt": 228.75,
                "gold_rate": 91.67, "making_rate": 18.00,
                "metal_value": 20969.36, "making_charge": 4117.50, "stone_value": 175.00,
            },
        },
        {
            "item_code": "Necklace - Traditional 22K",
            "qty": 3, "uom": "Piece",
            "rate": 7906.57,
            "description": "22K Heavy Temple Necklaces – 3 pieces with CZ",
            "_jewellery": {
                "gross_wt": 222.00, "stone_wt": 9.00, "net_gold_wt": 213.00,
                "gold_rate": 91.67, "making_rate": 18.00,
                "metal_value": 19525.71, "making_charge": 3834.00, "stone_value": 360.00,
            },
        },
        {
            "item_code": "Earrings - Stud 22K",
            "qty": 10, "uom": "Piece",
            "rate": 1032.05,
            "description": "22K Gold Stud Earrings – 10 pairs",
            "_jewellery": {
                "gross_wt": 98.60, "stone_wt": 0.00, "net_gold_wt": 98.60,
                "gold_rate": 91.67, "making_rate": 13.00,
                "metal_value": 9038.66, "making_charge": 1281.80, "stone_value": 0.00,
            },
        },
        {
            "item_code": "Ring - Diamond 18K",
            "qty": 4, "uom": "Piece",
            "rate": 916.83,
            "description": "18K Gold Diamond Rings – 4 pieces",
            "_jewellery": {
                "gross_wt": 32.96, "stone_wt": 3.40, "net_gold_wt": 29.56,
                "gold_rate": 75.00, "making_rate": 22.00,
                "metal_value": 2217.00, "making_charge": 650.32, "stone_value": 800.00,
            },
        },
    ]
    _Q4_STONES = [
        {
            "item_ref": "Ring - Melee Band 22K",
            "stone_type": "Round Diamond",
            "qty": 75, "weight": 7.50, "weight_unit": "ct",
            "rate_per_unit": 180.00, "amount": 1350.00,
        },
        {
            "item_ref": "Ring - Melee Band 22K",
            "stone_type": "Round Diamond",
            "qty": 38, "weight": 3.75, "weight_unit": "ct",
            "rate_per_unit": 180.00, "amount": 675.00,
        },
        {
            "item_ref": "Ring - Solitaire 22K",
            "stone_type": "Certified Solitaire Diamond",
            "qty": 5, "weight": 2.50, "weight_unit": "ct",
            "rate_per_unit": 950.00, "amount": 2375.00,
        },
        {
            "item_ref": "Ring - Solitaire 22K",
            "stone_type": "Certified Solitaire Diamond",
            "qty": 3, "weight": 1.50, "weight_unit": "ct",
            "rate_per_unit": 800.00, "amount": 1200.00,
        },
        {
            "item_ref": "Necklace - Traditional 22K",
            "stone_type": "CZ Synthetic Stone",
            "qty": 125, "weight": 6.25, "weight_unit": "g",
            "rate_per_unit": 1.40, "amount": 175.00,
        },
        {
            "item_ref": "Necklace - Traditional 22K",
            "stone_type": "CZ Synthetic Stone",
            "qty": 90, "weight": 9.00, "weight_unit": "g",
            "rate_per_unit": 4.00, "amount": 360.00,
        },
        {
            "item_ref": "Ring - Diamond 18K",
            "stone_type": "Round Diamond",
            "qty": 32, "weight": 3.40, "weight_unit": "ct",
            "rate_per_unit": 235.29, "amount": 800.00,
        },
    ]
    _Q4_SUMMARY = {
        "total_gross_wt":      972.06,
        "total_stone_wt":       22.50,
        "total_net_gold_wt":   949.56,
        "total_gold_value":  101270.36,
        "total_making_charges": 17119.62,
        "total_stone_charges":   8935.00,
    }
    _create_quotation(
        quotation_id="QUOT-SEED-004",
        customer="Goldfield Exports Pvt Ltd",
        price_list=price_list,
        valid_till=valid_till,
        today=today,
        items=_Q4_ITEMS,
        stones=_Q4_STONES,
        summary=_Q4_SUMMARY,
    )


def _create_quotation(quotation_id, customer, price_list, valid_till, today,
                      items, stones, summary):
    """Insert one Quotation with full jewellery pricing fields."""
    if frappe.db.sql(
        "SELECT name FROM `tabQuotation` WHERE title = %s LIMIT 1", quotation_id
    ):
        return

    # Build standard items list (strip the _jewellery helper key)
    std_items = []
    for it in items:
        row = {k: v for k, v in it.items() if k != "_jewellery"}
        std_items.append(row)

    doc = frappe.get_doc({
        "doctype": "Quotation",
        "title": quotation_id,
        "quotation_to": "Customer",
        "party_name": customer,
        "transaction_date": today,
        "valid_till": valid_till,
        "currency": _COMPANY_CURRENCY,
        "selling_price_list": price_list,
        "ignore_pricing_rule": 1,
        "items": std_items,
    })
    doc.insert(ignore_permissions=True, ignore_mandatory=True)

    # ── Set jewellery custom fields on each item row ──────────────────────────
    # Match by position (idx) so duplicate item_codes in one doc work correctly.
    rows = frappe.get_all(
        "Quotation Item",
        filters={"parent": doc.name},
        fields=["name", "item_code", "idx"],
        order_by="idx asc",
    )
    for row in rows:
        pos = row["idx"] - 1          # idx is 1-based
        jewellery = (
            items[pos].get("_jewellery")
            if pos < len(items)
            else None
        )
        if jewellery:
            try:
                frappe.db.set_value("Quotation Item", row["name"], jewellery)
            except Exception:
                pass

    # ── Set parent-level summary fields ──────────────────────────────────────
    try:
        frappe.db.set_value("Quotation", doc.name, summary)
    except Exception:
        pass

    # ── Insert stone/gem detail rows ─────────────────────────────────────────
    for idx, stone in enumerate(stones, start=1):
        try:
            frappe.get_doc({
                "doctype": "Jewellery Stone Detail",
                "parenttype": "Quotation",
                "parent": doc.name,
                "parentfield": "jewellery_stones",
                "idx": idx,
                **stone,
            }).insert(ignore_permissions=True)
        except Exception:
            pass

    frappe.logger().info(
        f"[loupe24k seed] Quotation {quotation_id} created for {customer}: {doc.name}"
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
        # ── CRM ───────────────────────────────────────────────────────────────
        {"type": "DocType", "label": "Lead",                   "link_to": "Lead",                   "color": "#42A5F5"},
        {"type": "DocType", "label": "Opportunity",            "link_to": "Opportunity",            "color": "#26C6DA"},
        # ── Sales ─────────────────────────────────────────────────────────────
        {"type": "DocType", "label": "Sales Order",            "link_to": "Sales Order",            "color": "#FFA726"},
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

        # ── CRM card ──────────────────────────────────────────────────────────
        {"type": "Card Break", "label": "CRM"},
        {"type": "Link", "label": "Lead",        "link_to": "Lead",        "link_type": "DocType", "onboard": 1},
        {"type": "Link", "label": "Opportunity", "link_to": "Opportunity", "link_type": "DocType", "onboard": 1},

        # ── Sales card ────────────────────────────────────────────────────────
        {"type": "Card Break", "label": "Sales"},
        {"type": "Link", "label": "Sales Order",   "link_to": "Sales Order",   "link_type": "DocType", "onboard": 1},
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
        {"id": "l24k-crm",            "type": "card", "data": {"card_name": "CRM",                 "col": 4}},
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


# ── Print Formats ─────────────────────────────────────────────────────────────

def _seed_print_formats():
    """Create jewellery print formats for Quotation and Sales Order and set them as default."""
    import os

    _pf_dir = os.path.join(
        os.path.dirname(__file__),
        "..", "loupe_24k", "print_format",
    )

    formats = [
        {
            "name": "Jewellery Quotation",
            "doc_type": "Quotation",
            "html_file": os.path.join(_pf_dir, "jewellery_quotation", "jewellery_quotation.html"),
        },
        {
            "name": "Jewellery Sales Order",
            "doc_type": "Sales Order",
            "html_file": os.path.join(_pf_dir, "jewellery_sales_order", "jewellery_sales_order.html"),
        },
    ]

    for pf in formats:
        with open(pf["html_file"], "r") as f:
            html_content = f.read()

        if frappe.db.exists("Print Format", pf["name"]):
            doc = frappe.get_doc("Print Format", pf["name"])
            doc.html = html_content
            doc.save(ignore_permissions=True)
        else:
            frappe.get_doc({
                "doctype": "Print Format",
                "name": pf["name"],
                "doc_type": pf["doc_type"],
                "module": "Loupe 24K",
                "print_format_type": "Jinja",
                "html": html_content,
                "disabled": 0,
                "custom_format": 1,
            }).insert(ignore_permissions=True)

        # Set as default print format for the DocType (idempotent)
        ps_name = f"{pf['doc_type']}-default_print_format-default_print_format"
        if frappe.db.exists("Property Setter", ps_name):
            frappe.db.set_value("Property Setter", ps_name, "value", pf["name"])
        else:
            frappe.make_property_setter({
                "doctype": pf["doc_type"],
                "doctype_or_field": "DocType",
                "fieldname": "default_print_format",
                "property": "default_print_format",
                "property_type": "Data",
                "value": pf["name"],
            }, ignore_validate=True)
        frappe.logger().info(f"[loupe24k seed] Print Format '{pf['name']}' set as default for {pf['doc_type']}")
