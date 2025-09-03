# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError

class ApproveSaleOrderCancelWizard(models.TransientModel):
    _name = 'approve.sale.order.cancel.wizard'
    _description = 'Approve Sales Order Cancellation Wizard'

    remark = fields.Char('Remark', required=True)

    def action_approve_sale_order_cancel(self):
        """
        Approves the selected sales order cancellation.
        """
        sale_orders = self.env['sale.order'].browse(self.env.context.get('active_ids', []))
        current_user = self.env.user


        approval_line = sale_orders.cancel_approval_users_ids.filtered(
                lambda l: l.user_id == current_user and not l.state
        )

        if approval_line:
            approval_line.write({
                'state': 'approve',
                'remark': self.remark,
                'action_date': fields.Datetime.now(),
            })
            sale_orders._update_cancel_assigned_to()

        return {'type': 'ir.actions.act_window_close'}


