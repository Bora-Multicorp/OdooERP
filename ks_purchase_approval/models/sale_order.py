# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    ks_linked_purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Linked Purchase Order',
        copy=False,
        help='Purchase Order linked to this Sale Order',
        ondelete='set null',
    )
    
    def action_view_linked_purchase_order(self):
        """Open the linked Purchase Order"""
        self.ensure_one()
        if not self.ks_linked_purchase_order_id:
            return False
        
        return {
            'name': _('Linked Purchase Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': self.ks_linked_purchase_order_id.id,
            'target': 'current',
        }

