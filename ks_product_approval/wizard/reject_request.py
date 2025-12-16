# -*- coding: utf-8 -*-

from odoo.exceptions import UserError

from odoo import fields, models


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
        for product in products:

            if product.state != 'pending':
                continue

            # 1. Find the matching approval line for the currently assigned user and mark it as rejected
            approval_line = product.approval_users_ids.filtered(
                lambda l: l.user_id == current_user and not l.state
            )

            if approval_line:
                approval_line.write({
                    'state': 'reject',
                    'remark': self.remark,
                    'action_date': fields.Datetime.now(),
                })

            # 2. grab all remaining users can mark their status as suspended
            pending_users_lines = product.approval_users_ids.filtered(
                lambda l: not l.state
            )

            if pending_users_lines:
                pending_users_lines.write({
                    'state': 'suspended',
                    'remark': "Rejected by previous authority",
                    'action_date': fields.Datetime.now(),
                })

            number_of_product_for_rejction += 1

        first_product = products[0]
        title = f"Total {number_of_product_for_rejction} products are rejected."
        message = "Activities are assigned to you."
        type = "info"
        partner_id = products[0].assigned_to.partner_id

        if number_of_product_for_rejction == 1:
            title = f"Product {first_product.name} rejected."
            message = ""
            type = "info"
        elif number_of_product_for_rejction == 0:
            title = f"No products in 'Pending' state were found among your selection. Please select products that are in the 'Pending' state to proceed."
            message = ""
            type = "danger"
            partner_id = self.env.user.partner_id

        first_product.env['bus.bus']._sendone(
            partner_id,
            'simple_notification',
            {
                'type': type,
                'title': title,
                'message': message,
                'sticky': True,
            },
        )

        if number_of_product_for_rejction > 0:
            ks_product_approval_users = self.env['product.approval.config'].sudo().search([])
            for user in ks_product_approval_users:
                if user.user_id != self.env.user:
                    first_product.env['bus.bus']._sendone(
                        user.user_id.partner_id,
                        'simple_notification',
                        {
                            'type': type,
                            'title': title,
                            'message': message,
                            'sticky': True,
                        },
                    )

        # 3. Remove assignee 
        product.write({
            'assigned_to': None
        })

        return {'type': 'ir.actions.act_window_close'}
