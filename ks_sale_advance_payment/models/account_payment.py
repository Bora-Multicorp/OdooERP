# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


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
        # Block any modification to posted advance payments linked to a sale order
        locked = self.filtered(lambda p: p.ks_sale_order_id and p.state == 'posted')
        # Allow only internal state transitions (e.g. reconciliation sets state='paid')
        editable_keys = {'state', 'is_matched', 'is_reconciled', 'reconciled_bill_ids',
                         'reconciled_invoice_ids', 'reconciled_invoices_count',
                         'reconciled_bills_count', 'move_id'}
        if locked and not set(vals.keys()).issubset(editable_keys):
            raise UserError(_(
                'Advance payments linked to a Sale Order cannot be modified once posted.'
            ))
        res = super().write(vals)
        if any(f in vals for f in ('ks_sale_order_id', 'amount', 'state', 'currency_id')):
            self._invalidate_sale_order_advance_amount()
        return res

    def action_draft(self):
        # Prevent resetting advance payments to draft
        if self.filtered(lambda p: p.ks_sale_order_id):
            raise UserError(_(
                'Advance payments linked to a Sale Order cannot be reset to draft.'
            ))
        return super().action_draft()

    def unlink(self):
        if self.filtered(lambda p: p.ks_sale_order_id and p.state == 'posted'):
            raise UserError(_(
                'Posted advance payments linked to a Sale Order cannot be deleted.'
            ))
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

