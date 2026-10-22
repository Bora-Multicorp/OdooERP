# -*- coding: utf-8 -*-

from odoo import api, fields, models


class StockValuationLayer(models.Model):
    _inherit = "stock.valuation.layer"

    value_usd = fields.Monetary(
        string="Value (USD)",
        compute="_compute_value_usd",
        currency_field="usd_currency_id",
        readonly=True,
    )
    usd_currency_id = fields.Many2one(
        "res.currency",
        string="USD",
        compute="_compute_usd_currency",
        readonly=True,
    )
    latest_purchase_price = fields.Float(
        string="Latest Purchase Price",
        compute="_compute_latest_prices_and_values",
        digits="Product Price",
        readonly=True,
    )
    latest_sales_price = fields.Float(
        string="Latest Sales Price",
        compute="_compute_latest_prices_and_values",
        digits="Product Price",
        readonly=True,
    )
    latest_sales_price_value = fields.Monetary(
        string="Latest Sales Price Value",
        compute="_compute_latest_prices_and_values",
        currency_field="currency_id",
        readonly=True,
    )

    @api.depends("product_id", "remaining_qty")
    def _compute_latest_prices_and_values(self):
        products = self.mapped("product_id")
        latest_sales_prices = {}
        latest_purchase_prices = {}
        if products:
            for product in products:
                if hasattr(product, "latest_purchase_price"):
                    latest_purchase_prices[product.id] = product.latest_purchase_price
                if hasattr(product, "latest_sales_price"):
                    latest_sales_prices[product.id] = product.latest_sales_price

            missing_sale_pids = [pid for pid in products.ids if pid not in latest_sales_prices]
            if missing_sale_pids:
                so_lines = self.env["sale.order.line"].search([
                    ("product_id", "in", missing_sale_pids),
                    ("state", "in", ["sale", "done"]),
                ])
                so_lines = so_lines.sorted(key=lambda l: (l.order_id.date_order or l.create_date, l.id), reverse=True)
                for line in so_lines:
                    if line.product_id.id not in latest_sales_prices:
                        latest_sales_prices[line.product_id.id] = line.price_unit

            missing_po_pids = [pid for pid in products.ids if pid not in latest_purchase_prices]
            if missing_po_pids:
                po_lines = self.env["purchase.order.line"].search([
                    ("product_id", "in", missing_po_pids),
                    ("state", "in", ["purchase", "done"]),
                ], order="date_approve desc, date_order desc, id desc")
                for line in po_lines:
                    if line.product_id.id not in latest_purchase_prices:
                        latest_purchase_prices[line.product_id.id] = line.price_unit

        for layer in self:
            s_price = latest_sales_prices.get(layer.product_id.id, 0.0)
            p_price = latest_purchase_prices.get(layer.product_id.id, 0.0)
            layer.latest_sales_price = s_price
            layer.latest_purchase_price = p_price
            layer.latest_sales_price_value = s_price * (layer.remaining_qty or 0.0)

    @api.depends()
    def _compute_usd_currency(self):
        usd = self.env.ref("base.USD", raise_if_not_found=False) or self.env["res.currency"].search(
            [("name", "=", "USD")], limit=1
        )
        for layer in self:
            layer.usd_currency_id = usd

    @api.depends("value", "currency_id", "company_id")
    def _compute_value_usd(self):
        usd = self.env.ref("base.USD", raise_if_not_found=False) or self.env["res.currency"].search(
            [("name", "=", "USD")], limit=1
        )
        if not usd:
            for layer in self:
                layer.value_usd = 0.0
            return
        today = fields.Date.context_today(self)
        for layer in self:
            if not layer.currency_id or layer.currency_id == usd:
                layer.value_usd = layer.value or 0.0
            else:
                try:
                    layer.value_usd = layer.currency_id._convert(
                        layer.value or 0.0,
                        usd,
                        company=layer.company_id,
                        date=today,
                    )
                except Exception:
                    layer.value_usd = 0.0
