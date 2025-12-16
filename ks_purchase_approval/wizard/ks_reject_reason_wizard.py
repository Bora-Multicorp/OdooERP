# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class KsRejectReasonWizard(models.TransientModel):
    _name = 'ks.reject.reason.wizard'
    _description = 'KS Reject Reason Wizard'

    ks_purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        required=True,
    )
    ks_rejection_type = fields.Selection([
        ('confirm', 'Confirmation Rejection'),
        ('update', 'Update Rejection'),
        ('cancel', 'Cancellation Rejection'),
    ], string='Rejection Type', required=True)
    
    ks_reason = fields.Text(
        string='Rejection Reason',
        required=True,
        help='Please provide a reason for the rejection (required)',
    )
    
    ks_rejection_type_label = fields.Char(
        string='Rejection Type Label',
        compute='_compute_rejection_type_label',
    )

    @api.depends('ks_rejection_type')
    def _compute_rejection_type_label(self):
        for record in self:
            if record.ks_rejection_type == 'confirm':
                record.ks_rejection_type_label = _('Confirmation Rejection')
            elif record.ks_rejection_type == 'update':
                record.ks_rejection_type_label = _('Update Rejection')
            elif record.ks_rejection_type == 'cancel':
                record.ks_rejection_type_label = _('Cancellation Rejection')
            else:
                record.ks_rejection_type_label = ''

    def action_submit_rejection(self):
        """Submit the rejection with the provided reason"""
        self.ensure_one()
        
        if not self.ks_reason or not self.ks_reason.strip():
            raise UserError(_("Rejection reason is required."))
        
        order = self.ks_purchase_order_id
        reason = self.ks_reason.strip()
        
        if self.ks_rejection_type == 'confirm':
            order.ks_do_reject_confirmation(reason)
        elif self.ks_rejection_type == 'update':
            order.ks_do_reject_update(reason)
        elif self.ks_rejection_type == 'cancel':
            order.ks_do_reject_cancel(reason)
        else:
            raise UserError(_("Invalid rejection type."))
        
        return {'type': 'ir.actions.act_window_close'}
