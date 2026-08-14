# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class KsSalePriceWarningWizard(models.TransientModel):
    _name = 'ks.sale.price.warning.wizard'
    _description = 'KS Sale Price Below Purchase Warning Wizard'

    ks_sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        required=True,
        ondelete='cascade',
    )
    ks_warning_message = fields.Text(
        string='Warning Message',
        readonly=True,
    )

    def action_continue(self):
        """Continue with order creation / confirmation, bypassing price warning prompt."""
        self.ensure_one()
        order = self.ks_sale_order_id
        return order.with_context(bypass_price_warning=True).action_confirm()
