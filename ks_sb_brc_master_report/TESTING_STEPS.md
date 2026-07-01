# SB/BRC Master Report – Testing Steps

## Prerequisites

- Odoo 18 instance running
- **Apps installed**: `account`, `sale`, `stock`, `product`
- For full invoice/SB data: **l10n_in** (Indian localization) if you use Shipping Bill fields on invoices

---

## 1. Install the Module

1. **Enable Developer Mode** (if not already):
   - Go to **Settings** → scroll down → **Activate the developer mode**.

2. **Update Apps List**:
   - Go to **Apps**.
   - Click **Update Apps List**.
   - Confirm if prompted.

3. **Install the module**:
   - In **Apps**, remove the “Apps” filter.
   - Search for **“SB/BRC Master”** or **“SB BRC Master Report”**.
   - Click **Install**.

4. **Verify installation**:
   - No error popup.
   - In the main menu you see **SB/BRC Master** (top level or under your custom/accounting menu, depending on your menu configuration).

---

## 2. Access the SB/BRC Master Report

1. Go to **SB/BRC Master** → **SB/BRC Master Report**.
2. You should see:
   - An empty list (tree) view, or
   - A message like “Create your first SB/BRC Master Report!” if no records exist.
3. Confirm the list columns show: Sr. No., Date, Invoice, SB No, Buyer, Invoice Amount (USD), Amount (INR), BRC Status, BRC Date, BRC No, BRC Amount USD.

---

## 3. Create a New Record (Minimal)

1. Click **Create**.
2. **Required / main fields**:
   - **Date**: Should default to today; you can change it.
   - Leave **Invoice** empty for this test (or pick one if you have customer invoices).
3. **Save**.
4. Check:
   - **Sr. No.** is filled automatically (e.g. 1, 2, 3…).
   - Record opens in form view and all tabs are visible.

---

## 4. Create a Record with One or Multiple Invoices (Full Flow)

1. **Prepare invoices** (if needed):
   - **Sales** → create Quotations → Confirm → **Create Invoice** → **Post** the invoices.
   - Or use existing posted **Customer Invoices** (**Accounting** → **Invoices**).
   - For “multiple invoices in one record”, use 2–3 invoices that belong to the **same Shipping Bill (SB)**.

2. **Create SB/BRC Master record**:
   - **SB/BRC Master** → **SB/BRC Master Report** → **Create**.
   - **Date**: e.g. today.
   - **Invoices**: Select **one or more** posted customer invoices (multi-select / tags).
     - One record can have **multiple invoices** (same SB).
3. **Save** (or click outside the Invoices field to trigger related computations).
4. **Verify “from invoices” and computed fields**:
   - **Consignee**: From first invoice or “Multiple” if different across invoices.
   - **Buyer**: From first invoice or “Multiple” if different.
   - **Currency**: From first invoice.
   - **Invoice Amount (USD)** (or invoice currency): **Sum** of all selected invoices’ totals.
   - **QTY (KG)**: **Sum** of quantities on all selected invoices’ lines.
   - **Unit Rate**: **Weighted average** across all selected invoices’ lines.
   - **Amount (INR)**: Computed if **EX Rate** is set; formula: Invoice Amount × EX Rate.
   - **SB No**: From first invoice (e.g. **l10n_in** Shipping Bill number); same SB expected for all invoices in one record.

---

## 4b. Test Multiple Invoices in One Record

1. Create **2–3 posted Customer Invoices** (same customer/consignee and same SB number if you use l10n_in).
2. **SB/BRC Master Report** → **Create**.
3. In **Invoices**, click and add **all 2–3 invoices** (multi-select; they appear as tags).
4. **Save**.
5. Verify:
   - **Invoice Amount (USD)** = sum of the 2–3 invoices’ totals.
   - **QTY (KG)** = sum of quantities from all invoice lines.
   - **Unit Rate** = weighted average (total amount / total qty across all lines).
   - **Consignee** / **Buyer**: If same for all → one name; if different → comma-separated or “Multiple”.
   - **SB No** = from first invoice (same for all when same SB).

---

## 5. Test Charges and Totals

1. Open the record you created (with or without invoice).
2. Go to the **Charges** tab.
3. Enter amounts in some fields, e.g.:
   - Freight: 1000  
   - Agency Charges: 500  
   - Terminal handling: 300  
   - Insurance: 200  
4. **Save**.
5. Check **Total**: It should equal the sum of all charge fields you filled (and others if you entered them).
6. **Planning / Average costing** (in **Shipping Details** or main form):
   - **For Planing Costing** and **Average For Costing** should update based on **Total** and **QTY (KG)** (e.g. Total / QTY (KG) when QTY > 0).

---

## 6. Test BRC Section

1. In the same record, go to **BRC Details** tab.
2. Set:
   - **BRC Status**: YES.
   - **BRC Date**: Any date.
   - **BRC No**: e.g. `BRC-2024-001`.
   - **BRC Amount USD**: e.g. 10000 (or same as Invoice Amount for full realization).
3. **Save**.
4. Check **Still in Realization**: It should be **Invoice Amount (USD) − BRC Amount USD** (e.g. 0 if you entered the same amount).

---

## 7. Test Drawback (DBK) and RODTEP

1. **Drawback (DBK)** tab:
   - **DBK %**: YES/NO.
   - **DBK Claimed**: YES/NO.
   - Enter **FOB value (INR)** (e.g. in Invoice Details or BRC section if you have such a field there) or **SB FOB value**.
   - **DBK as Per Calculation**: Should compute (e.g. 4% of FOB when applicable); **DBK Amount** can be manual.
2. **RODTEP** tab:
   - **RODTEP Amount**: Should compute from FOB (placeholder formula in module).
   - **RODTEP AMOUNT PER SB**: Manual.

---

## 8. Test CHA Invoice and Net Balance

1. Open **CHA Invoice** tab.
2. Enter:
   - **Tax Able Amt**: e.g. 10000.
   - **GST Amt**: e.g. 1800.
3. **Save**.
4. Check **Net Balance Payable**: Should be **Tax Able Amt + GST Amt** (e.g. 11800).

---

## 9. Test List (Tree) View and Search

1. Go back to **SB/BRC Master Report** list.
2. **Sort**: Click column headers (Date, SB No, Buyer, etc.) and confirm sort order changes.
3. **Search**:
   - Use the search bar: type invoice number, SB No, buyer name, BRC No, etc.
   - Results should filter accordingly.
4. **Filters** (if available in your view):
   - e.g. “BRC Received” (BRC Status = YES), “BRC Pending” (BRC Status = NO).
   - Apply and confirm list updates.
5. **Group By** (if available):
   - Group by Date, Invoice, BRC Status, Country, or CHA and confirm grouping.

---

## 10. Test Multiple Records and Serial Number

1. Create 2–3 more records (with or without invoice).
2. Check:
   - **Sr. No.** increments (2, 3, 4…).
   - Each record has its own Date, Invoice (optional), and BRC/charges data.
3. Delete one record (if your rights allow) and create another; **Sr. No.** should continue from the last used number (e.g. 5).

---

## 11. Access Rights (Optional)

1. Log in as a **basic User** (no “Settings” access):
   - User should see **SB/BRC Master** → **SB/BRC Master Report** and create/edit/delete as per `ir.model.access.csv`.
2. Log in as **Administrator**:
   - Same or more access; no regression.

---

## 12. Quick Checklist

- [ ] Module installs without error.
- [ ] Menu **SB/BRC Master** → **SB/BRC Master Report** is visible.
- [ ] Create record without invoice: Sr. No. and Date work.
- [ ] Create record with one invoice: Consignee, Buyer, Currency, Invoice Amount, QTY, Unit Rate, Amount (INR) behave correctly.
- [ ] Create record with **multiple invoices** (same SB): Invoice Amount = sum of totals, QTY = sum of quantities, Consignee/Buyer show first or “Multiple”.
- [ ] Charges tab: Total equals sum of charge fields.
- [ ] BRC tab: Still in Realization = Invoice Amount USD − BRC Amount USD.
- [ ] CHA Invoice tab: Net Balance Payable = Tax Able Amt + GST Amt.
- [ ] List view: sort, search, and filters work.
- [ ] Serial number auto-increments for new records.

---

## Troubleshooting

| Issue | What to check |
|-------|----------------|
| Module not in Apps list | Update Apps List; ensure module is in `addons_path` (e.g. `custom_addons/OdooERP`). |
| “No module named …” or import error | Dependencies: `account`, `sale`, `stock`, `product` installed. |
| SB No / Shipping Bill not filling | Install/use **l10n_in** and set Shipping Bill number on the invoice (Indian localization). |
| Related fields empty after selecting invoice | Save the record or click outside the Invoice field; check that the invoice is posted. |
| Total or other computed field wrong | Ensure all charge fields use the same currency (company currency). |
| Permission error | Check `security/ir.model.access.csv` and user’s groups. |

---

If you want, these steps can be turned into automated tests (e.g. Python unit tests or Odoo tours) for regression testing.
