# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class KsRequestReasonWizard(models.TransientModel):
    _name = 'ks.request.reason.wizard'
    _description = 'KS Request Reason Wizard'

    ks_purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        required=True,
    )
    ks_request_type = fields.Selection([
        ('update', 'Update Request'),
        ('cancel', 'Cancellation Request'),
    ], string='Request Type', required=True)
    
    ks_approver_1_id = fields.Many2one(
        'res.users',
        string='Approver 1',
        required=True,
        domain="[('id', 'in', ks_available_approver_1_ids)]",
        help='First approver (must approve before Approver 2)',
    )
    ks_approver_2_id = fields.Many2one(
        'res.users',
        string='Approver 2',
        required=True,
        domain="[('id', 'in', ks_available_approver_2_ids)]",
        help='Second approver (approves after Approver 1)',
    )
    ks_available_approver_1_ids = fields.Many2many(
        'res.users',
        string='Available Approver 1 Users',
        compute='_compute_available_approvers',
    )
    ks_available_approver_2_ids = fields.Many2many(
        'res.users',
        string='Available Approver 2 Users',
        compute='_compute_available_approvers',
    )
    
    ks_reason = fields.Text(
        string='Reason',
        required=True,
        help='Please provide a reason for your request',
    )
    
    ks_request_type_label = fields.Char(
        string='Request Type Label',
        compute='_compute_request_type_label',
    )

    @api.depends('ks_request_type', 'ks_purchase_order_id')
    def _compute_available_approvers(self):
        """Compute available approvers based on request type and configuration"""
        for record in self:
            if record.ks_purchase_order_id and record.ks_purchase_order_id._has_approval_config():
                approval_type = 'update' if record.ks_request_type == 'update' else 'cancel'
                approver_type_field = {
                    'update': 'ks_update_approver_type',
                    'cancel': 'ks_cancel_approver_type',
                }.get(approval_type)
                
                if approver_type_field:
                    # Get users configured as Approver 1
                    configs_approver_1 = self.env['ks.purchase.approval.config'].search([
                        ('active', '=', True),
                        (approver_type_field, '=', 'approver_1'),
                    ])
                    record.ks_available_approver_1_ids = configs_approver_1.mapped('user_id')
                    
                    # Get users configured as Approver 2
                    configs_approver_2 = self.env['ks.purchase.approval.config'].search([
                        ('active', '=', True),
                        (approver_type_field, '=', 'approver_2'),
                    ])
                    record.ks_available_approver_2_ids = configs_approver_2.mapped('user_id')
                else:
                    record.ks_available_approver_1_ids = False
                    record.ks_available_approver_2_ids = False
            else:
                record.ks_available_approver_1_ids = False
                record.ks_available_approver_2_ids = False

    @api.depends('ks_request_type')
    def _compute_request_type_label(self):
        for record in self:
            if record.ks_request_type == 'update':
                record.ks_request_type_label = _('Update Request')
            elif record.ks_request_type == 'cancel':
                record.ks_request_type_label = _('Cancellation Request')
            else:
                record.ks_request_type_label = ''

    @api.constrains('ks_approver_1_id', 'ks_approver_2_id')
    def _check_approvers_different(self):
        """Ensure Approver 1 and Approver 2 are different users"""
        for record in self:
            if record.ks_approver_1_id and record.ks_approver_2_id:
                if record.ks_approver_1_id == record.ks_approver_2_id:
                    raise UserError(_("Approver 1 and Approver 2 must be different users."))

    @api.onchange('ks_approver_1_id')
    def _onchange_approver_1(self):
        """Clear Approver 2 if it's the same as Approver 1"""
        if self.ks_approver_1_id and self.ks_approver_2_id:
            if self.ks_approver_1_id == self.ks_approver_2_id:
                self.ks_approver_2_id = False

    @api.onchange('ks_approver_2_id')
    def _onchange_approver_2(self):
        """Clear Approver 1 if it's the same as Approver 2"""
        if self.ks_approver_1_id and self.ks_approver_2_id:
            if self.ks_approver_1_id == self.ks_approver_2_id:
                self.ks_approver_1_id = False

    def action_submit_request(self):
        """Submit the request with the provided reason and approvers"""
        self.ensure_one()
        
        if not self.ks_reason or not self.ks_reason.strip():
            raise UserError(_("Please provide a reason for your request."))
        
        if not self.ks_approver_1_id or not self.ks_approver_2_id:
            raise UserError(_("Both Approver 1 and Approver 2 are required."))
        
        if self.ks_approver_1_id == self.ks_approver_2_id:
            raise UserError(_("Approver 1 and Approver 2 must be different users."))
        
        order = self.ks_purchase_order_id
        reason = self.ks_reason.strip()
        
        if self.ks_request_type == 'update':
            order.ks_do_request_update(reason, self.ks_approver_1_id.id, self.ks_approver_2_id.id)
        elif self.ks_request_type == 'cancel':
            order.ks_do_request_cancel(reason, self.ks_approver_1_id.id, self.ks_approver_2_id.id)
        else:
            raise UserError(_("Invalid request type."))
        
        return {'type': 'ir.actions.act_window_close'}
