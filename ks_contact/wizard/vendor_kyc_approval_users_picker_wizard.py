# -*- coding: utf-8 -*-

from odoo import api, fields, models


class POConfirmationApprovalUsersPicker(models.TransientModel):
    _name = 'vendor.kyc.approval.user.picker.wizard'
    _description = 'vendor.kyc.approval users picker'

    user_ids_according_to_user_selection = fields.Char(store=True)

    kyc_id = fields.Many2one('res.partner.kyc.approval', string="Approval for Vendor Kyc Confirmation")

    approval_level_1_user_id = fields.Many2one(
        'res.users',
        string="Approval Level 1",
        readonly=True,
    )

    approval_level_2_user_id = fields.Many2one(
        'res.users',
        string="Approval Level 2",
        readonly=True,
    )

    add_button_disabled = fields.Boolean(
        string="Disable Add Button",
        compute='_compute_add_button_disabled'
    )

    @api.depends('approval_level_1_user_id', 'approval_level_2_user_id')
    def _compute_add_button_disabled(self):
        for rec in self:
            rec.add_button_disabled = not (rec.approval_level_1_user_id or rec.approval_level_2_user_id)

    def add_users_for_approval(self):
        """Add selected users to approval workflow"""
        if not self.kyc_id:
            return
        
        # Create approval_users_ids records directly
        # This bypasses the need for vendor.approval.config records
        approval_vals = []
        
        if self.approval_level_1_user_id:
            approval_vals.append((0, 0, {
                'sequence': 1,
                'user_id': self.approval_level_1_user_id.id
            }))
        
        if self.approval_level_2_user_id:
            approval_vals.append((0, 0, {
                'sequence': 2,
                'user_id': self.approval_level_2_user_id.id
            }))
        
        if approval_vals:
            # Write approval users and trigger parallel approval flow
            self.kyc_id.write({
                'approval_users_ids': approval_vals,
                'state': 'pending'
            })
            # Create activities for all approvers simultaneously (parallel approval)
            self.kyc_id._schedule_parallel_approval_activities()

    @api.model
    def default_get(self, fields):
        """Load configured approval level users from Vendor Approval Settings"""
        res = super().default_get(fields)
        
        # Get approval config for current company
        config = self.env['vendor.approval.config'].get_config()
        
        if config:
            # Load configured users (read-only display)
            if 'approval_level_1_user_id' in fields and config.approval_level_1_user_id:
                res['approval_level_1_user_id'] = config.approval_level_1_user_id.id
            
            if 'approval_level_2_user_id' in fields and config.approval_level_2_user_id:
                res['approval_level_2_user_id'] = config.approval_level_2_user_id.id
            
            # Update user_ids_according_to_user_selection for backward compatibility
            user_ids = []
            if config.approval_level_1_user_id:
                user_ids.append(str(config.approval_level_1_user_id.id))
            if config.approval_level_2_user_id:
                user_ids.append(str(config.approval_level_2_user_id.id))
            if 'user_ids_according_to_user_selection' in fields:
                res['user_ids_according_to_user_selection'] = ','.join(user_ids)

        return res
