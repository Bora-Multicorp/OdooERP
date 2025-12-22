# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class VendorApprovalConfig(models.Model):
    _name = "vendor.approval.config"
    _description = "Vendor Approval Settings"
    _rec_name = 'company_id'
    _order = 'company_id'

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    approval_level_1_user_id = fields.Many2one(
        'res.users',
        string='Approval Level 1',
        required=True,
        tracking=True,
        help='User assigned to Approval Level 1. This user cannot be assigned to Level 2.',
        domain="[('id', '!=', approval_level_2_user_id), ('share', '=', False)]"
    )

    approval_level_2_user_id = fields.Many2one(
        'res.users',
        string='Approval Level 2',
        required=True,
        tracking=True,
        help='User assigned to Approval Level 2. This user cannot be assigned to Level 1.',
        domain="[('id', '!=', approval_level_1_user_id), ('share', '=', False)]"
    )

    # Legacy fields for backward compatibility (deprecated)
    sequence = fields.Integer(string='Sequence', index=True, tracking=True)
    user_id = fields.Many2one('res.users', string='User (Legacy)', tracking=True)
    default_user = fields.Boolean(string="Default (Legacy)")
    default_approver = fields.Selection([
        ('approver1', 'Approver 1'),
        ('approver2', 'Approver 2'),
    ], string="Default (Legacy)")
    color = fields.Integer(string="Color Index", readonly=True)

    _sql_constraints = [
        ('unique_company', 'unique(company_id)', 'Only one approval configuration per company is allowed.'),
        ('different_users', 'CHECK(approval_level_1_user_id != approval_level_2_user_id)', 
         'Approval Level 1 and Level 2 must have different users.'),
    ]

    @api.constrains('approval_level_1_user_id', 'approval_level_2_user_id')
    def _check_different_users(self):
        """Ensure Level 1 and Level 2 users are different"""
        for record in self:
            if record.approval_level_1_user_id and record.approval_level_2_user_id:
                if record.approval_level_1_user_id == record.approval_level_2_user_id:
                    raise ValidationError(_(
                        "Approval Level 1 and Approval Level 2 must have different users. "
                        "The same user cannot be assigned to both levels."
                    ))

    @api.model
    def default_get(self, fields_list):
        """Set default company"""
        defaults = super().default_get(fields_list)
        if 'company_id' not in defaults:
            defaults['company_id'] = self.env.company.id
        return defaults

    @api.model
    def create(self, vals):
        """Create approval config with validation"""
        # Check if config already exists for this company
        if vals.get('company_id'):
            existing = self.search([('company_id', '=', vals['company_id'])])
            if existing:
                raise ValidationError(_(
                    "Approval configuration already exists for company '%s'. "
                    "Please update the existing configuration instead."
                ) % self.env['res.company'].browse(vals['company_id']).name)

        # Validate both users are set
        if not vals.get('approval_level_1_user_id') or not vals.get('approval_level_2_user_id'):
            raise ValidationError(_(
                "Both Approval Level 1 and Approval Level 2 users must be configured."
            ))

        # Validate users are different
        if vals.get('approval_level_1_user_id') == vals.get('approval_level_2_user_id'):
            raise ValidationError(_(
                "Approval Level 1 and Approval Level 2 must have different users."
            ))

        return super().create(vals)

    def write(self, vals):
        """Update approval config with validation"""
        # Validate users are different if both are being updated
        if 'approval_level_1_user_id' in vals and 'approval_level_2_user_id' in vals:
            if vals['approval_level_1_user_id'] == vals['approval_level_2_user_id']:
                raise ValidationError(_(
                    "Approval Level 1 and Approval Level 2 must have different users."
                ))
        elif 'approval_level_1_user_id' in vals:
            # Level 1 is being updated, check against existing Level 2
            for record in self:
                if vals['approval_level_1_user_id'] == record.approval_level_2_user_id.id:
                    raise ValidationError(_(
                        "Approval Level 1 user cannot be the same as Approval Level 2 user."
                    ))
        elif 'approval_level_2_user_id' in vals:
            # Level 2 is being updated, check against existing Level 1
            for record in self:
                if vals['approval_level_2_user_id'] == record.approval_level_1_user_id.id:
                    raise ValidationError(_(
                        "Approval Level 2 user cannot be the same as Approval Level 1 user."
                    ))

        return super().write(vals)

    def get_approval_level_1_users(self):
        """Get all users assigned to Approval Level 1 across all companies"""
        return self.search([]).mapped('approval_level_1_user_id')

    def get_approval_level_2_users(self):
        """Get all users assigned to Approval Level 2 across all companies"""
        return self.search([]).mapped('approval_level_2_user_id')

    def get_all_approval_users(self):
        """Get all users assigned to any approval level (for backward compatibility)"""
        level1 = self.get_approval_level_1_users()
        level2 = self.get_approval_level_2_users()
        return level1 | level2

    @api.model
    def get_config(self, company_id=None):
        """Get approval configuration for the specified or current company"""
        if not company_id:
            company_id = self.env.company.id
        return self.search([('company_id', '=', company_id)], limit=1)
