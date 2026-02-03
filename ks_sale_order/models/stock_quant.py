# -*- coding: utf-8 -*-

from odoo import api, models


class StockQuant(models.Model):
    _inherit = 'stock.quant'
    
    def write(self, vals):
        """Override to check stock availability when quantity changes"""
        result = super().write(vals)
        
        # Only check if quantity is being updated and increased
        if 'quantity' in vals:
            # Get products affected by this quant change
            affected_products = self.mapped('product_id')
            
            if affected_products:
                # Check only Sale Orders that have these products
                sale_orders = self.env['sale.order'].search([
                    ('ks_po_created_for_stock', '=', True),
                    ('state', 'not in', ('sale', 'done', 'cancel')),
                ])
                
                # Filter SOs that have the affected products
                relevant_sos = sale_orders.filtered(
                    lambda so: any(
                        line.product_id in affected_products 
                        for line in so.order_line 
                        if line.product_id and line.product_id.is_storable
                    )
                )
                
                # Check each relevant SO to see if stock is now available
                for so in relevant_sos:
                    so._ks_check_and_notify_stock_availability()
        
        return result
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override to check stock availability when new quants are created"""
        result = super().create(vals_list)
        
        # Get products affected by new quants
        affected_products = result.mapped('product_id')
        
        if affected_products:
            # Check only Sale Orders that have these products
            sale_orders = self.env['sale.order'].search([
                ('ks_po_created_for_stock', '=', True),
                ('state', 'not in', ('sale', 'done', 'cancel')),
            ])
            
            # Filter SOs that have the affected products
            relevant_sos = sale_orders.filtered(
                lambda so: any(
                    line.product_id in affected_products 
                    for line in so.order_line 
                    if line.product_id and line.product_id.is_storable
                )
            )
            
            # Check each relevant SO to see if stock is now available
            for so in relevant_sos:
                so._ks_check_and_notify_stock_availability()
        
        return result

