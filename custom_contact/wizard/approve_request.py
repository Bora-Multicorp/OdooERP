# -*- coding: utf-8 -*-

from odoo import api, fields, models

class ApproveRequestWizard(models.TransientModel):
    _name = 'approve.request.wizard'
    _description = 'Approve Request Form'

    kyc_approval_id = fields.Many2one('res.partner.kyc.approval', string="Approval for Vendor", domain="[('id', '=', active_id)]")
    remark = fields.Char('Remark', required=True)

    def action_approve_request(self):
        self.ensure_one()
        approval = self.kyc_approval_id
        current_user = self.env.user

        # Find the matching approval line for the currently assigned user
        approval_line = approval.approval_users_ids.filtered(
            lambda l: l.user_id == current_user and not l.state
        )

        if approval_line:
            approval_line.write({
                'state': 'approve',
                'remark': self.remark,
                'action_date': fields.Datetime.now(),
            })
            # Recompute the next approver
            approval._update_assigned_to()

        return {'type': 'ir.actions.act_window_close'}

