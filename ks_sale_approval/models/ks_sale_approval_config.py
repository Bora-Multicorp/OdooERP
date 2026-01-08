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
    
    # PM Users for Confirmation Approval
    ks_confirm_pm1_id = fields.Many2one(
        'res.users',
        string='Confirmation Approver PM1',
        required=True,
        help='First/Primary approval manager for SO confirmation requests',
    )
    ks_confirm_pm2_id = fields.Many2one(
        'res.users',
        string='Confirmation Approver PM2',
        help='Second approval manager for SO confirmation requests (required for dual approval mode)',
    )
    
    # PM Users for Cancel Approval
    ks_cancel_pm1_id = fields.Many2one(
        'res.users',
        string='Cancel Approver PM1',
        required=True,
        help='First/Primary approval manager for SO cancel requests',
    )
    ks_cancel_pm2_id = fields.Many2one(
        'res.users',
        string='Cancel Approver PM2',
        help='Second approval manager for SO cancel requests (required for dual approval mode)',
    )
    
    # ===== PM Users for Edit Approval =====
    ks_edit_pm1_id = fields.Many2one(
        'res.users',
        string='Edit Approver PM1',
        required=True,
        help='First/Primary approval manager for SO edit requests',
    )
    ks_edit_pm2_id = fields.Many2one(
        'res.users',
        string='Edit Approver PM2',
        help='Second approval manager for SO edit requests (required for dual approval mode)',
    )
    
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('company_uniq', 'unique(company_id)', 
         'Only one approval configuration per company is allowed!'),
    ]

    @api.constrains('ks_approval_mode', 'ks_confirm_pm2_id', 'ks_cancel_pm2_id', 'ks_edit_pm2_id')
    def _check_dual_approval_pms(self):
        """Validate PM2 is set when dual approval mode is selected"""
        for record in self:
            if record.ks_approval_mode == 'dual':
                if not record.ks_confirm_pm2_id:
                    raise ValidationError(_(
                        "Confirmation Approver PM2 is required when using Two PM Approval mode!"
                    ))
                if not record.ks_cancel_pm2_id:
                    raise ValidationError(_(
                        "Cancel Approver PM2 is required when using Two PM Approval mode!"
                    ))
                if not record.ks_edit_pm2_id:
                    raise ValidationError(_(
                        "Edit Approver PM2 is required when using Two PM Approval mode!"
                    ))

    @api.constrains('ks_confirm_pm1_id', 'ks_confirm_pm2_id')
    def _check_confirm_pms_different(self):
        for record in self:
            if record.ks_confirm_pm2_id and record.ks_confirm_pm1_id == record.ks_confirm_pm2_id:
                raise ValidationError(_(
                    "Confirmation Approver PM1 and PM2 must be different users!"
                ))

    @api.constrains('ks_cancel_pm1_id', 'ks_cancel_pm2_id')
    def _check_cancel_pms_different(self):
        for record in self:
            if record.ks_cancel_pm2_id and record.ks_cancel_pm1_id == record.ks_cancel_pm2_id:
                raise ValidationError(_(
                    "Cancel Approver PM1 and PM2 must be different users!"
                ))

    @api.constrains('ks_edit_pm1_id', 'ks_edit_pm2_id')
    def _check_edit_pms_different(self):
        """Validate that Edit PM1 and PM2 are different users"""
        for record in self:
            if record.ks_edit_pm2_id and record.ks_edit_pm1_id == record.ks_edit_pm2_id:
                raise ValidationError(_(
                    "Edit Approver PM1 and PM2 must be different users!"
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
        pm_users = self.ks_confirm_pm1_id | self.ks_cancel_pm1_id | self.ks_edit_pm1_id
        if self.ks_confirm_pm2_id:
            pm_users |= self.ks_confirm_pm2_id
        if self.ks_cancel_pm2_id:
            pm_users |= self.ks_cancel_pm2_id
        if self.ks_edit_pm2_id:
            pm_users |= self.ks_edit_pm2_id
        return pm_users

    def get_confirm_pms(self):
        """Return PM users for confirmation approval"""
        self.ensure_one()
        pms = self.ks_confirm_pm1_id
        if self.ks_confirm_pm2_id:
            pms |= self.ks_confirm_pm2_id
        return pms

    def get_cancel_pms(self):
        """Return PM users for cancel approval"""
        self.ensure_one()
        pms = self.ks_cancel_pm1_id
        if self.ks_cancel_pm2_id:
            pms |= self.ks_cancel_pm2_id
        return pms

    def get_edit_pms(self):
        """Return PM users for edit approval"""
        self.ensure_one()
        pms = self.ks_edit_pm1_id
        if self.ks_edit_pm2_id:
            pms |= self.ks_edit_pm2_id
        return pms

    def is_dual_approval(self):
        """Check if dual approval mode is enabled"""
        self.ensure_one()
        return self.ks_approval_mode == 'dual'

