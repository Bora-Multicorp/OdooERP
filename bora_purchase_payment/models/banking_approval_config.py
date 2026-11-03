# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BankingApprovalConfig(models.Model):
    _name = 'banking.approval.config'
    _description = 'Banking Authorised Approvers'
    _rec_name = 'name'

    name = fields.Char(
        string='Configuration Name',
        default='Global Banking Approval Configuration',
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
    ], string='Approval Mode', required=True, default='single',
       help='Single Level: Any approver from Approvers 1 list can approve.\n'
            'Two Level: Approvers from both Approvers 1 and Approvers 2 are configured.')

    # Approver Users - Multiple users support
    ks_approver_1_ids = fields.Many2many(
        'res.users',
        'banking_approval_approver_1_rel',
        'config_id',
        'user_id',
        string='Approvers 1',
        required=True,
        help='First/Primary approvers for payment approval requests',
    )
    ks_approver_2_ids = fields.Many2many(
        'res.users',
        'banking_approval_approver_2_rel',
        'config_id',
        'user_id',
        string='Approvers 2',
        help='Second approvers for payment approval requests (required for two level approval mode)',
    )

    active = fields.Boolean(default=True)

    @api.constrains('active')
    def _check_single_active_config(self):
        """Ensure only one active configuration exists globally"""
        for record in self:
            if record.active:
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
        """Get the global approval configuration (applies to all companies)."""
        return self.sudo().search([('active', '=', True)], limit=1)

    def get_all_approvers(self):
        """Return all approver users configured in the system for this config"""
        self.ensure_one()
        if self.ks_approval_mode == 'two_way':
            return self.ks_approver_1_ids | self.ks_approver_2_ids
        return self.ks_approver_1_ids

    def get_approvers_by_level(self, approver_level):
        """Get approvers for a specific level (approver1 / approver_1 or approver2 / approver_2)"""
        self.ensure_one()
        if approver_level in ('approver1', 'approver_1'):
            return self.ks_approver_1_ids
        elif approver_level in ('approver2', 'approver_2'):
            return self.ks_approver_2_ids
        return self.env['res.users']

    def is_two_way_approval(self):
        """Check if two-way approval mode is enabled"""
        self.ensure_one()
        return self.ks_approval_mode == 'two_way'

    @api.model
    def get_approval_mode(self):
        config = self.sudo().get_config()
        if config:
            return config.ks_approval_mode
        return 'single'
