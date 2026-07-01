# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class KsPurchaseApprovalConfig(models.Model):
    _name = 'ks.purchase.approval.config'
    _description = 'KS Purchase Approval Configuration'
    _rec_name = 'name'

    name = fields.Char(
        string='Configuration Name',
        default='Global Purchase Approval Configuration',
        required=True,
        help='Name for this approval configuration. Only one active configuration is allowed.',
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=False,
        readonly=True,
        help='This field is kept for backward compatibility but is not used. Configuration is global for all companies.',
    )
    
    # Approval Mode - Single or Two Level approval
    ks_approval_mode = fields.Selection([
        ('single', 'Single Level Approval'),
        ('two_way', 'Two Level Approval'),
    ], string='Approval Mode', required=True, default='two_way',
       help='Single Level: Only Approver 1 needs to approve.\n'
            'Two Level: Both Approver 1 and Approver 2 must approve before PO is confirmed.')
    
    # Approver Users - Multiple users support
    ks_approver_1_ids = fields.Many2many(
        'res.users',
        'ks_purchase_approval_approver_1_rel',
        'config_id',
        'user_id',
        string='Approvers 1',
        required=True,
        help='First/Primary approvers for PO approval requests (select one when requesting approval)',
    )
    ks_approver_2_ids = fields.Many2many(
        'res.users',
        'ks_purchase_approval_approver_2_rel',
        'config_id',
        'user_id',
        string='Approvers 2',
        help='Second approvers for PO approval requests (select one when requesting approval, required for two level approval mode)',
    )
    
    active = fields.Boolean(default=True)

    @api.constrains('active')
    def _check_single_active_config(self):
        """Ensure only one active configuration exists globally"""
        for record in self:
            if record.active:
                # Check for other active configs
                other_active = self.search([
                    ('active', '=', True),
                    ('id', '!=', record.id),
                ], limit=1)
                if other_active:
                    raise ValidationError(_(
                        'Only one active global approval configuration is allowed! '
                        'Please deactivate the existing configuration "%s" (ID: %s) before activating this one.'
                    ) % (other_active.name or 'Unnamed', other_active.id))

    @api.constrains('ks_approval_mode', 'ks_approver_2_ids')
    def _check_two_way_approval_approvers(self):
        """Validate Approver 2 is set when two level approval mode is selected"""
        for record in self:
            if record.ks_approval_mode == 'two_way':
                if not record.ks_approver_2_ids:
                    raise ValidationError(_(
                        "Approvers 2 are required when using Two Level Approval mode!"
                    ))

    @api.model
    def get_config(self, company_id=None):
        """Get the global approval configuration (applies to all companies). Use sudo so only admin can open the config UI."""
        config = self.sudo().search([('active', '=', True)], limit=1)
        return config

    def get_all_approvers(self):
        """Return all approver users configured in the system for this config"""
        self.ensure_one()
        approvers = self.ks_approver_1_ids | self.ks_approver_2_ids
        return approvers

    def get_approvers_by_level(self, approver_level):
        """
        Get approvers for a specific level (approver_1 or approver_2)
        Returns list of user_ids who are configured for this level
        """
        self.ensure_one()
        if approver_level == 'approver_1':
            return self.ks_approver_1_ids
        elif approver_level == 'approver_2':
            return self.ks_approver_2_ids
        return self.env['res.users']

    def is_two_way_approval(self):
        """Check if two-way approval mode is enabled"""
        self.ensure_one()
        return self.ks_approval_mode == 'two_way'
    
    @api.model
    def get_approval_mode(self):
        """Get the system-wide approval mode (single or two_way)"""
        config = self.sudo().get_config()
        if config:
            return config.ks_approval_mode
        # Default to two_way if no config exists
        return 'two_way'
