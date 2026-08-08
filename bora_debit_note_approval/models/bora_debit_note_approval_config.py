# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BoraDebitNoteApprovalConfig(models.Model):
    _name = 'bora.debit.note.approval.config'
    _description = 'Bora Debit Note Approval Configuration'
    _rec_name = 'name'

    name = fields.Char(
        string='Configuration Name',
        required=True,
    )
    bora_dn_approval_mode = fields.Selection([
        ('single', 'Single Approver (PM1 Only)'),
        ('dual', 'Two Approvers (Both Required)'),
    ], string='Approval Mode', required=True, default='single',
       help='Single: One PM1 approval allows the debit note to be confirmed.\n'
            'Dual: Both PM1 and PM2 must approve before confirmation.')

    bora_dn_company_ids = fields.Many2many(
        'res.company',
        'bora_debit_note_approval_company_rel',
        'config_id', 'company_id',
        string='Applicable Companies',
        help='Restrict this approval configuration to the selected companies. '
             'Leave empty to apply globally to all companies. '
             'Approver 1 and Approver 2 users are filtered to members of these companies.',
    )

    bora_dn_pm1_ids = fields.Many2many(
        'res.users',
        'bora_debit_note_approval_pm1_rel',
        'config_id', 'user_id',
        string='Debit Note Approvers PM1',
        required=True,
        domain="[('company_ids', 'in', bora_dn_company_ids), ('share', '=', False)] "
               "if bora_dn_company_ids else [('share', '=', False)]",
    )
    bora_dn_pm2_ids = fields.Many2many(
        'res.users',
        'bora_debit_note_approval_pm2_rel',
        'config_id', 'user_id',
        string='Debit Note Approvers PM2',
        domain="[('company_ids', 'in', bora_dn_company_ids), ('share', '=', False)] "
               "if bora_dn_company_ids else [('share', '=', False)]",
    )
    active = fields.Boolean(default=True)

    @api.constrains('bora_dn_approval_mode', 'bora_dn_pm2_ids')
    def _check_dual_approval_pms(self):
        for record in self:
            if record.bora_dn_approval_mode == 'dual' and not record.bora_dn_pm2_ids:
                raise ValidationError(_(
                    'Debit Note Approvers PM2 are required when using Two Approver mode!'
                ))

    @api.model
    def get_config(self, company=None):
        """
        Return the best-matching active configuration for the given company.

        Lookup order:
          1. Active config that explicitly lists the company in bora_dn_company_ids.
          2. Active config with no companies set (global / fallback).
        Returns an empty recordset if nothing matches.
        """
        if company:
            specific = self.search([
                ('active', '=', True),
                ('bora_dn_company_ids', 'in', company.id),
            ], limit=1)
            if specific:
                return specific

        # Global (no company restriction) fallback
        return self.search([
            ('active', '=', True),
            ('bora_dn_company_ids', '=', False),
        ], limit=1)

    def get_all_pm_users(self):
        self.ensure_one()
        return self.bora_dn_pm1_ids | self.bora_dn_pm2_ids

    def is_dual_approval(self):
        self.ensure_one()
        return self.bora_dn_approval_mode == 'dual'
