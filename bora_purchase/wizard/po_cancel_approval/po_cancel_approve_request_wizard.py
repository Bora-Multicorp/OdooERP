
# -*- coding: utf-8 -*-

from odoo import fields, models

class POConfirmApproveWizard(models.TransientModel):
    _name = 'cancel.po.wizard'
    _description = 'Approval for Purchase Order Cancellation'

    order_id = fields.Many2one('purchase.order', string="Approval for Purchase Order Cancellation")

    remark = fields.Char('Remark', required=True)

    def action_approve_po_cancel(self): 
        self.ensure_one()

        # Find the matching approval line for the currently assigned user
        approval_line = self.order_id.approval_users_ids_for_cancellation.filtered(
            lambda l: l.user_id == self.env.user and not l.state
        )
        
        approval_line = approval_line[-1] if approval_line else False

        if approval_line:
            approval_line.write({
                'state': 'approve',
                'remark': self.remark,
                'action_date': fields.Datetime.now(),
            })
            # Recompute the next approver
            self.order_id._update_assigned_to_form_PO_cancellation()
            self.order_id._create_activity_and_send_notification_on_cancellation_approval()

        return {'type': 'ir.actions.act_window_close'}

