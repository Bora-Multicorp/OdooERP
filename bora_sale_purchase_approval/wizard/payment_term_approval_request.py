# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class ApprovePaymentWizard(models.TransientModel):
    _name = 'approve.payment.term.wizard'
    _description = 'Approve Payment term Form'


    remark = fields.Char('Remark', required=True)

    def action_approve_payment_term_credit(self):
        """
        Approves the selected payment orders and updates the approval flow.
        """
        # Get the selected sales order records from the context
        sale_orders = self.env['sale.order'].browse(self.env.context.get('active_ids', []))
        current_user = self.env.user

        approval_line = sale_orders.credit_approval_users_ids.filtered(
            lambda l: l.user_id == current_user and not l.state
        )

        if approval_line:
            approval_line.write({
                'state': 'approve',
                'remark': self.remark,
                'action_date': fields.Datetime.now(),
            })
            sale_orders.write({
                "is_payment_approved": True,

            })

            sale_orders._update_credit_assigned_to()

        return {'type': 'ir.actions.act_window_close'}

