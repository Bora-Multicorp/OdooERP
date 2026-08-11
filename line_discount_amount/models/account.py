# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare, float_round

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    discount = fields.Float(
        string='Discount (%)',
        digits='Discount',
        compute='_compute_discount',
        inverse='_inverse_discount',
        store=True,
        readonly=False,
    )
    discount_amount = fields.Monetary(
        string='Discount Amount',
        currency_field='currency_id',
        help="Fixed discount amount applied to the invoice line.",
        compute='_compute_discount_amount',
        inverse='_inverse_discount_amount',
        store=True,
        readonly=False,
    )

    @api.depends('price_unit', 'quantity', 'discount_amount')
    def _compute_discount(self):
        for line in self:
            base_amount = line.price_unit * line.quantity
            if base_amount > 0 and line.discount_amount:
                discount_pct = (line.discount_amount / base_amount) * 100.0
                line.discount = float_round(discount_pct, precision_digits=2)
            elif not line.discount_amount:
                line.discount = 0.0

    def _inverse_discount(self):
        """Allows direct editing of discount %."""
        for line in self:
            base_amount = line.price_unit * line.quantity
            precision = line.currency_id.rounding or 0.01
            if line.discount and base_amount:
                amt = base_amount * (line.discount / 100.0)
                line.discount_amount = float_round(amt, precision_rounding=precision)
            else:
                line.discount_amount = 0.0

    @api.depends('price_unit', 'quantity', 'discount_amount')
    def _compute_discount(self):
        """Recompute discount % when discount_amount or line values change."""
        for line in self:
            base_amount = line.price_unit * line.quantity
            if base_amount > 0 and line.discount_amount:
                discount_pct = (line.discount_amount / base_amount) * 100.0
                line.discount = float_round(discount_pct, precision_digits=2)

    @api.depends('price_unit', 'quantity', 'discount')
    def _compute_discount_amount(self):
        """Compute discount amount based on percentage discount."""
        for line in self:
            base_amount = line.price_unit * line.quantity
            precision = line.currency_id.rounding or 0.01
            if line.discount and base_amount:
                amt = base_amount * (line.discount / 100.0)
                line.discount_amount = float_round(amt, precision_rounding=precision)
            else:
                line.discount_amount = 0.0

    def _inverse_discount_amount(self):
        """Set percentage discount when discount amount is typed manually."""
        for line in self:
            base_amount = line.price_unit * line.quantity
            if base_amount > 0 and line.discount_amount:
                discount_pct = (line.discount_amount / base_amount) * 100.0
                line.discount = float_round(discount_pct, precision_digits=2)
            else:
                line.discount = 0.0

    # 4. CONSTRAINS FOR VALIDATION
    @api.constrains('discount_amount', 'price_unit', 'quantity')
    def _check_discount_amount(self):
        """Ensure discount amount is non-negative and within line total limit."""
        for line in self:
            precision = line.currency_id.rounding or 0.01
            base_amount = line.price_unit * line.quantity
            if float_compare(line.discount_amount, 0.0, precision_rounding=precision) < 0:
                raise ValidationError(_("Discount amount cannot be negative."))
            if base_amount > 0 and float_compare(line.discount_amount, base_amount, precision_rounding=precision) > 0:
                raise ValidationError(_("Discount amount cannot exceed the line's total price."))