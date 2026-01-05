# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class VendorApprovalConfig(models.Model):
    _name = "vendor.approval.config"
    _description = "Vendor Approval Settings"
    _rec_name = 'user_id'
    _order = 'approver_type, user_id'

    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        tracking=True,
        help='User assigned as approver',
        domain="[('share', '=', False)]"
    )

    approver_type = fields.Selection([
        ('approver1', 'Approver 1'),
        ('approver2', 'Approver 2'),
    ], string="Approver Type", required=True, tracking=True)

    _sql_constraints = [
        ('unique_user_approver_type', 'unique(user_id, approver_type)',
         'This user is already configured for this approver type.'),
    ]

    def get_approver1_users(self):
        """Get all users configured as Approver 1"""
        return self.search([('approver_type', '=', 'approver1')]).mapped('user_id')

    def get_approver2_users(self):
        """Get all users configured as Approver 2"""
        return self.search([('approver_type', '=', 'approver2')]).mapped('user_id')

    def get_all_approval_users(self):
        """Get all users assigned to any approval level"""
        approver1 = self.get_approver1_users()
        approver2 = self.get_approver2_users()
        return approver1 | approver2

    @api.model
    def get_config(self):
        """Get approval configuration (for backward compatibility)"""
        # Return any config record for backward compatibility
        return self.search([], limit=1)
