# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class KsApproveConfirmationReasonWizard(models.TransientModel):
    _name = 'ks.approve.confirmation.reason.wizard'
    _description = 'KS Approve Confirmation Reason Wizard'

    ks_purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        required=True,
    )
    ks_reason = fields.Text(
        string='Reason for confirmation',
        required=True,
        help='Please provide a reason for the confirmation (required)',
    )

    def action_submit_approval(self):
        """Submit the approval with the provided reason"""
        self.ensure_one()
        
        if not self.ks_reason or not self.ks_reason.strip():
            raise UserError(_("Reason for confirmation is required."))
        
        order = self.ks_purchase_order_id
        reason = self.ks_reason.strip()
        
        # Call the approval method with reason
        order.ks_do_approve_confirmation(reason)
        
        return {'type': 'ir.actions.act_window_close'}

