# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    ks_latest_purchase_price = fields.Monetary(
        string='Latest Purchase Price (Base)',
        currency_field='ks_latest_purchase_currency_id',
        copy=False,
        company_dependent=True,
        help='Last purchase unit price in base (company) currency, updated when a Purchase Order is confirmed.',
    )
    ks_latest_purchase_currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Latest Purchase Currency',
        copy=False,
        company_dependent=True,
        help='Currency of the latest purchase price (base/company currency at time of purchase).',
    )


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    ks_latest_purchase_price = fields.Monetary(
        string='Latest Purchase Price (Base)',
        currency_field='ks_latest_purchase_currency_id',
        compute='_compute_ks_latest_purchase_price',
        store=False,
        help='Latest purchase price (base) from any variant. Read-only; stored per variant on product.product.',
    )
    ks_latest_purchase_currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Latest Purchase Currency',
        compute='_compute_ks_latest_purchase_price',
        store=False,
    )

    @api.depends('product_variant_ids.ks_latest_purchase_price', 'product_variant_ids.ks_latest_purchase_currency_id')
    @api.depends_context('company')
    def _compute_ks_latest_purchase_price(self):
        """Show minimum latest purchase price across variants for display on template."""
        for tmpl in self:
            variants = tmpl.product_variant_ids.filtered(lambda p: p.ks_latest_purchase_price)
            if not variants:
                tmpl.ks_latest_purchase_price = 0.0
                tmpl.ks_latest_purchase_currency_id = False
                continue
            # Use first variant's currency; if multiple currencies, take first variant's value for display
            first = variants[0]
            tmpl.ks_latest_purchase_currency_id = first.ks_latest_purchase_currency_id
            if first.ks_latest_purchase_currency_id:
                prices = []
                for v in variants:
                    if v.ks_latest_purchase_currency_id == first.ks_latest_purchase_currency_id:
                        prices.append(v.ks_latest_purchase_price)
                tmpl.ks_latest_purchase_price = min(prices) if prices else 0.0
            else:
                tmpl.ks_latest_purchase_price = 0.0
