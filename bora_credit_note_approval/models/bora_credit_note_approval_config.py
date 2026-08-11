# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BoraCreditNoteApprovalConfig(models.Model):
    _name = 'bora.credit.note.approval.config'
    _description = 'Bora Credit Note Approval Configuration'
    _rec_name = 'name'

    name = fields.Char(
        string='Configuration Name',
        required=True,
    )
    bora_cn_approval_mode = fields.Selection([
        ('single', 'Single Approver (PM1 Only)'),
        ('dual', 'Two Approvers (Both Required)'),
    ], string='Approval Mode', required=True, default='single',
       help='Single: One PM1 approval allows the credit note to be confirmed.\n'
            'Dual: Both PM1 and PM2 must approve before confirmation.')

    bora_cn_company_ids = fields.Many2many(
        'res.company',
        'bora_credit_note_approval_company_rel',
        'config_id', 'company_id',
        string='Applicable Companies',
        help='Restrict this approval configuration to the selected companies. '
             'Leave empty to apply globally to all companies. '
             'Approver 1 and Approver 2 users are filtered to members of these companies.',
    )

    bora_cn_pm1_ids = fields.Many2many(
        'res.users',
        'bora_credit_note_approval_pm1_rel',
        'config_id', 'user_id',
        string='Credit Note Approvers PM1',
        required=True,
        domain="[('company_ids', 'in', bora_cn_company_ids), ('share', '=', False)] "
               "if bora_cn_company_ids else [('share', '=', False)]",
    )
    bora_cn_pm2_ids = fields.Many2many(
        'res.users',
        'bora_credit_note_approval_pm2_rel',
        'config_id', 'user_id',
        string='Credit Note Approvers PM2',
        domain="[('company_ids', 'in', bora_cn_company_ids), ('share', '=', False)] "
               "if bora_cn_company_ids else [('share', '=', False)]",
    )
    active = fields.Boolean(default=True)

    @api.constrains('bora_cn_approval_mode', 'bora_cn_pm2_ids')
    def _check_dual_approval_pms(self):
        for record in self:
            if record.bora_cn_approval_mode == 'dual' and not record.bora_cn_pm2_ids:
                raise ValidationError(_(
                    'Credit Note Approvers PM2 are required when using Two Approver mode!'
                ))

    @api.model
    def get_config(self, company=None):
        """
        Return the best-matching active configuration for the given company.

        Lookup order:
          1. Active config that explicitly lists the company in bora_cn_company_ids.
          2. Active config with no companies set (global / fallback).
          3. Any active config fallback.
        Returns an empty recordset if nothing matches.
        """
        configs = self.search([('active', '=', True)])
        if not configs:
            return self.browse()

        target_company = company or self.env.company
        if target_company:
            specific = configs.filtered(lambda c: target_company in c.bora_cn_company_ids)
            if specific:
                return specific[0]

        global_cfg = configs.filtered(lambda c: not c.bora_cn_company_ids)
        if global_cfg:
            return global_cfg[0]

        return configs[0]

    def get_all_pm_users(self):
        self.ensure_one()
        return self.bora_cn_pm1_ids | self.bora_cn_pm2_ids

    def is_dual_approval(self):
        self.ensure_one()
        return self.bora_cn_approval_mode == 'dual'
