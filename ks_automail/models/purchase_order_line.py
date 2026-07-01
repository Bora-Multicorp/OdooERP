# -*- coding: utf-8 -*-

from odoo import api, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.onchange('taxes_id')
    def _onchange_taxes_id_no_tax_order(self):
        """If order has No Tax checked, do not allow tax on line."""
        if self.order_id and self.order_id.ks_no_tax_allowed and self.taxes_id:
            self.taxes_id = [(5, 0, 0)]

    def write(self, vals):
        res = super().write(vals)
        # When order has No Tax, ensure no tax remains on lines
        no_tax_lines = self.filtered(lambda l: l.order_id.ks_no_tax_allowed and l.taxes_id)
        if no_tax_lines:
            super(PurchaseOrderLine, no_tax_lines).write({'taxes_id': [(5, 0, 0)]})
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """When creating lines for an order with No Tax, ensure no tax is set."""
        for vals in vals_list:
            if vals.get('order_id') and vals.get('taxes_id'):
                order = self.env['purchase.order'].browse(vals['order_id'])
                if order.ks_no_tax_allowed:
                    vals['taxes_id'] = [(5, 0, 0)]
        return super().create(vals_list)
