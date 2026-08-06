# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

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
        if template:
            template = template.sudo()
        variant = template.product_variant_ids[:1] if template else self.env['product.product']
        for line in self:
            line.is_cash_handling_charge = bool(
                line.product_id and variant and line.product_id == variant
            )

    def _ks_get_cash_handling_product(self):
        template = self.env.ref(
            'ks_warehouse_extension.product_template_cash_handling_charges',
            raise_if_not_found=False,
        )
        if not template:
            return self.env['product.product']
        template = template.sudo()
        if not template.product_variant_ids:
            return self.env['product.product']
        return template.product_variant_ids[0].sudo()

    @api.onchange('product_id')
    def _onchange_product_id_check_cash_handling(self):
        product = self._ks_get_cash_handling_product()
        if not product:
            return
        if self.product_id == product and getattr(self.order_id, 'ks_zone', None) != 'dubai':
            self.product_id = False
            return {
                'warning': {
                    'title': _('Product Not Available'),
                    'message': _('Cash handling charges can only be added to Dubai zone orders.'),
                }
            }

    @api.constrains('product_id', 'order_id')
    def _check_cash_handling_zone(self):
        product = self._ks_get_cash_handling_product()
        if not product:
            return
        for line in self:
            if (line.product_id == product
                    and getattr(line.order_id, 'ks_zone', None) != 'dubai'):
                raise ValidationError(_(
                    'Cash handling charges can only be added to Dubai zone orders.'
                ))

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
