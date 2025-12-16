from odoo.exceptions import UserError

from odoo import fields, models


class ApproveProductWizard(models.TransientModel):
    _name = 'approve.product.wizard'
    _description = 'Approve Request Form (Multi-Product)'

    remark = fields.Char('Remark', required=True)

    def action_approve_product(self):

        products = self.env['product.template'].browse(self.env.context.get('active_ids', []))
        current_user = self.env.user

        if not products:
            raise UserError("No products selected for approval. Please select at least one product.")

        number_of_product_for_approvals = 0
        for product in products:

            if product.state != 'pending':
                continue

            approval_line = product.approval_users_ids.filtered(
                lambda l: l.user_id == current_user and not l.state
            )

            if approval_line:
                approval_line.write({
                    'state': 'approve',
                    'remark': self.remark,
                    'action_date': fields.Datetime.now(),
                })
            product._update_assigned_to(False)
            number_of_product_for_approvals += 1

        first_product = products[0]
        title = f"Total {number_of_product_for_approvals} new products are assigned to you for the approval."
        message = "Activities are assigned to you."
        type = "success"
        partner_id = products[0].assigned_to.partner_id
        if number_of_product_for_approvals == 1:
            title = f"Product approval for {first_product.name}"
            message = "Activity assigned to you."
            type = "success"
        elif number_of_product_for_approvals == 0:
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
                'message': message,
                'sticky': True,
            },
        )

        if partner_id != self.env.user.partner_id:
            title = "Product approved successfully."
            if number_of_product_for_approvals > 1:
                title = f"Total {number_of_product_for_approvals} products are approved successfully."

            first_product.env['bus.bus']._sendone(
                self.env.user.partner_id,
                'simple_notification',
                {
                    'type': "info",
                    'title': title,
                    'message': "",
                    'sticky': True,
                },
            )

        return {'type': 'ir.actions.act_window_close'}
