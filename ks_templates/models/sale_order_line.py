# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    made_in_country_id = fields.Many2one(
        comodel_name='res.country',
        string='Made In',
        help='Country of origin for this line (e.g. Made in India). Shown on delivery and SO/PO PDFs.',
    )

    def _prepare_procurement_values(self, group_id=False):
        values = super()._prepare_procurement_values(group_id=group_id)
        if self.made_in_country_id:
            values['made_in_country_id'] = self.made_in_country_id.id
        return values
