# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class KsGrnMismatchApproveWizard(models.TransientModel):
    _name = 'ks.grn.mismatch.approve.wizard'
    _description = 'GRN Mismatch Approve / Reject Wizard'

    ks_grn_mismatch_approval_id = fields.Many2one(
        'ks.grn.mismatch.approval',
        string='GRN Mismatch Request',
        required=True,
        ondelete='cascade',
    )
    approve = fields.Boolean(
        string='Approve',
        default=True,
        help='If set, approve the request; otherwise reject.',
    )
    reason = fields.Text(
        string='Reason',
        required=True,
        help='Reason for approval or rejection (required).',
    )

    def action_confirm(self):
        self.ensure_one()
        if not self.reason or not self.reason.strip():
            raise UserError(_('Please enter a reason.'))
        req = self.ks_grn_mismatch_approval_id
        po = req.purchase_id
        current_user = self.env.user
        approvers = po.ks_approver_1_id
        if po.ks_approver_2_id:
            approvers |= po.ks_approver_2_id
        if current_user not in approvers:
            raise UserError(
                _('Only the Purchase Order approvers (%s) can approve or reject this GRN mismatch request.')
                % ', '.join(approvers.mapped('name'))
            )
        reason = self.reason.strip()
        if self.approve:
            req._do_approve(reason, current_user)
        else:
            req._do_reject(reason, current_user)
        return {'type': 'ir.actions.act_window_close'}
