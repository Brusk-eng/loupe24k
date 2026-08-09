# Loupe 24K

**The jewellery business management system built for the way you actually work.**

Loupe 24K is a purpose-built ERPNext application that brings the full back-office of a modern jewellery business — inventory, production, sales, and compliance — into one place. Whether you run a single workshop or a multi-location retail chain, Loupe 24K replaces the patchwork of spreadsheets, WhatsApp threads, and disconnected tools with a single source of truth.

---

## The Problem

Jewellery businesses operate differently from other retail or manufacturing businesses:

- Inventory isn't just SKUs — it's metal type, purity (karat), stone grades, weight, and finish
- Production is job-order driven, with karigar (artisan) accountability at every stage
- Pricing is live — it moves with gold and silver spot rates
- Regulatory compliance (hallmarking, BIS certification) creates documentation overhead
- Customer orders often involve custom design, repair, and exchange — not just off-the-shelf sales

Generic ERP systems force jewellers to bend their workflow to the software. Loupe 24K is built the other way around.

---

## Three Ledgers, Always in Balance

The core idea behind Loupe 24K is that a jewellery business runs three parallel ledgers simultaneously, and they must reconcile at every step:

| Ledger | Unit | What it tracks |
|---|---|---|
| **Money** | INR | Standard ERPNext stock + accounting — untouched |
| **Fine Gold** | Grams (fine) | Gross weight × touch factor at every transaction |
| **Stones** | Carats + pieces | Diamonds and gemstones, tracked separately from metal |

Every operation — melting, casting, filing, polishing, setting, hallmarking — posts to all three ledgers in one step.

---

## What Loupe 24K Does

### Fine Gold Ledger
A parallel metal sub-ledger that tracks fine gold (gross weight × karat touch factor) across every transaction. Know your fine-gold position by warehouse, karigar, and party at any moment. Supports 24K (1.0), 22K (0.9167), and 18K (0.750) touch factors.

### Stone Ledger
A separate sub-ledger for diamonds and gemstones measured in carats and pieces. Certified solitaires tracked serially; melee parcels tracked by lot. Reconcile issued vs. set vs. returned vs. broken against configurable breakage allowances.

### Live Metal Rate & Pricing
Daily karat-wise rates with auto-derivation (22K and 18K derive from the 24K master via touch). Invoice price build-up: fine gold value + making charges + wastage + stone value + hallmarking, with split GST (3% gold, 5% services).

### Karigar / Job Work Management
Formal job-work challans (ITC-04 compliant) issue metal and stones to artisans. A 1-year return clock enforces CGST Section 143. Reconciliation compares returned fine gold against a per-karigar wastage allowance (default 2%) and flags excess loss.

### Scrap Recovery & Refining
Sprue/button and filing scrap remelt directly. Polishing dust goes to the refiner at a configurable recovery percentage. Recovered fine gold is credited back to the metal account — scrap is metal in transit, not waste.

### Hallmarking & HUID Traceability
Per-piece HUID capture from the BIS hallmarking centre. Each finished ring carries its serial number, gross weight, purity, and hallmark date. Full audit trail for regulatory inspection.

### Step-wise Weight Tracking
Every manufacturing operation (alloying → casting → filing → polishing → setting) captures weight-in, weight-out, scrap, and loss. Fine-in must equal fine-out + scrap + loss within a 0.005 g tolerance — the system blocks submission if it doesn't balance.

---

## Data Model Overview

| DocType | Purpose |
|---|---|
| Fine Gold Ledger Entry | One row per fine-gold movement (issue/receipt/scrap/loss/recovery/rework) |
| Stone Ledger Entry | One row per stone movement (issue/set/return/broken) |
| Stone Master | Stone type definition (shape, colour, clarity, cut, rate per carat) |
| Stone Lot | Specific parcel or serial stone, linked to a Stone Master |
| Metal Rate | Daily karat-wise gold rate |
| Karigar Metal Issue | Job-work challan — issues metal + stones to a karigar or setter |
| Karigar Reconciliation | Settles a job-work issue: weighs return, calculates fine loss vs allowance |
| Scrap Recovery Entry | Sends scrap to refiner, credits recovered fine gold |
| Hallmarking Register | Per-piece HUID and hallmark details |

Custom fields are added to standard ERPNext DocTypes (Item, BOM, Work Order, Stock Entry, Job Card, Serial No, Quotation, Sales Invoice, Supplier) to carry weight, karat, and stone data through the standard manufacturing flow.

---

## Who Is This For

- Jewellery manufacturers and wholesalers managing ring or ornament production
- Retail jewellery stores with repair and custom order services
- Chains running multiple showrooms or workshops
- Businesses that need ITC-04 compliance and BIS hallmarking documentation

---

## Built On

Loupe 24K is a custom application for [ERPNext](https://erpnext.com/) v15, the world's leading open-source ERP. ERPNext provides battle-tested financials, manufacturing, HR, and CRM out of the box — Loupe 24K adds the jewellery-specific layer on top without touching the core.

---

## License

MIT
