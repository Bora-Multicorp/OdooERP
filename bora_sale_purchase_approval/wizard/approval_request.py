# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class ApproveSaleOrderWizard(models.TransientModel):
    _name = 'approve.sale.order.wizard'
    _description = 'Approve Sales Order Form'


    remark = fields.Char('Remark', required=True)

    def action_approve_sale_order(self):
        """
        Approves the selected sales orders and updates the approval flow.
        """
        # Get the selected sales order records from the context
        sale_orders = self.env['sale.order'].browse(self.env.context.get('active_ids', []))
        current_user = self.env.user

        approval_line = sale_orders.confirm_approval_users_ids.filtered(
            lambda l: l.user_id == current_user and not l.state
        )

        if approval_line:
            approval_line.write({
                'state': 'approve',
                'remark': self.remark,
                'action_date': fields.Datetime.now(),
            })
            sale_orders._update_assigned_to()


        return {'type': 'ir.actions.act_window_close'}

