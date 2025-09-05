# -*- coding: utf-8 -*-

from odoo import fields, models

class ApproveProductWizard(models.TransientModel):
    _name = 'approve.pi.unlock.wizard'
    _description = 'Approve Request Form'

    order_approval_id = fields.Many2one('sale.order', string="Approval for Unlock PI")

    remark = fields.Char('Remark', required=True)

    def action_approve_pi_unlock(self):
        self.ensure_one()
        approval = self.order_approval_id

        # Find the matching approval line for the currently assigned user
        approval_line = approval.approval_users_ids.filtered(
            lambda l: l.user_id == self.env.user and not l.state
        )

        if approval_line:
            approval_line.write({
                'state': 'approve',
                'remark': self.remark,
                'action_date': fields.Datetime.now(),
            })
            # Recompute the next approver
            approval._update_assigned_to()
            approval._create_activity_and_send_notification_on_approval()

        return {'type': 'ir.actions.act_window_close'}

