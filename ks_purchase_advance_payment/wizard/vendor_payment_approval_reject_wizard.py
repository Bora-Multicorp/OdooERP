# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class VendorPaymentApprovalRejectWizard(models.TransientModel):
    _name = 'vendor.payment.approval.reject.wizard'
    _description = 'Reject Vendor Payment Request'

    reason = fields.Text(string='Rejection Reason', required=True)
    request_ids = fields.Many2many(
        'vendor.payment.approval.request',
        string='Requests',
        relation='vendor_payment_approval_reject_wizard_request_rel',
        column1='wizard_id',
        column2='request_id',
        help='Requests to reject (from context).',
    )
    payment_ids = fields.Many2many(
        'account.payment',
        string='Payments',
        relation='vendor_payment_approval_reject_wizard_payment_rel',
        column1='wizard_id',
        column2='payment_id',
        help='Payments to reject (from context).',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids')
        default_reqs = self.env.context.get('default_request_ids')
        default_pays = self.env.context.get('default_payment_ids')

        if default_pays or active_model == 'account.payment':
            if default_pays:
                res['payment_ids'] = default_pays
            elif active_ids:
                res['payment_ids'] = [(6, 0, active_ids)]
        elif default_reqs or active_model == 'vendor.payment.approval.request':
            if default_reqs:
                res['request_ids'] = default_reqs
            elif active_ids:
                res['request_ids'] = [(6, 0, active_ids)]
        elif active_ids:
            res['request_ids'] = [(6, 0, active_ids)]
        return res

    def action_reject(self):
        active_model = self.env.context.get('active_model')
        if self.payment_ids or active_model == 'account.payment':
            payments = self.payment_ids or self.env['account.payment'].browse(
                self.env.context.get('active_ids', [])
            )
            if not payments:
                raise UserError(_('No payments selected.'))
            pending = payments.filtered(lambda p: p.state == 'pending_approval')
            if not pending:
                raise UserError(_('None of the selected payments are in Pending Approval state.'))
            for pay in pending:
                pay._do_reject(self.reason)
            return {'type': 'ir.actions.act_window_close'}

        request_ids = self.request_ids or self.env['vendor.payment.approval.request'].browse(
            self.env.context.get('active_ids', [])
        )
        if not request_ids:
            raise UserError(_('No payment approval requests selected.'))
        pending = request_ids.filtered(lambda r: r.state == 'pending_approval')
        if not pending:
            raise UserError(
                _('None of the selected requests are in Pending Approval state. Please select pending requests only.')
            )
        for req in pending:
            req._do_reject(self.reason)
        return {'type': 'ir.actions.act_window_close'}
