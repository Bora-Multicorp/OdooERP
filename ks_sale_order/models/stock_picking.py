# -*- coding: utf-8 -*-

from odoo import api, models, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    def _action_done(self):
        """Override to check if stock is now available for related Sale Orders"""
        result = super()._action_done()
        
        # Only process incoming pickings (receipts) that are done
        incoming_pickings = self.filtered(
            lambda p: p.picking_type_id.code == 'incoming' and p.state == 'done'
        )
        
        if not incoming_pickings:
            return result
        
        # Get all Purchase Orders from these pickings
        purchase_orders = incoming_pickings.mapped('purchase_id')
        
        if not purchase_orders:
            return result
        
        # Find Sale Orders linked to the validated Purchase Orders
        sale_orders = purchase_orders.mapped('ks_source_sale_order_id').filtered(
            lambda so: so and so.ks_po_created_for_stock and so.state not in ('sale', 'done', 'cancel')
        )
        
        # Check each SO to see if stock is now available
        for so in sale_orders:
            so._ks_check_and_notify_stock_availability()
        
        return result
    
    def button_validate(self):
        """Override button_validate to check stock availability after validation"""
        result = super().button_validate()
        
        # Stock availability check is handled in _action_done
        return result

