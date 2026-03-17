# -*- coding: utf-8 -*-
from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    made_in_country_id = fields.Many2one(
        comodel_name='res.country',
        string='Made In',
        help='Country of origin for this line (e.g. Made in India). Shown on receipt and PO PDFs.',
    )

    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        vals = super()._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom)
        if self.made_in_country_id:
            vals['made_in_country_id'] = self.made_in_country_id.id
        return vals
