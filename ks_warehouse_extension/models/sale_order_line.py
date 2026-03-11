# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

from .sale_order import KS_DUBAI_CASH_HANDLING_PERCENT


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_cash_handling_charge = fields.Boolean(
        string='Is Cash Handling Charge',
        compute='_compute_is_cash_handling_charge',
        store=False,
    )
    is_cash_handling_rate_deviation = fields.Boolean(
        string='Cash Handling Rate Changed',
        compute='_compute_is_cash_handling_rate_deviation',
        store=False,
        help='True when Dubai cash handling charge line percentage differs from default 1.2%.',
    )

    @api.depends('product_id', 'order_id.ks_zone')
    def _compute_is_cash_handling_charge(self):
        template = self.env.ref(
            'ks_warehouse_extension.product_template_cash_handling_charges',
            raise_if_not_found=False
        )
        variant = template.product_variant_ids[:1] if template else self.env['product.product']
        for line in self:
            line.is_cash_handling_charge = bool(
                line.product_id and variant and line.product_id == variant
            )

    @api.depends('price_subtotal', 'order_id.amount_untaxed', 'is_cash_handling_charge')
    def _compute_is_cash_handling_rate_deviation(self):
        for line in self:
            if not line.is_cash_handling_charge or not line.order_id or line.order_id.amount_untaxed == 0:
                line.is_cash_handling_rate_deviation = False
                continue
            effective_pct = (line.price_subtotal / line.order_id.amount_untaxed) * 100.0
            line.is_cash_handling_rate_deviation = abs(
                effective_pct - KS_DUBAI_CASH_HANDLING_PERCENT
            ) > 0.01
