# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BoraInsuranceApprovalConfig(models.Model):
    _name = 'bora.insurance.approval.config'
    _description = 'Bora Insurance Approval Configuration'
    _rec_name = 'name'

    name = fields.Char(
        string='Configuration Name',
        required=True,
    )
    bora_approval_mode = fields.Selection([
        ('single', 'Single Approver (PM1 Only)'),
        ('dual', 'Two Approvers (Both Required)'),
    ], string='Approval Mode', required=True, default='single',
       help='Single: One PM1 approval allows the insurance payment to be approved.\n'
            'Dual: Both PM1 and PM2 must approve before insurance payment approval.')

    bora_company_ids = fields.Many2many(
        'res.company',
        'bora_insurance_approval_company_rel',
        'config_id', 'company_id',
        string='Applicable Companies',
        help='Restrict this approval configuration to the selected companies. '
             'Leave empty to apply globally to all companies. '
             'Approver 1 and Approver 2 users are filtered to members of these companies.',
    )

    bora_insurance_pm1_ids = fields.Many2many(
        'res.users',
        'bora_insurance_approval_pm1_rel',
        'config_id', 'user_id',
        string='Payment Approvers PM1',
        required=True,
        domain="[('company_ids', 'in', bora_company_ids), ('share', '=', False)] "
               "if bora_company_ids else [('share', '=', False)]",
    )
    bora_insurance_pm2_ids = fields.Many2many(
        'res.users',
        'bora_insurance_approval_pm2_rel',
        'config_id', 'user_id',
        string='Payment Approvers PM2',
        domain="[('company_ids', 'in', bora_company_ids), ('share', '=', False)] "
               "if bora_company_ids else [('share', '=', False)]",
    )
    active = fields.Boolean(default=True)

    @api.constrains('bora_approval_mode', 'bora_insurance_pm2_ids')
    def _check_dual_approval_pms(self):
        for record in self:
            if record.bora_approval_mode == 'dual' and not record.bora_insurance_pm2_ids:
                raise ValidationError(_(
                    'Payment Approvers PM2 are required when using Two Approver mode!'
                ))

    @api.model
    def get_config(self, company=None):
        """
        Return the best-matching active configuration for the given company.

        Lookup order:
          1. Active config that explicitly lists the company in bora_company_ids.
          2. Active config with no companies set (global / fallback).
          3. Any active config fallback.
        Returns an empty recordset if nothing matches.
        """
        configs = self.search([('active', '=', True)])
        if not configs:
            return self.browse()

        target_company = company or self.env.company
        config = self.browse()
        if target_company:
            specific = configs.filtered(lambda c: target_company in c.bora_company_ids)
            if specific:
                config = specific[0]

        if not config:
            global_cfg = configs.filtered(lambda c: not c.bora_company_ids)
            if global_cfg:
                config = global_cfg[0]

        if not config:
            config = configs[0]

        if config:
            config._sync_payment_approvers()
        return config

    def get_all_pm_users(self):
        self.ensure_one()
        return self.bora_insurance_pm1_ids | self.bora_insurance_pm2_ids

    def is_dual_approval(self):
        self.ensure_one()
        return self.bora_approval_mode == 'dual'

    def _sync_payment_approvers(self):
        """Ensure insurance.payment.approver records exist for all users in this configuration."""
        Approver = self.env['insurance.payment.approver']
        for config in self:
            if not config.active:
                continue
            companies = config.bora_company_ids or self.env['res.company'].search([])
            pm_users = config.get_all_pm_users()
            for comp in companies:
                for user in pm_users:
                    existing = Approver.search([
                        ('user_id', '=', user.id),
                        ('company_id', '=', comp.id),
                    ], limit=1)
                    if not existing:
                        Approver.sudo().create({
                            'name': user.name,
                            'user_id': user.id,
                            'company_id': comp.id,
                            'active': True,
                        })
                    elif not existing.active:
                        existing.sudo().write({'active': True})

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_payment_approvers()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._sync_payment_approvers()
        return res


class InsurancePaymentApprover(models.Model):
    _inherit = 'insurance.payment.approver'

    @api.constrains('active', 'company_id', 'user_id')
    def _check_single_active_approver(self):
        """Allow multiple active approver records per company (unique per user and company)."""
        for rec in self:
            if not rec.active or not rec.user_id or not rec.company_id:
                continue
            duplicate = self.search([
                ('company_id', '=', rec.company_id.id),
                ('user_id', '=', rec.user_id.id),
                ('active', '=', True),
                ('id', '!=', rec.id),
            ], limit=1)
            if duplicate:
                raise ValidationError(
                    f"'{rec.user_id.name}' is already an active Insurance Payment Approver for "
                    f"'{rec.company_id.name}'."
                )
