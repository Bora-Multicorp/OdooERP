# -*- coding: utf-8 -*-

from odoo import fields, models

class RejectProductWizard(models.TransientModel):
    _name = 'reject.pi.unlock.wizard'
    _description = 'Reject pi unlock Form'

    order_id = fields.Many2one('sale.order', string="Rejection of PI Unlock Request")
    remark = fields.Char('Remark', required=True)

    def action_reject_pi_unlock(self):
        self.ensure_one()
        approval = self.order_id

        # 1. Find the matching approval line for the currently assigned user
        approval_line = approval.approval_users_ids.filtered(
            lambda l: l.user_id == self.env.user and not l.state
        )

        if approval_line:
            approval_line.write({
                'state': 'reject',
                'remark': self.remark,
                'action_date': fields.Datetime.now(),
            })


        # 2. grab all remaining users can mark their status as suspended
        pending_users_lines = self.order_id.approval_users_ids.filtered(
            lambda l: not l.state
        )

        if pending_users_lines:
            pending_users_lines.write({
                'state': 'suspended',
                'remark': "Rejected by previous authority.",
                'action_date': fields.Datetime.now(),
            })



            # Recompute the next approver
        approval._update_assigned_to()
        approval._send_notification_on_rejection()

        return {'type': 'ir.actions.act_window_close'}