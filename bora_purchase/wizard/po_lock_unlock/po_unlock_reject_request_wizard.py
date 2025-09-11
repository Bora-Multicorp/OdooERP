
# -*- coding: utf-8 -*-

from odoo import fields, models

class POUnlockRejectWizard(models.TransientModel):
    _name = 'reject.po.unlock.wizard'
    _description = 'Reject po unlock Form'

    order_approval_id = fields.Many2one('purchase.order', string="Rejection of PO Unlock Request")
    remark = fields.Char('Remark', required=True)

    def action_reject_po_unlock(self):
        self.ensure_one()
        approval = self.order_approval_id

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
            # Recompute the next approver
            approval._send_notification_on_rejection()
            # approval._update_assigned_to()

        # 2. grab all remaining users can mark their status as suspended
        pending_users_lines = self.order_id.approval_users_ids.filtered(
            lambda l: not l.state
        )

        if pending_users_lines:
            pending_users_lines.write({
                'state': 'suspended',
                'remark': "Rejected by previous authority",
                'action_date': fields.Datetime.now(),
            })

        return {'type': 'ir.actions.act_window_close'}
