# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare, float_round


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    discount_amount = fields.Monetary(
        string='Discount Amount',
        currency_field='currency_id',
        compute='_compute_discount_amount',
        inverse='_inverse_discount_amount',
        store=True,
        readonly=False,
    )

    @api.depends('product_qty', 'product_uom', 'company_id', 'order_id.partner_id', 'discount_amount')
    def _compute_price_unit_and_date_planned_and_name(self):
        # Run standard Odoo seller pricelist and vendor evaluation logic
        super()._compute_price_unit_and_date_planned_and_name()
        for line in self:
            base_amount = line.price_unit * line.product_qty
            # Override percentage discount if custom discount_amount is present
            if base_amount > 0 and line.discount_amount:
                discount_pct = (line.discount_amount / base_amount) * 100.0
                line.discount = float_round(discount_pct, precision_digits=2)

    @api.depends('price_unit', 'product_qty', 'discount')
    def _compute_discount_amount(self):
        """Compute discount amount when price, quantity, or discount % changes."""
        for line in self:
            base_amount = line.price_unit * line.product_qty
            precision = line.currency_id.rounding or 0.01
            if line.discount and base_amount:
                amt = base_amount * (line.discount / 100.0)
                line.discount_amount = float_round(amt, precision_rounding=precision)
            else:
                line.discount_amount = 0.0

    def _inverse_discount_amount(self):
        """Set percentage discount when discount amount is typed manually."""
        for line in self:
            base_amount = line.price_unit * line.product_qty
            if base_amount > 0 and line.discount_amount:
                discount_pct = (line.discount_amount / base_amount) * 100.0
                line.discount = float_round(discount_pct, precision_digits=2)
            elif not line.discount_amount:
                line.discount = 0.0

    @api.constrains('discount_amount', 'price_unit', 'product_qty')
    def _check_discount_amount(self):
        """Ensure discount amount is non-negative and within line total limit."""
        for line in self:
            precision = line.currency_id.rounding or 0.01
            base_amount = line.price_unit * line.product_qty
            if float_compare(line.discount_amount, 0.0, precision_rounding=precision) < 0:
                raise ValidationError(_("Discount amount cannot be negative."))
            if base_amount > 0 and float_compare(line.discount_amount, base_amount, precision_rounding=precision) > 0:
                raise ValidationError(_("Discount amount cannot exceed the line's total price."))

    def _prepare_account_move_line(self, move=False):
        """Pass discount percentage and discount amount to the Vendor Bill line."""
        res = super()._prepare_account_move_line(move=move)
        res['discount'] = self.discount
        res['discount_amount'] = self.discount_amount or 0.0
        return res