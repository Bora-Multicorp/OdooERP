# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class VendorPaymentApprovalApproveWizard(models.TransientModel):
    _name = 'vendor.payment.approval.approve.wizard'
    _description = 'Approve Vendor Payment Request'

    reason = fields.Text(string='Approval Reason', required=True)
    request_ids = fields.Many2many(
        'vendor.payment.approval.request',
        string='Requests',
        relation='vendor_payment_approval_approve_wizard_request_rel',
        column1='wizard_id',
        column2='request_id',
        help='Requests to approve (from context).',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'request_ids' in fields_list and not res.get('request_ids') and self.env.context.get('active_ids'):
            res['request_ids'] = [(6, 0, self.env.context['active_ids'])]
        return res

    def action_approve(self):
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
            req._do_approve(self.reason)
        return {'type': 'ir.actions.act_window_close'}
