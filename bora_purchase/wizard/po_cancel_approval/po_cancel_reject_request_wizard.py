# -*- coding: utf-8 -*-

from odoo import fields, models

class POConfirmRejectWizard(models.TransientModel): 
    _name = 'reject.cancel.po.wizard'
    _description = 'Rejection for Purchase Order Cancellation'

    order_id = fields.Many2one('purchase.order', string="Rejection for Purchase Order Cancellation")

    remark = fields.Char('Remark', required=True)

    def action_reject_po_cancellation(self):
        self.ensure_one()

        # 1. Find the matching approval line for the currently assigned user and mark it as rejected
        approval_line = self.order_id.approval_users_ids_for_cancellation.filtered(
            lambda l: l.user_id == self.env.user and not l.state
        )

        approval_line = approval_line[-1] if approval_line else False

        if approval_line:
            approval_line.write({
                'state': 'reject',
                'remark': self.remark,
                'action_date': fields.Datetime.now(),
            })

        # 2. grab all remaining users can mark their status as suspended
        pending_users_lines = self.order_id.approval_users_ids_for_cancellation.filtered(
            lambda l: not l.state
        )

        if pending_users_lines:
            pending_users_lines.write({
                'state': 'suspended',
                'remark': "",
                'action_date': fields.Datetime.now(),
            })



        # Recompute the next approver
        self.order_id._update_assigned_to_form_PO_cancellation()
        self.order_id._send_notification_on_rejection_of_PO_cancellation()

        return {'type': 'ir.actions.act_window_close'}