# -*- coding: utf-8 -*-

from odoo import fields, models


class SOConfirmApproveWizard(models.TransientModel):
    _name = 'cancel.so.wizard'
    _description = 'Approval for Sale Order Cancellation'

    sale_id = fields.Many2one('sale.order', string="Approval for Sale Order Cancellation")

    remark = fields.Char('Remark', required=True)

    def action_approve_so_cancel(self):
        self.ensure_one()

        # Find the matching approval line for the currently assigned user
        approval_line = self.sale_id.so_approval_users_ids_for_cancellation.filtered(
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
            self.sale_id._update_assigned_to_form_SO_cancellation()
            self.sale_id._create_activity_and_send_notification_on_cancellation_approval()

        return {'type': 'ir.actions.act_window_close'}

