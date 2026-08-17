# -*- coding: utf-8 -*-
from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def get_grn_summary(self):
        """
        Calculate GRN amounts based on received quantities.

        Returns:
            {
                'gross_amount': float,
                'discount_amount': float,
                'subtotal': float,
                'gst_summary': [
                    {
                        'name': str,
                        'rate': float,
                        'amount': float,
                    }
                ],
                'tax_amount': float,
                'round_off': float,
                'total_amount': float,
            }
        """
        self.ensure_one()

        currency = self.purchase_id.currency_id
        gross_amount = 0.0
        discount_amount = 0.0
        tax_amounts = {}

        def get_tax_type(tax):
            if getattr(tax, "l10n_in_tax_type", False):
                return tax.l10n_in_tax_type

            name = (tax.name or "").lower()

            if "igst" in name:
                return "igst"
            elif "cgst" in name:
                return "cgst"
            elif "sgst" in name or "utgst" in name:
                return "sgst"

            return None

        def fmt_rate(rate):
            return (
                f"{rate:.1f}".rstrip("0").rstrip(".")
                if rate % 1
                else f"{rate:.0f}"
            )

        # ---------------------------------------------------------
        # RECEIVED LINES
        # ---------------------------------------------------------
        for move in self.move_ids_without_package.filtered(
            lambda m: m.quantity and m.purchase_line_id
        ):
            purchase_line = move.purchase_line_id

            qty = move.quantity or 0.0
            price_unit = purchase_line.price_unit or 0.0
            discount = purchase_line.discount or 0.0

            # Gross amount before discount
            line_gross = qty * price_unit
            gross_amount += line_gross

            # Discount amount
            line_discount = line_gross * discount / 100.0
            discount_amount += line_discount

            # Net amount after discount
            line_net = line_gross - line_discount

            # -----------------------------------------------------
            # TAX
            # Calculate tax on received quantity after discount
            # -----------------------------------------------------
            taxes = purchase_line.taxes_id.compute_all(
                line_net / qty if qty else 0.0,
                currency=currency,
                quantity=qty,
                product=purchase_line.product_id,
                partner=self.partner_id,
            )

            for tax_vals in taxes.get("taxes", []):
                tax = self.env["account.tax"].browse(tax_vals["id"])

                tax_type = get_tax_type(tax)

                if not tax_type:
                    continue

                key = (tax_type, tax.amount)

                if key not in tax_amounts:
                    tax_amounts[key] = {
                        "tax": tax,
                        "amount": 0.0,
                        "tax_type": tax_type,
                    }

                tax_amounts[key]["amount"] += tax_vals["amount"]

        # ---------------------------------------------------------
        # SUBTOTAL
        # ---------------------------------------------------------
        subtotal = gross_amount - discount_amount

        # ---------------------------------------------------------
        # SEPARATE GST TYPES
        # ---------------------------------------------------------
        cgst = {}
        sgst = {}
        igst = {}

        for (tax_type, rate), values in tax_amounts.items():
            if tax_type == "cgst":
                cgst[rate] = values

            elif tax_type == "sgst":
                sgst[rate] = values

            elif tax_type == "igst":
                igst[rate] = values

        gst_summary = []

        # ---------------------------------------------------------
        # CGST + SGST AT SAME RATE
        # Same naming format as Purchase Order
        # ---------------------------------------------------------
        all_rates = sorted(set(cgst) | set(sgst))

        for rate in all_rates:
            cgst_data = cgst.get(rate)
            sgst_data = sgst.get(rate)

            if cgst_data and sgst_data:
                gst_summary.append({
                    "name": (
                        "Input SGST/UTGST @%s%% + "
                        "Input CGST @%s%%"
                    ) % (
                        fmt_rate(rate),
                        fmt_rate(rate),
                    ),
                    "rate": rate,
                    "amount": (
                        cgst_data["amount"]
                        + sgst_data["amount"]
                    ),
                })

            elif cgst_data:
                gst_summary.append({
                    "name": "Input CGST @%s%%" % fmt_rate(rate),
                    "rate": rate,
                    "amount": cgst_data["amount"],
                })

            elif sgst_data:
                gst_summary.append({
                    "name": "Input SGST/UTGST @%s%%" % fmt_rate(rate),
                    "rate": rate,
                    "amount": sgst_data["amount"],
                })

        # ---------------------------------------------------------
        # IGST
        # Same naming format as Purchase Order
        # ---------------------------------------------------------
        for rate, values in sorted(igst.items()):
            gst_summary.append({
                "name": "Input IGST @%s%%" % fmt_rate(rate),
                "rate": rate,
                "amount": values["amount"],
            })

        # ---------------------------------------------------------
        # TOTAL TAX
        # ---------------------------------------------------------
        tax_amount = sum(
            row["amount"]
            for row in gst_summary
        )

        # ---------------------------------------------------------
        # ROUND OFF
        # Positive round-off is treated as a deduction
        # ---------------------------------------------------------
        round_off = self.purchase_id.ks_round_off or 0.0

        # ---------------------------------------------------------
        # FINAL TOTAL
        # ---------------------------------------------------------
        total_amount = subtotal + tax_amount - round_off

        return {
            "gross_amount": gross_amount,
            "discount_amount": discount_amount,
            "subtotal": subtotal,
            "gst_summary": gst_summary,
            "tax_amount": tax_amount,
            "round_off": round_off,
            "total_amount": total_amount,
        }