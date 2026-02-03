# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class KsSaleRejectReasonWizard(models.TransientModel):
    _name = 'ks.sale.reject.reason.wizard'
    _description = 'KS Sale Reject/Request Reason Wizard'

    ks_sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        required=True,
    )
    ks_action_type = fields.Selection([
        ('reject_confirm', 'Reject Confirmation'),
        ('reject_cancel', 'Reject Cancellation'),
        ('reject_edit', 'Reject Edit'),
        ('cancel_request', 'Request Cancellation'),
        ('edit_request', 'Request Edit'),
    ], string='Action Type', required=True)
    
    ks_reason = fields.Text(
        string='Reason',
        required=True,
        help='Please provide a reason (required)',
    )
    
    ks_action_type_label = fields.Char(
        string='Action Type Label',
        compute='_compute_action_type_label',
    )

    @api.depends('ks_action_type')
    def _compute_action_type_label(self):
        labels = {
            'reject_confirm': _('Reject Confirmation Request'),
            'reject_cancel': _('Reject Cancellation Request'),
            'reject_edit': _('Reject Edit Request'),
            'cancel_request': _('Request Cancellation'),
            'edit_request': _('Request Edit Access'),
        }
        for record in self:
            record.ks_action_type_label = labels.get(record.ks_action_type, '')

    def action_submit(self):
        """Submit the action with the provided reason"""
        self.ensure_one()
        
        if not self.ks_reason or not self.ks_reason.strip():
            raise UserError(_("Reason is required."))
        
        order = self.ks_sale_order_id
        reason = self.ks_reason.strip()
        
        if self.ks_action_type == 'reject_confirm':
            order.ks_do_reject_confirmation(reason)
        elif self.ks_action_type == 'reject_cancel':
            order.ks_do_reject_cancel(reason)
        elif self.ks_action_type == 'reject_edit':
            order.ks_do_reject_edit(reason)
        elif self.ks_action_type == 'cancel_request':
            order.ks_do_request_cancel(reason)
        elif self.ks_action_type == 'edit_request':
            order.ks_do_request_edit(reason)
        else:
            raise UserError(_("Invalid action type."))
        
        return {'type': 'ir.actions.act_window_close'}

