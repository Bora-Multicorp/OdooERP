# -*- coding: utf-8 -*-

from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('tax_id')
    def _onchange_tax_id_no_tax_order(self):
        """If order has No Tax checked, do not allow tax on line."""
        if self.order_id and self.order_id.ks_no_tax_allowed and self.tax_id:
            self.tax_id = [(5, 0, 0)]

    def write(self, vals):
        res = super().write(vals)
        # When order has No Tax, ensure no tax remains on lines (e.g. after write with tax_id)
        if vals.get('tax_id') or 'tax_id' not in vals:
            no_tax_lines = self.filtered(lambda l: l.order_id.ks_no_tax_allowed and l.tax_id)
            if no_tax_lines:
                super(SaleOrderLine, no_tax_lines).write({'tax_id': [(5, 0, 0)]})
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """When creating lines for an order with No Tax, ensure no tax is set."""
        for vals in vals_list:
            if vals.get('order_id') and vals.get('tax_id'):
                order = self.env['sale.order'].browse(vals['order_id'])
                if order.ks_no_tax_allowed:
                    vals['tax_id'] = [(5, 0, 0)]
        return super().create(vals_list)
