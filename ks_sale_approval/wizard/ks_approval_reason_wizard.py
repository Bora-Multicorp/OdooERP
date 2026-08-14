# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class KsApprovalReasonWizard(models.TransientModel):
    _name = 'ks.sale.approval.reason.wizard'
    _description = 'KS Sale Approval/Rejection Reason Wizard'

    ks_sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        required=True,
    )
    ks_action_type = fields.Selection([
        ('approve_confirm', 'Approve Confirmation'),
        ('reject_confirm', 'Reject Confirmation'),
        ('approve_cancel', 'Approve Cancel'),
        ('reject_cancel', 'Reject Cancel'),
        ('approve_edit', 'Approve Edit'),
        ('reject_edit', 'Reject Edit'),
    ], string='Action Type', required=True)
    
    ks_reason = fields.Text(
        string='Reason',
        required=True,
        help='Please provide a reason (required)',
    )
    
    ks_price_below_purchase_warning = fields.Text(
        string='Price Below Purchase Warning',
        related='ks_sale_order_id.ks_price_below_purchase_warning',
        readonly=True,
    )
    
    ks_action_type_label = fields.Char(
        string='Action Type',
        compute='_compute_action_type_label',
    )
    
    ks_is_rejection = fields.Boolean(
        string='Is Rejection',
        compute='_compute_action_type_label',
    )
    
    ks_button_text = fields.Char(
        string='Button Text',
        compute='_compute_action_type_label',
    )

    @api.depends('ks_action_type')
    def _compute_action_type_label(self):
        """Compute the action type label and button text"""
        labels = {
            'approve_confirm': _('Confirmation Approval'),
            'reject_confirm': _('Confirmation Rejection'),
            'approve_cancel': _('Cancellation Approval'),
            'reject_cancel': _('Cancellation Rejection'),
            'approve_edit': _('Edit Approval'),
            'reject_edit': _('Edit Rejection'),
        }
        button_texts = {
            'approve_confirm': _('Confirm Approval'),
            'reject_confirm': _('Confirm Rejection'),
            'approve_cancel': _('Confirm Approval'),
            'reject_cancel': _('Confirm Rejection'),
            'approve_edit': _('Confirm Approval'),
            'reject_edit': _('Confirm Rejection'),
        }
        for record in self:
            record.ks_action_type_label = labels.get(record.ks_action_type, '')
            record.ks_is_rejection = record.ks_action_type.startswith('reject_')
            record.ks_button_text = button_texts.get(record.ks_action_type, 'Submit')

    def action_submit(self):
        """Submit the approval/rejection with reason"""
        self.ensure_one()
        
        if not self.ks_reason or not self.ks_reason.strip():
            raise UserError(_("Reason/Comment is required. Please provide a reason before proceeding."))
        
        order = self.ks_sale_order_id
        reason = self.ks_reason.strip()
        current_user = self.env.user
        
        if self.ks_action_type == 'approve_confirm':
            order._ks_do_approve_confirmation_with_reason(reason, current_user)
        elif self.ks_action_type == 'reject_confirm':
            order.ks_do_reject_confirmation(reason)
        elif self.ks_action_type == 'approve_cancel':
            order._ks_do_approve_cancel_with_reason(reason, current_user)
        elif self.ks_action_type == 'reject_cancel':
            order.ks_do_reject_cancel(reason)
        elif self.ks_action_type == 'approve_edit':
            order._ks_do_approve_edit_with_reason(reason, current_user)
        elif self.ks_action_type == 'reject_edit':
            order.ks_do_reject_edit(reason)
        else:
            raise UserError(_("Invalid action type."))
        
        return {'type': 'ir.actions.act_window_close'}

