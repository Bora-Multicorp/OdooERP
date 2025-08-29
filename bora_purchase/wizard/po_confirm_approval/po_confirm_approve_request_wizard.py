
# -*- coding: utf-8 -*-

from odoo import fields, models

class POConfirmApproveWizard(models.TransientModel):
    _name = 'confirm.po.wizard'
    _description = 'Approval for Purchase Order Confirmation'

    order_id = fields.Many2one('purchase.order', string="Approval for Purchase Order Confirmation")

    remark = fields.Char('Remark', required=True)

    def action_approve_po_confirm(self):
        self.ensure_one()

        # Find the matching approval line for the currently assigned user
        approval_line = self.order_id.approval_users_ids.filtered(
            lambda l: l.user_id == self.env.user and not l.state
        )

        if approval_line:
            approval_line.write({
                'state': 'approve',
                'remark': self.remark,
                'action_date': fields.Datetime.now(),
            })
            # Recompute the next approver
            # approval._update_assigned_to()
            # approval._create_activity_and_send_notification_on_approval()

        return {'type': 'ir.actions.act_window_close'}

