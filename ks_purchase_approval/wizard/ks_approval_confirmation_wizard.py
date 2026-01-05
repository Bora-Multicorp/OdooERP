# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class KsApprovalConfirmationWizard(models.TransientModel):
    _name = 'ks.approval.confirmation.wizard'
    _description = 'KS Approval Confirmation Wizard'

    ks_purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        required=True,
    )
    ks_approver_1_id = fields.Many2one(
        'res.users',
        string='Approver 1',
        required=True,
        domain="[('id', 'in', ks_available_approver_1_ids)]",
        help='First approver for confirmation (must approve before Approver 2)',
    )
    ks_approver_2_id = fields.Many2one(
        'res.users',
        string='Approver 2',
        required=True,
        domain="[('id', 'in', ks_available_approver_2_ids)]",
        help='Second approver for confirmation (approves after Approver 1)',
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

    @api.depends('ks_purchase_order_id')
    def _compute_available_approvers(self):
        """Compute available approvers based on configuration"""
        for record in self:
            if record.ks_purchase_order_id and record.ks_purchase_order_id._has_approval_config():
                # Get users configured as Approver 1 for confirmation
                configs_approver_1 = self.env['ks.purchase.approval.config'].search([
                    ('active', '=', True),
                    ('ks_confirm_approver_type', '=', 'approver_1'),
                ])
                record.ks_available_approver_1_ids = configs_approver_1.mapped('user_id')
                
                # Get users configured as Approver 2 for confirmation
                configs_approver_2 = self.env['ks.purchase.approval.config'].search([
                    ('active', '=', True),
                    ('ks_confirm_approver_type', '=', 'approver_2'),
                ])
                record.ks_available_approver_2_ids = configs_approver_2.mapped('user_id')
            else:
                record.ks_available_approver_1_ids = False
                record.ks_available_approver_2_ids = False

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

    def action_confirm_send(self):
        """User confirms to send the approval request with selected approvers"""
        self.ensure_one()
        if not self.ks_approver_1_id or not self.ks_approver_2_id:
            raise UserError(_("Both Approver 1 and Approver 2 are required."))
        if self.ks_approver_1_id == self.ks_approver_2_id:
            raise UserError(_("Approver 1 and Approver 2 must be different users."))
        self.ks_purchase_order_id._ks_send_to_pending_approval(
            self.ks_approver_1_id.id,
            self.ks_approver_2_id.id
        )
        return {'type': 'ir.actions.act_window_close'}

