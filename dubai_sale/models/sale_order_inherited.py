from odoo import models
from odoo.exceptions import UserError

class SalesOrderInherited(models.Model):
    _inherit = 'sale.order'



    # check "Re-ordering" rule exist or not
    def action_confirm(self):
        for order in self:
            # Check for re-order rules on each line item.
            # This is done by checking if the product has a reordering_min_qty set.
            for line in order.order_line:
                product_template = line.product_id.product_tmpl_id
                
                # We check for a reordering rule on the product template.
                # The search_count method is a very efficient way to check for existence.
                reorder_rule_count = self.env['stock.warehouse.orderpoint'].search_count([
                    ('product_id', '=', line.product_id.id),
                    ('active', '=', True)
                ])

                # If no reordering rule is found and the product is storable,
                # you can raise a warning or take other actions.
                if reorder_rule_count == 0 and product_template.type == 'consu':
                    # This is where you can add your custom logic.
                    # For example, raise a UserError to block the confirmation.
                    raise UserError(
                        f"No re-order rule is configured for product '{product_template.name}'. Please configure one before confirming this order."
                    )

            # If all checks pass, call the original action_confirm method
            # to proceed with the sales order confirmation.
            return super(SalesOrderInherited, self).action_confirm()

