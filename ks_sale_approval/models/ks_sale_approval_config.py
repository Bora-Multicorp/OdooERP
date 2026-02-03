# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class KsSaleApprovalConfig(models.Model):
    _name = 'ks.sale.approval.config'
    _description = 'KS Sale Approval Configuration'
    _rec_name = 'company_id'

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    
    # Approval Mode - Single or Two PM approval
    ks_approval_mode = fields.Selection([
        ('single', 'Single PM Approval'),
        ('dual', 'Two PM Approval (Both Required)'),
    ], string='Approval Mode', required=True, default='single',
       help='Single: One PM approval confirms the SO.\n'
            'Dual: Both PM1 and PM2 must approve before SO is confirmed.')
    
    # PM Users for Confirmation Approval - Multiple users support
    ks_confirm_pm1_ids = fields.Many2many(
        'res.users',
        'ks_sale_approval_confirm_pm1_rel',
        'config_id',
        'user_id',
        string='Confirmation Approvers PM1',
        required=True,
        help='First/Primary approval managers for SO confirmation requests (select one when requesting approval)',
    )
    ks_confirm_pm2_ids = fields.Many2many(
        'res.users',
        'ks_sale_approval_confirm_pm2_rel',
        'config_id',
        'user_id',
        string='Confirmation Approvers PM2',
        help='Second approval managers for SO confirmation requests (select one when requesting approval, required for dual approval mode)',
    )
    
    # PM Users for Cancel Approval - Multiple users support
    ks_cancel_pm1_ids = fields.Many2many(
        'res.users',
        'ks_sale_approval_cancel_pm1_rel',
        'config_id',
        'user_id',
        string='Cancel Approvers PM1',
        required=True,
        help='First/Primary approval managers for SO cancel requests (select one when requesting approval)',
    )
    ks_cancel_pm2_ids = fields.Many2many(
        'res.users',
        'ks_sale_approval_cancel_pm2_rel',
        'config_id',
        'user_id',
        string='Cancel Approvers PM2',
        help='Second approval managers for SO cancel requests (select one when requesting approval, required for dual approval mode)',
    )
    
    # ===== PM Users for Edit Approval - Multiple users support =====
    ks_edit_pm1_ids = fields.Many2many(
        'res.users',
        'ks_sale_approval_edit_pm1_rel',
        'config_id',
        'user_id',
        string='Edit Approvers PM1',
        required=True,
        help='First/Primary approval managers for SO edit requests (select one when requesting approval)',
    )
    ks_edit_pm2_ids = fields.Many2many(
        'res.users',
        'ks_sale_approval_edit_pm2_rel',
        'config_id',
        'user_id',
        string='Edit Approvers PM2',
        help='Second approval managers for SO edit requests (select one when requesting approval, required for dual approval mode)',
    )
    
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('company_uniq', 'unique(company_id)', 
         'Only one approval configuration per company is allowed!'),
    ]

    @api.constrains('ks_approval_mode', 'ks_confirm_pm2_ids', 'ks_cancel_pm2_ids', 'ks_edit_pm2_ids')
    def _check_dual_approval_pms(self):
        """Validate PM2 is set when dual approval mode is selected"""
        for record in self:
            if record.ks_approval_mode == 'dual':
                if not record.ks_confirm_pm2_ids:
                    raise ValidationError(_(
                        "Confirmation Approvers PM2 are required when using Two PM Approval mode!"
                    ))
                if not record.ks_cancel_pm2_ids:
                    raise ValidationError(_(
                        "Cancel Approvers PM2 are required when using Two PM Approval mode!"
                    ))
                if not record.ks_edit_pm2_ids:
                    raise ValidationError(_(
                        "Edit Approvers PM2 are required when using Two PM Approval mode!"
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
        pm_users = self.ks_confirm_pm1_ids | self.ks_cancel_pm1_ids | self.ks_edit_pm1_ids
        pm_users |= self.ks_confirm_pm2_ids
        pm_users |= self.ks_cancel_pm2_ids
        pm_users |= self.ks_edit_pm2_ids
        return pm_users

    def get_confirm_pms(self):
        """Return PM users for confirmation approval"""
        self.ensure_one()
        pms = self.ks_confirm_pm1_ids | self.ks_confirm_pm2_ids
        return pms

    def get_cancel_pms(self):
        """Return PM users for cancel approval"""
        self.ensure_one()
        pms = self.ks_cancel_pm1_ids | self.ks_cancel_pm2_ids
        return pms

    def get_edit_pms(self):
        """Return PM users for edit approval"""
        self.ensure_one()
        pms = self.ks_edit_pm1_ids | self.ks_edit_pm2_ids
        return pms

    def is_dual_approval(self):
        """Check if dual approval mode is enabled"""
        self.ensure_one()
        return self.ks_approval_mode == 'dual'

