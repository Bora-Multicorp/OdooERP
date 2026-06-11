# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    ks_is_advance_line = fields.Boolean(
        string='Is Advance Deduction Line',
        compute='_compute_ks_is_advance_line',
        store=True,
    )

    @api.depends('product_id', 'product_id.product_tmpl_id.is_advance_payment_product')
    def _compute_ks_is_advance_line(self):
        for line in self:
            line.ks_is_advance_line = bool(
                line.product_id and line.product_id.product_tmpl_id.is_advance_payment_product
            )

    def write(self, vals):
        if self.env.context.get('ks_check_advance_line'):
            editable_fields = {'sequence', 'display_type', 'name'}
            restricted = set(vals.keys()) - editable_fields
            if restricted:
                for line in self:
                    if line.ks_is_advance_line:
                        raise UserError(_(
                            'Advance payment deduction lines cannot be edited.'
                        ))
        return super().write(vals)
