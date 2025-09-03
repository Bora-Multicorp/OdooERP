# -*- coding: utf-8 -*-
from odoo import api, fields, models

class RejectSaleOrderWizard(models.TransientModel):
    _name = 'reject.sale.order.wizard'
    _description = 'Reject Sales Order Form'

    # The sales order that is being rejected
    sale_order_id = fields.Many2one('sale.order', string="Rejection for Sales Order", domain="[('id', '=', active_id)]")

    # A field for the user to add rejection remarks
    remark = fields.Char('Remark', required=True)

    def action_reject_sale_order(self):
        """
        Rejects the sales order and updates the corresponding approval line.
        """
        self.ensure_one()
        sale_order = self.sale_order_id
        current_user = self.env.user

        # Finds the specific approval line for the current user
        approval_line = sale_order.confirm_approval_users_ids.filtered(
            lambda l: l.user_id == current_user and not l.state
        )

        if approval_line:
            # Writes the rejection status, remark, and action date to the line
            approval_line.write({
                'state': 'reject',
                'remark': self.remark,
                'action_date': fields.Datetime.now(),
            })
            # Updates the sales order's state to 'rejected'
            sale_order.state = 'rejected'

        return {'type': 'ir.actions.act_window_close'}
