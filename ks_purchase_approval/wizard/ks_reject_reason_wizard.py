# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class KsRejectReasonWizard(models.TransientModel):
    _name = 'ks.purchase.reject.reason.wizard'
    _description = 'KS Purchase Reject Reason Wizard'

    ks_purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        required=True,
    )
    
    ks_action_type = fields.Selection([
        ('cancel_request', 'Cancel Request'),
        ('edit_request', 'Edit Request'),
    ], string='Action Type', default='cancel_request')
    
    ks_reason = fields.Text(
        string='Reason',
        required=True,
        help='Please provide a reason (required)',
    )

    def action_submit(self):
        """Submit the request with the provided reason"""
        self.ensure_one()
        
        if not self.ks_reason or not self.ks_reason.strip():
            raise UserError(_("Reason is required."))
        
        order = self.ks_purchase_order_id
        reason = self.ks_reason.strip()
        
        if self.ks_action_type == 'cancel_request':
            order.ks_do_request_cancel(reason)
        elif self.ks_action_type == 'edit_request':
            order.ks_do_request_edit(reason)
        else:
            raise UserError(_("Invalid action type."))
        
        return {'type': 'ir.actions.act_window_close'}
