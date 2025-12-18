# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class KsApproveUpdateReasonWizard(models.TransientModel):
    _name = 'ks.approve.update.reason.wizard'
    _description = 'KS Approve Update Reason Wizard'

    ks_purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        required=True,
    )
    ks_reason = fields.Text(
        string='Reason for approval',
        required=True,
        help='Please provide a reason for the update approval (required)',
    )

    def action_submit_approval(self):
        """Submit the update approval with the provided reason"""
        self.ensure_one()
        
        if not self.ks_reason or not self.ks_reason.strip():
            raise UserError(_("Reason for approval is required."))
        
        order = self.ks_purchase_order_id
        reason = self.ks_reason.strip()
        
        # Call the approval method with reason
        order.ks_do_approve_update(reason)
        
        return {'type': 'ir.actions.act_window_close'}

