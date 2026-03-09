# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    ks_zone = fields.Selection([
        ('russia', 'Russia'),
        ('india', 'India'),
        ('dubai', 'Dubai'),
        ('sez', 'Sez'),
    ], string='Zone', required=True, default='india',
       help='Select the zone for this purchase order.',
       tracking=True)

    ks_no_tax_allowed = fields.Boolean(
        string='No Tax',
        default=False,
        help='If checked, no tax can be applied on order lines; existing line taxes are cleared.',
        tracking=True,
    )

    @api.onchange('ks_no_tax_allowed')
    def _onchange_ks_no_tax_allowed_clear_tax(self):
        """When No Tax is ticked, remove tax from all order lines."""
        if self.ks_no_tax_allowed and self.order_line:
            for line in self.order_line:
                if line.taxes_id:
                    line.taxes_id = [(5, 0, 0)]

    def write(self, vals):
        """Clear line taxes when No Tax is set; prevent changing ks_zone once order is in purchase/done state."""
        if vals.get('ks_no_tax_allowed'):
            for order in self:
                lines_with_tax = order.order_line.filtered(lambda l: l.taxes_id)
                if lines_with_tax:
                    lines_with_tax.write({'taxes_id': [(5, 0, 0)]})
        if 'ks_zone' in vals:
            for order in self:
                if order.state in ('purchase', 'done'):
                    raise UserError(_('Zone cannot be changed once the purchase order is confirmed.'))
        return super().write(vals)

    def button_confirm(self):
        """Validate no tax when flag set before confirming"""
        for order in self:
            if order.ks_no_tax_allowed:
                lines_with_tax = order.order_line.filtered(
                    lambda l: l.taxes_id
                )
                if lines_with_tax:
                    raise ValidationError(_(
                        'Tax is not allowed on this order (No Tax is checked). '
                        'Please remove tax from the following line(s): %s'
                    ) % ', '.join(lines_with_tax.mapped('name') or lines_with_tax.mapped('product_id.name')))
        return super().button_confirm()
