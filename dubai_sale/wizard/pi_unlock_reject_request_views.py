# -*- coding: utf-8 -*-

from odoo import fields, models

class RejectProductWizard(models.TransientModel):
    _name = 'reject.pi.unlock.wizard'
    _description = 'Reject pi unlock Form'

    order_approval_id = fields.Many2one('sale.order', string="Rejection of PI Unlock Request")
    remark = fields.Char('Remark', required=True)

    def action_reject_pi_unlock(self):
        self.ensure_one()
        approval = self.order_approval_id

        # Find the matching approval line for the currently assigned user
        approval_line = approval.approval_users_ids.filtered(
            lambda l: l.user_id == self.env.user and not l.state
        )

        if approval_line:
            approval_line.write({
                'state': 'reject',
                'remark': self.remark,
                'action_date': fields.Datetime.now(),
            })
            # Recompute the next approver
            approval._send_notification_on_rejection()
            # approval._update_assigned_to()

        return {'type': 'ir.actions.act_window_close'}
