# -*- coding: utf-8 -*-
from odoo import api, fields, models

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    made_in_country_id = fields.Many2one(
        comodel_name='res.country',
        string='Made In',
        help='Country of origin for this line (e.g. Made in India). Shown on delivery and SO/PO PDFs.',
    )

    def _is_advance_payment_product(self):
        """Check if this line's product is the advance payment product."""
        return (
            self.product_id
            and self.product_id.product_tmpl_id.is_advance_payment_product
        )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if not record.is_downpayment and record._is_advance_payment_product():
                record.sudo().write({'is_downpayment': True})
        return records

    def write(self, vals):
        result = super().write(vals)
        if 'product_id' in vals or 'is_downpayment' in vals:
            for record in self:
                if not record.is_downpayment and record._is_advance_payment_product():
                    super(SaleOrderLine, record).write({'is_downpayment': True})
        return result

    def _prepare_procurement_values(self, group_id=False):
        values = super()._prepare_procurement_values(group_id=group_id)
        if self.made_in_country_id:
            values['made_in_country_id'] = self.made_in_country_id.id
        return values
