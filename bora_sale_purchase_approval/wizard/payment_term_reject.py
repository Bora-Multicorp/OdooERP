# -*- coding: utf-8 -*-
from odoo import api, fields, models

class RejectPaymentTermWizard(models.TransientModel):
    _name = 'reject.payment.term.wizard'
    _description = 'Reject Payment Credit Term Form'

    # The sales order that is being rejected
    sale_order_id = fields.Many2one('sale.order', string="Rejection for Credit Payment Term", domain="[('id', '=', active_id)]")

    # A field for the user to add rejection remarks
    remark = fields.Char('Remark', required=True)

    def action_reject_payment_term(self):
        """
        Rejects the sales order and updates the corresponding approval line.
        """
        self.ensure_one()
        sale_order = self.sale_order_id
        current_user = self.env.user

        # Finds the specific approval line for the current user
        approval_line = sale_order.credit_approval_users_ids.filtered(
            lambda l: l.user_id == current_user and not l.state
        )

        if approval_line:
            # Writes the rejection status, remark, and action date to the line
            approval_line.write({
                'state': 'reject',
                'remark': self.remark,
                'action_date': fields.Datetime.now(),
            })
            sale_order.write({
                "is_payment_rejected": True,
            })

        return {'type': 'ir.actions.act_window_close'}
