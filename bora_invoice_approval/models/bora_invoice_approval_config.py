# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BoraInvoiceApprovalConfig(models.Model):
    _name = 'bora.invoice.approval.config'
    _description = 'Bora Invoice Approval Configuration'
    _rec_name = 'name'

    name = fields.Char(string='Configuration Name', required=True)

    bora_inv_company_ids = fields.Many2many(
        'res.company',
        'bora_invoice_approval_company_rel',
        'config_id', 'company_id',
        string='Applicable Companies',
        help='Restrict this configuration to selected companies. '
             'Leave empty to act as a global fallback for all companies.',
    )
    active = fields.Boolean(default=True)

    # ── Local sale (Customer from India) ─────────────────────────────────────
    bora_inv_local_approval_mode = fields.Selection([
        ('single', 'Single Approver (PM1 Only)'),
        ('dual', 'Two Approvers (Both Required)'),
    ], string='Local Approval Mode', required=True, default='single')

    bora_inv_local_pm1_ids = fields.Many2many(
        'res.users',
        'bora_invoice_approval_local_pm1_rel',
        'config_id', 'user_id',
        string='Local Approvers PM1',
        domain="[('company_ids', 'in', bora_inv_company_ids), ('share', '=', False)] "
               "if bora_inv_company_ids else [('share', '=', False)]",
    )
    bora_inv_local_pm2_ids = fields.Many2many(
        'res.users',
        'bora_invoice_approval_local_pm2_rel',
        'config_id', 'user_id',
        string='Local Approvers PM2',
        domain="[('company_ids', 'in', bora_inv_company_ids), ('share', '=', False)] "
               "if bora_inv_company_ids else [('share', '=', False)]",
    )

    # ── Export / Foreign sale (Customer NOT from India) ───────────────────────
    bora_inv_export_approval_mode = fields.Selection([
        ('single', 'Single Approver (PM1 Only)'),
        ('dual', 'Two Approvers (Both Required)'),
    ], string='Export Approval Mode', required=True, default='single')

    bora_inv_export_pm1_ids = fields.Many2many(
        'res.users',
        'bora_invoice_approval_export_pm1_rel',
        'config_id', 'user_id',
        string='Export Approvers PM1',
        domain="[('company_ids', 'in', bora_inv_company_ids), ('share', '=', False)] "
               "if bora_inv_company_ids else [('share', '=', False)]",
    )
    bora_inv_export_pm2_ids = fields.Many2many(
        'res.users',
        'bora_invoice_approval_export_pm2_rel',
        'config_id', 'user_id',
        string='Export Approvers PM2',
        domain="[('company_ids', 'in', bora_inv_company_ids), ('share', '=', False)] "
               "if bora_inv_company_ids else [('share', '=', False)]",
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Constraints
    # ─────────────────────────────────────────────────────────────────────────
    @api.constrains('bora_inv_local_approval_mode', 'bora_inv_local_pm1_ids',
                    'bora_inv_local_pm2_ids')
    def _check_local_approval(self):
        for record in self:
            if not record.bora_inv_local_pm1_ids:
                raise ValidationError(_('Local Approvers PM1 is required.'))
            if record.bora_inv_local_approval_mode == 'dual' and not record.bora_inv_local_pm2_ids:
                raise ValidationError(_(
                    'Local Approvers PM2 is required when using Two Approver mode for Local sale!'
                ))

    @api.constrains('bora_inv_export_approval_mode', 'bora_inv_export_pm1_ids',
                    'bora_inv_export_pm2_ids')
    def _check_export_approval(self):
        for record in self:
            if not record.bora_inv_export_pm1_ids:
                raise ValidationError(_('Export Approvers PM1 is required.'))
            if record.bora_inv_export_approval_mode == 'dual' and not record.bora_inv_export_pm2_ids:
                raise ValidationError(_(
                    'Export Approvers PM2 is required when using Two Approver mode for Export sale!'
                ))

    # ─────────────────────────────────────────────────────────────────────────
    # Query helpers
    # ─────────────────────────────────────────────────────────────────────────
    @api.model
    def get_config(self, company=None):
        """Return best-matching active config for the given company.
        Priority: company-specific first, then global (no companies set), then any active config fallback.
        """
        configs = self.search([('active', '=', True)])
        if not configs:
            return self.browse()

        target_company = company or self.env.company
        if target_company:
            specific = configs.filtered(lambda c: target_company in c.bora_inv_company_ids)
            if specific:
                return specific[0]

        global_cfg = configs.filtered(lambda c: not c.bora_inv_company_ids)
        if global_cfg:
            return global_cfg[0]

        return configs[0]

    def get_approvers_for_sale_type(self, is_local):
        """Return (approval_mode, pm1_ids, pm2_ids) for local or export."""
        self.ensure_one()
        if is_local:
            return (self.bora_inv_local_approval_mode,
                    self.bora_inv_local_pm1_ids,
                    self.bora_inv_local_pm2_ids)
        return (self.bora_inv_export_approval_mode,
                self.bora_inv_export_pm1_ids,
                self.bora_inv_export_pm2_ids)

    def get_all_pm_users(self):
        """Return all configured PM users (local + export) — used for admin bypass check."""
        self.ensure_one()
        return (self.bora_inv_local_pm1_ids | self.bora_inv_local_pm2_ids |
                self.bora_inv_export_pm1_ids | self.bora_inv_export_pm2_ids)

    def is_dual_approval(self, is_local):
        self.ensure_one()
        mode = self.bora_inv_local_approval_mode if is_local else self.bora_inv_export_approval_mode
        return mode == 'dual'
