# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class POConfirmationApprovalUsersPicker(models.TransientModel):
    _name = 'vendor.kyc.approval.user.picker.wizard'
    _description = 'vendor.kyc.approval users picker'

    kyc_id = fields.Many2one('res.partner.kyc.approval', string="Approval for Vendor Kyc Confirmation")

    approver1_user_ids = fields.Many2many(
        comodel_name='res.users',
        compute='_compute_approver_user_ids',
        string="Available Approver 1 Users",
        store=False
    )
    
    approver2_user_ids = fields.Many2many(
        comodel_name='res.users',
        compute='_compute_approver_user_ids',
        string="Available Approver 2 Users",
        store=False
    )

    approver1_user = fields.Many2one(
        comodel_name='res.users',
        string="Approver 1",
        required=True,
        domain="[('id', 'in', approver1_user_ids)]"
    )

    approver2_user = fields.Many2one(
        comodel_name='res.users',
        string="Approver 2",
        required=True,
        domain="[('id', 'in', approver2_user_ids)]"
    )

    add_button_disabled = fields.Boolean(
        string="Disable Add Button",
        compute='_compute_add_button_disabled'
    )

    @api.depends('kyc_id')
    def _compute_approver_user_ids(self):
        """Compute available approver users from config"""
        for rec in self:
            config = self.env['vendor.approval.config'].get_config()
            if config:
                # Get users configured as Approver 1
                rec.approver1_user_ids = config.ks_approver_1_ids
                # Get users configured as Approver 2
                rec.approver2_user_ids = config.ks_approver_2_ids
            else:
                rec.approver1_user_ids = False
                rec.approver2_user_ids = False

    @api.depends('approver1_user', 'approver2_user')
    def _compute_add_button_disabled(self):
        for rec in self:
            rec.add_button_disabled = not (rec.approver1_user and rec.approver2_user)

    @api.onchange('approver1_user')
    def _onchange_approver1_user(self):
        """Validate approver 1 selection"""
        if self.approver1_user and self.approver2_user == self.approver1_user:
            self.approver2_user = False

    @api.onchange('approver2_user')
    def _onchange_approver2_user(self):
        """Validate approver 2 selection"""
        if self.approver2_user and self.approver1_user == self.approver2_user:
            self.approver1_user = False

    def add_users_for_approval(self):
        """Add selected users to approval workflow (sequential)"""
        if not self.kyc_id:
            raise ValidationError(_("KYC record is missing."))
        
        if not self.approver1_user or not self.approver2_user:
            raise ValidationError(_("Please select both Approver 1 and Approver 2."))
        
        # Create approval_users_ids records with sequence
        # Approver 1 gets sequence 1, Approver 2 gets sequence 2
        approval_vals = []
        
        approval_vals.append((0, 0, {
            'sequence': 1,
            'user_id': self.approver1_user.id
        }))
        
        approval_vals.append((0, 0, {
            'sequence': 2,
            'user_id': self.approver2_user.id
        }))
        
        if approval_vals:
            # Write approval users and trigger sequential approval flow
            self.kyc_id.write({
                'approval_users_ids': approval_vals,
                'state': 'pending',
                'kyc_approval_creator': self.env.user.id
            })
            # Create activity only for first approver (sequential approval)
            self.kyc_id._schedule_sequential_approval_activities()
