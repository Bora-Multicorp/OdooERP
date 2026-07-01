# my_module/models/product_bulk_approval_wizard.py
from odoo import models, fields


class ProductBulkApprovalWizard(models.TransientModel):
    _name = 'product.bulk.submit.approval.wizard'
    _description = 'Confirm Bulk Submit Approval'

    # You can add fields here if you need more context or options in the confirmation dialog
    product_count = fields.Integer(string="Number of Products", readonly=True)

    # You could also add a many2many field to show the selected products
    # product_ids = fields.Many2many('product.template', string="Products to Approve")

    def action_submit_for_bulk_approval(self):
        """
        This method is called when the user clicks 'Confirm' in the wizard.
        It then calls the actual bulk_approval method on the product.template model.
        """
        # Get the IDs of the products from the context that was passed to the wizard
        product_ids = self.env.context.get('active_ids')
        if product_ids:
            products = self.env['product.template'].browse(product_ids)
            return products.bulk_submit_for_approval()  # Call your existing bulk_approval method

        # If no products found in context (shouldn't happen if triggered from selection)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': "Error",
                'message': "No products found to submit for approval.",
                'type': 'danger',
                'sticky': True,
            }
        }
