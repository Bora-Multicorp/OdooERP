# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare, float_round

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    discount_amount = fields.Monetary(
        string='Discount Amount',
        currency_field='currency_id',
        help="Discount amount applied to the line.",
        compute='_compute_discount_amount',
        inverse='_inverse_discount_amount',
        store=True,
        readonly=False
    )

    @api.depends('product_id', 'product_uom', 'product_uom_qty', 'discount_amount')
    def _compute_discount(self):
        super()._compute_discount()
        for line in self:
            base_amount = line.price_unit * line.product_uom_qty
            # If user entered a discount_amount, override discount % with calculated amount
            if base_amount > 0 and line.discount_amount:
                discount_pct = (line.discount_amount / base_amount) * 100.0
                line.discount = float_round(discount_pct, precision_digits=2)

    @api.depends('price_unit', 'product_uom_qty', 'discount')
    def _compute_discount_amount(self):
        """Compute discount amount based on percentage discount."""
        for line in self:
            base_amount = line.price_unit * line.product_uom_qty
            precision = line.currency_id.rounding or 0.01
            if line.discount and base_amount:
                discount_amount = base_amount * (line.discount / 100.0)
                line.discount_amount = float_round(discount_amount, precision_rounding=precision)
            else:
                line.discount_amount = 0.0

    def _inverse_discount_amount(self):
        """Set percentage discount based on discount amount."""
        for line in self:
            base_amount = line.price_unit * line.product_uom_qty
            if base_amount > 0 and line.discount_amount:
                discount_percentage = (line.discount_amount / base_amount) * 100.0
                line.discount = float_round(discount_percentage, precision_digits=2)
            else:
                line.discount = 0.0

    @api.constrains('discount_amount', 'price_unit', 'product_uom_qty')
    def _check_discount_amount(self):
        """Ensure discount amount is not negative and does not exceed line total."""
        for line in self:
            precision = line.currency_id.rounding or 0.01
            base_amount = line.price_unit * line.product_uom_qty
            if float_compare(line.discount_amount, 0.0, precision_rounding=precision) < 0:
                raise ValidationError(_("Discount amount cannot be negative."))
            if base_amount > 0 and float_compare(line.discount_amount, base_amount, precision_rounding=precision) > 0:
                raise ValidationError(_("Discount amount cannot exceed the line's total price."))

    def _prepare_invoice_line(self, **optional_values):
        """Pass both discount percentage and discount amount to the invoice line."""
        res = super()._prepare_invoice_line(**optional_values)
        res['discount_amount'] = self.discount_amount or 0.0
        return res