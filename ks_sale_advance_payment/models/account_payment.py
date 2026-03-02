# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # Link to Sale Order for advance payments
    ks_sale_order_id = fields.Many2one(
        comodel_name='sale.order',
        string='Sale Order',
        copy=False,
        help='The Sale Order this advance payment is linked to',
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        payments = super().create(vals_list)
        payments._invalidate_sale_order_advance_amount()
        return payments

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ('ks_sale_order_id', 'amount', 'state', 'currency_id')):
            self._invalidate_sale_order_advance_amount()
        return res

    def unlink(self):
        orders = self.mapped('ks_sale_order_id').filtered('id')
        res = super().unlink()
        if orders:
            orders._compute_ks_advance_payment_amount()
        return res

    def _invalidate_sale_order_advance_amount(self):
        """Recompute advance payment amount on linked sale orders so the UI and stored value update."""
        orders = self.mapped('ks_sale_order_id').filtered('id')
        if orders:
            orders._compute_ks_advance_payment_amount()

