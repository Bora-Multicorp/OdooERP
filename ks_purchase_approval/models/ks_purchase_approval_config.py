# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class KsPurchaseApprovalConfig(models.Model):
    _name = 'ks.purchase.approval.config'
    _description = 'KS Purchase Approval Configuration'
    _rec_name = 'company_id'

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    
    # PM Users for Confirmation Approval
    ks_confirm_pm1_id = fields.Many2one(
        'res.users',
        string='Confirmation Approver PM1',
        required=True,
        help='First approval manager for PO confirmation requests',
    )
    ks_confirm_pm2_id = fields.Many2one(
        'res.users',
        string='Confirmation Approver PM2',
        required=True,
        help='Second approval manager for PO confirmation requests',
    )
    
    # PM Users for Update Approval
    ks_update_pm1_id = fields.Many2one(
        'res.users',
        string='Update Approver PM1',
        related="ks_confirm_pm1_id",
        required=True,
        help='First approval manager for PO update requests',
    )
    ks_update_pm2_id = fields.Many2one(
        'res.users',
        string='Update Approver PM2',
        related="ks_confirm_pm2_id",
        required=True,
        help='Second approval manager for PO update requests',
    )
    
    # PM Users for Cancel Approval
    ks_cancel_pm1_id = fields.Many2one(
        'res.users',
        string='Cancel Approver PM1',
        related="ks_confirm_pm1_id",
        required=True,
        help='First approval manager for PO cancel requests',
    )
    ks_cancel_pm2_id = fields.Many2one(
        'res.users',
        string='Cancel Approver PM2',
        related="ks_confirm_pm2_id",
        required=True,
        help='Second approval manager for PO cancel requests',
    )
    
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('company_uniq', 'unique(company_id)', 
         'Only one approval configuration per company is allowed!'),
    ]

    @api.constrains('ks_confirm_pm1_id', 'ks_confirm_pm2_id')
    def _check_confirm_pms_different(self):
        for record in self:
            if record.ks_confirm_pm1_id == record.ks_confirm_pm2_id:
                raise ValidationError(_(
                    "Confirmation Approver PM1 and PM2 must be different users!"
                ))

    @api.constrains('ks_update_pm1_id', 'ks_update_pm2_id')
    def _check_update_pms_different(self):
        for record in self:
            if record.ks_update_pm1_id == record.ks_update_pm2_id:
                raise ValidationError(_(
                    "Update Approver PM1 and PM2 must be different users!"
                ))

    @api.constrains('ks_cancel_pm1_id', 'ks_cancel_pm2_id')
    def _check_cancel_pms_different(self):
        for record in self:
            if record.ks_cancel_pm1_id == record.ks_cancel_pm2_id:
                raise ValidationError(_(
                    "Cancel Approver PM1 and PM2 must be different users!"
                ))

    @api.model
    def get_config(self, company_id=None):
        """Get approval configuration for the specified or current company"""
        if not company_id:
            company_id = self.env.company.id
        config = self.search([('company_id', '=', company_id)], limit=1)
        return config

    def get_all_pm_users(self):
        """Return all PM users configured in the system for this config"""
        self.ensure_one()
        return (
            self.ks_confirm_pm1_id | self.ks_confirm_pm2_id |
            self.ks_update_pm1_id | self.ks_update_pm2_id |
            self.ks_cancel_pm1_id | self.ks_cancel_pm2_id
        )

