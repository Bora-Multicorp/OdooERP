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
