# -*- coding: utf-8 -*-

from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Link to originating Sale Order (from ks_sale_order stock flow)
    ks_source_sale_order_id = fields.Many2one(
        'sale.order',
        string='Source Sale Order',
        copy=False,
        help='Sale Order that triggered the creation of this Purchase Order due to insufficient stock'
    )

    def action_view_source_sale_order(self):
        """Open the source Sale Order"""
        self.ensure_one()
        if not self.ks_source_sale_order_id:
            return False

        return {
            'name': 'Source Sale Order',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.ks_source_sale_order_id.id,
            'target': 'current',
        }
