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
    latest_sales_price = fields.Float(
        string='Latest Sales Price',
        compute='_compute_latest_sales_price',
        digits='Product Price',
        help='Latest unit price from confirmed sales orders.',
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

    def _compute_latest_sales_price(self):
        so_lines = self.env['sale.order.line'].search([
            ('product_id', 'in', self.ids),
            ('state', 'in', ['sale', 'done']),
        ])
        so_lines = so_lines.sorted(key=lambda l: (l.order_id.date_order or l.create_date, l.id), reverse=True)

        latest_prices = {}
        for line in so_lines:
            if line.product_id.id not in latest_prices:
                latest_prices[line.product_id.id] = line.price_unit

        for product in self:
            product.latest_sales_price = latest_prices.get(product.id, 0.0)
