# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class ApproveSaleOrderWizard(models.TransientModel):
    _name = 'approve.sale.order.wizard'
    _description = 'Approve Sales Order Form'

    sale_id = fields.Many2one('sale.order', string="Approval for Sale Order Confirmation")

    remark = fields.Char('Remark', required=True)

    def action_approve_so_confirm(self):
        self.ensure_one()

        # Find the matching approval line for the currently assigned user
        approval_line = self.sale_id.so_approval_users_ids_for_confirmation.filtered(
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
            self.sale_id._update_assigned_to_form_SO_confirm()
            self.sale_id._create_activity_and_send_notification_on_confirm_approval()

        return {'type': 'ir.actions.act_window_close'}


