# -*- coding: utf-8 -*-

from odoo import api, fields, models


class RejectRequestWizard(models.TransientModel):
    _name = 'reject.request.wizard'
    _description = 'Reject Request Form'

    kyc_approval_id = fields.Many2one('res.partner.kyc.approval', string="Approval for Vendor",
                                      domain="[('id', '=', active_id)]")
    remark = fields.Char('Remark', required=True)

    def action_reject_request(self):
        self.ensure_one()
        approval = self.kyc_approval_id
        current_user = self.env.user

        # Find the matching approval line for the currently assigned user
        approval_line = approval.approval_users_ids.filtered(
            lambda l: l.user_id == current_user and not l.state
        )

        if approval_line:
            approval_line.write({
                'state': 'reject',
                'remark': self.remark,
                'action_date': fields.Datetime.now(),
            })
            approval.write(
                {'rejection_date': fields.Datetime.now(), 'rejection_reason': self.remark, 'assigned_to': False,
                 'is_rejected': True})
            # Recompute the next approver
            # approval._update_assigned_to()

        return {'type': 'ir.actions.act_window_close'}
