# -*- coding: utf-8 -*-

from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        """Override to send packed email when picking is validated"""
        result = super().button_validate()
        
        for picking in self:
            if picking.sale_id and picking.picking_type_id.code == 'outgoing':
                # Check if all pickings for this sale order are done
                sale_order = picking.sale_id
                
                # Check if this is the last picking to be validated
                all_pickings = sale_order.picking_ids.filtered(
                    lambda p: p.picking_type_id.code == 'outgoing'
                )
                all_done = all(p.state == 'done' for p in all_pickings)
                
                if all_done:
                    # Only send emails for India and Dubai zones
                    if sale_order.ks_zone in ['india', 'dubai']:
                        # Get auto-send settings (from config or manual override)
                        auto_send_packed = sale_order.ks_auto_send_packed
                        auto_send_shipped = sale_order.ks_auto_send_shipped
                        
                        # All pickings are done - order is packed
                        if auto_send_packed and not sale_order.ks_email_packed_sent:
                            sale_order._send_packed_email()
                        
                        # Check if order is shipped (all pickings done and delivery confirmed)
                        if auto_send_shipped and not sale_order.ks_email_shipped_sent:
                            sale_order._send_shipped_email()
        
        return result

    def action_done(self):
        """Override action_done for compatibility"""
        result = super().action_done()
        
        for picking in self:
            if picking.sale_id and picking.picking_type_id.code == 'outgoing':
                sale_order = picking.sale_id
                
                all_pickings = sale_order.picking_ids.filtered(
                    lambda p: p.picking_type_id.code == 'outgoing'
                )
                all_done = all(p.state == 'done' for p in all_pickings)
                
                if all_done:
                    # Only send emails for India and Dubai zones
                    if sale_order.ks_zone in ['india', 'dubai']:
                        # Get auto-send settings (from config or manual override)
                        auto_send_packed = sale_order.ks_auto_send_packed
                        auto_send_shipped = sale_order.ks_auto_send_shipped
                        
                        if auto_send_packed and not sale_order.ks_email_packed_sent:
                            sale_order._send_packed_email()
                        
                        if auto_send_shipped and not sale_order.ks_email_shipped_sent:
                            sale_order._send_shipped_email()
        
        return result

