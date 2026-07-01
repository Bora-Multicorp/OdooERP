# Report Source – Otek Purchase Order Report (PU-001)

**Structure:** Row 3 = Description / calculation information. Row 4 = Column name. Data from Row 5.  
**Total:** 17 columns.

| # | Row 3 (Description / Calculation) | Row 4 (Column name) |
|---|----------------------------------|---------------------|
| 1 | Purchase order name (clickable) | PO Number |
| 2 | Vendor Name | Supplier |
| 3 | Name of the product category | Product Category |
| 4 | Name of the product | Product |
| 5 | Total Qty Ordered against all POs for that product | Qty |
| 6 | Currency rate from the PO multiplied by unit price | FOB |
| 7 | Currency rate × Qty | Amount |
| 8 | Total Payment against the PO | Payment |
| 9 | Amount − Payment | Balance |
| 10 | Exchange rate × Amount | INR Amount |
| 11 | Editable field | Freight+Ins. |
| 12 | Editable field | BCD |
| 13 | Editable field | SWS |
| 14 | Pull from Purchase order (tax) | IGST |
| 15 | Editable field | Fine + Interest |
| 16 | Sum of Freight+Ins., BCD, SWS, IGST and Fine + Interest | Total exp. |
| 17 | (Total exp. + INR Amount) ÷ Qty | Per Pc. Landed |

**Editable fields (in list view):** Freight+Ins., BCD, SWS, IGST, Fine + Interest.  
**PO Number:** Many2one to purchase.order — clickable to open the PO.
