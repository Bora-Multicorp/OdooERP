# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    latest_purchase_price = fields.Float(
        string='Latest Purchase Price',
        compute='_compute_latest_purchase_price',
        digits='Product Price',
        help='Latest unit price from confirmed purchase orders.',
    )

    def _compute_latest_purchase_price(self):
        po_lines = self.env['purchase.order.line'].search([
            ('product_id', 'in', self.ids),
            ('state', 'in', ['purchase', 'done']),
        ], order='date_approve desc, date_order desc, id desc')

        latest_prices = {}
        for line in po_lines:
            if line.product_id.id not in latest_prices:
                latest_prices[line.product_id.id] = line.price_unit

        for product in self:
            product.latest_purchase_price = latest_prices.get(product.id, 0.0)
