# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError

class RejectSaleOrderCancelWizard(models.TransientModel):
    _name = 'reject.sale.order.cancel.wizard'
    _description = 'Reject Sales Order Cancellation Form'

    remark = fields.Char('Remark', required=True)

    def action_reject_sale_order_cancel(self):
        """
        Rejects the selected sales order cancellation and updates the approval flow.
        """
        self.ensure_one()
        sale_orders = self.env['sale.order'].browse(self.env.context.get('active_ids', []))
        current_user = self.env.user

        approval_line = sale_orders.cancel_approval_users_ids.filtered(
                lambda l: l.user_id == current_user and not l.state
        )

        if approval_line:
            approval_line.write({
                'state': 'reject',
                'remark': self.remark,
                'action_date': fields.Datetime.now(),
            })
            sale_orders._update_cancel_state_based_on_approvals()

        return {'type': 'ir.actions.act_window_close'}