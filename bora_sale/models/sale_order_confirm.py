from odoo import models
from odoo.exceptions import UserError

class SalesOrderInherited(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        for order in self:
            for line in order.order_line:
                product_template = line.product_id.product_tmpl_id
                
                reorder_rule_count = self.env['stock.warehouse.orderpoint'].search_count([
                    ('product_id', '=', line.product_id.id),
                    ('active', '=', True)
                ])

                if reorder_rule_count == 0 and product_template.type == 'consu':
                    raise UserError(
                        f"No re-order rule is configured for product '{product_template.name}'. Please configure one before confirming this order."
                    )
                
                if product_template.type == 'consu' and not product_template.seller_ids:
                    raise UserError(
                        f"No vendor is added for product '{product_template.name}'. Please add a vendor to the product form before confirming this order."
                    )                

        return super(SalesOrderInherited, self).action_confirm()

    


    def action_trigger_reordering_rules(self):
        orderpoints = self.env['stock.warehouse.orderpoint'].search([]) 

        if orderpoints:
            orderpoints.sudo()._procure_orderpoint_confirm()
            self.env.user.notify_success(message="Reordering rules processed successfully!")
        else:
            self.env.user.notify_warning(message="No active reordering rules found.")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': "Reordering",
                'message': "Reordering rules processed.",
                'type': 'success',
                'sticky': False,
            }
        }
