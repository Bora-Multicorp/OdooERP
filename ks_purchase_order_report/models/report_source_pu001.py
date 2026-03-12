# -*- coding: utf-8 -*-
# Report source: doc/REPORT_SOURCE_PU001.md
# Row 3 = description/calculation, Row 4 = column name. Data from Row 5.
# Single source of truth for list view labels, help texts, and Excel export.

# List of (row3_description, row4_column_name) in column order — 17 columns
PU001_COLUMNS = [
    ("Purchase order name (clickable)", "PO Number"),
    ("Vendor Name", "Supplier"),
    ("Name of the product category", "Product Category"),
    ("Name of the product", "Product"),
    ("Total Qty Ordered against all POs for that product", "Qty"),
    ("Currency rate from the PO multiplied by unit price", "FOB"),
    ("Currency rate × Qty", "Amount"),
    ("Total Payment against the PO", "Payment"),
    ("Amount − Payment", "Balance"),
    ("Exchange rate × Amount", "INR Amount"),
    ("Editable field", "Freight+Ins."),
    ("Editable field", "BCD"),
    ("Editable field", "SWS"),
    ("Pull from Purchase order (tax)", "IGST"),
    ("Editable field", "Fine + Interest"),
    ("Sum of Freight+Ins., BCD, SWS, IGST and Fine + Interest", "Total exp."),
    ("(Total exp. + INR Amount) ÷ Qty", "Per Pc. Landed"),
]

# For Excel: Row 3 texts, Row 4 headers (same order)
PU001_ROW3_DESCRIPTIONS = [t[0] for t in PU001_COLUMNS]
PU001_ROW4_HEADERS = [t[1] for t in PU001_COLUMNS]

# Field name (technical) in same order as columns
PU001_FIELD_NAMES = [
    "order_id",       # PO Number (clickable)
    "supplier",
    "product_categ",
    "product",
    "qty",
    "fob",
    "amount",
    "payment",
    "balance",
    "inr_amount",
    "freight_ins",
    "bcd",
    "sws",
    "igst",
    "fine_interest",
    "total_exp",
    "per_pc_landed_cost",
]

# Editable fields (user can change in list view)
PU001_EDITABLE_FIELDS = {"freight_ins", "bcd", "sws", "igst", "fine_interest"}
