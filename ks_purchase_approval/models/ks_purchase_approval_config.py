# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class KsPurchaseApprovalConfig(models.Model):
    _name = 'ks.purchase.approval.config'
    _description = 'KS Purchase Approval Configuration'
    _rec_name = 'user_id'
    _check_company_auto = False

    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        index=True,
        help='User for whom this approval configuration applies',
    )
    
    # Approver Types
    ks_confirm_approver_type = fields.Selection([
        ('approver_1', 'Approver 1'),
        ('approver_2', 'Approver 2'),
    ], string='Confirmation Approver Type', required=True,
        help='Approver type for PO confirmation requests')
    
    ks_update_approver_type = fields.Selection([
        ('approver_1', 'Approver 1'),
        ('approver_2', 'Approver 2'),
    ], string='Update Approver Type', required=True,
        help='Approver type for PO update requests')
    
    ks_cancel_approver_type = fields.Selection([
        ('approver_1', 'Approver 1'),
        ('approver_2', 'Approver 2'),
    ], string='Cancel Approver Type', required=True,
        help='Approver type for PO cancel requests')
    
    active = fields.Boolean(default=True)

    @api.constrains('user_id', 'ks_confirm_approver_type')
    def _check_confirm_approver_duplicate(self):
        """Check individually for Confirmation approver type duplicates"""
        for record in self:
            duplicates = self.search([
                ('id', '!=', record.id),
                ('user_id', '=', record.user_id.id),
                ('ks_confirm_approver_type', '=', record.ks_confirm_approver_type),
            ])
            if duplicates:
                raise ValidationError(_(
                    "User '%s' already has a configuration as Confirmation %s. "
                    "A user can have both Approver 1 and Approver 2, but not duplicate records for the same approver type."
                ) % (record.user_id.name, dict(record._fields['ks_confirm_approver_type'].selection)[record.ks_confirm_approver_type]))

    @api.constrains('user_id', 'ks_update_approver_type')
    def _check_update_approver_duplicate(self):
        """Check individually for Update approver type duplicates"""
        for record in self:
            duplicates = self.search([
                ('id', '!=', record.id),
                ('user_id', '=', record.user_id.id),
                ('ks_update_approver_type', '=', record.ks_update_approver_type),
            ])
            if duplicates:
                raise ValidationError(_(
                    "User '%s' already has a configuration as Update %s. "
                    "A user can have both Approver 1 and Approver 2, but not duplicate records for the same approver type."
                ) % (record.user_id.name, dict(record._fields['ks_update_approver_type'].selection)[record.ks_update_approver_type]))

    @api.constrains('user_id', 'ks_cancel_approver_type')
    def _check_cancel_approver_duplicate(self):
        """Check individually for Cancel approver type duplicates"""
        for record in self:
            duplicates = self.search([
                ('id', '!=', record.id),
                ('user_id', '=', record.user_id.id),
                ('ks_cancel_approver_type', '=', record.ks_cancel_approver_type),
            ])
            if duplicates:
                raise ValidationError(_(
                    "User '%s' already has a configuration as Cancel %s. "
                    "A user can have both Approver 1 and Approver 2, but not duplicate records for the same approver type."
                ) % (record.user_id.name, dict(record._fields['ks_cancel_approver_type'].selection)[record.ks_cancel_approver_type]))

    @api.model
    def get_config_for_user(self, user_id=None):
        """Get approval configuration for the specified or current user"""
        if not user_id:
            user_id = self.env.user.id
        config = self.search([('user_id', '=', user_id), ('active', '=', True)], limit=1)
        return config

    def get_approvers_by_type(self, approval_type):
        """
        Get approvers based on approval type (confirm, update, cancel)
        Returns list of user_ids who are configured as Approver 1 or Approver 2 for this type
        """
        self.ensure_one()
        approver_type_field = {
            'confirm': 'ks_confirm_approver_type',
            'update': 'ks_update_approver_type',
            'cancel': 'ks_cancel_approver_type',
        }.get(approval_type)
        
        if not approver_type_field:
            return self.env['res.users']
        
        approver_type = getattr(self, approver_type_field)
        # Return users who have this approver type configured
        domain = [
            ('active', '=', True),
            (approver_type_field, '=', approver_type),
        ]
        configs = self.search(domain)
        return configs.mapped('user_id')

    def get_all_approvers(self):
        """Return all users configured as approvers in the system"""
        configs = self.search([('active', '=', True)])
        return configs.mapped('user_id')

