# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.exceptions import UserError 

class RejectProductWizard(models.TransientModel):
    _name = 'reject.product.wizard'
    _description = 'Reject product Form'

    remark = fields.Char('Remark', required=True)

    def action_reject_product(self):
        products = self.env['product.template'].browse(self.env.context.get('active_ids', []))
        current_user = self.env.user

        if not products:
            raise UserError("No products selected for rejection. Please select at least one product.")


        number_of_product_for_rejction = 0
        for product in products: # LOOP THROUGH EACH SELECTED PRODUCT

            if product.state != 'pending':
                continue

                    
            approval_line = product.approval_users_ids.filtered(
                lambda l: l.user_id == current_user and not l.state
            )


            if approval_line:
                approval_line.write({
                    'state': 'reject',
                    'remark': self.remark,
                    'action_date': fields.Datetime.now(),
                })
            number_of_product_for_rejction += 1 


        first_product = products[0]
        title = f"Total {number_of_product_for_rejction} products are rejected."
        message = "Activities are assigned to you."
        type = "success"
        partner_id = products[0].assigned_to.partner_id

        if number_of_product_for_rejction == 1:
            title = f"Product {first_product.name} rejected."
            message = "Activity assigned to you."
            type = "success"
        elif number_of_product_for_rejction == 0:
            title = f"No products in 'Pending for Approval' state were found among your selection. Please select products that are in the 'Pending' state to proceed."
            message = ""
            type = "danger"
            partner_id = self.env.user.partner_id

        first_product.env['bus.bus']._sendone(
                partner_id,
                'simple_notification',
                {
                    'type': type,
                    'title': title,
                    'message':  message,
                    'sticky': True,
                },
            )


        return {'type': 'ir.actions.act_window_close'}


        approval = self.product_approval_id
        current_user = self.env.user

        # Find the matching approval line for the currently assigned user
        approval_line = approval.approval_users_ids.filtered(
            lambda l: l.user_id == current_user and not l.state
        )

        if approval_line:
            approval_line.write({
                'state': 'reject',
                'remark': self.remark,
                'action_date': fields.Datetime.now(),
            })
            # Recompute the next approver
            # approval._update_assigned_to()

        return {'type': 'ir.actions.act_window_close'}
