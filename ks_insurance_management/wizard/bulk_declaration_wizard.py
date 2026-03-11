# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class BulkDeclarationWizard(models.TransientModel):
    _name = 'bulk.declaration.wizard'
    _description = 'Bulk Declaration Download Wizard'

    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)
    declaration_type = fields.Selection([
        ('marine', 'Marine'), ('fire_burglary', 'Fire & Burglary'), ('both', 'Both'),
    ], string='Declaration Type', required=True, default='both')
    company_ids = fields.Many2many(
        'res.company',
        string='Companies',
        default=lambda self: self.env.company,
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise UserError("Date From must be before Date To.")

    def action_generate_declarations(self):
        self.ensure_one()
        created = self.env['insurance.declaration']
        for company in self.company_ids:
            types = []
            if self.declaration_type in ('marine', 'both'):
                types.append('marine')
            if self.declaration_type in ('fire_burglary', 'both'):
                types.append('fire_burglary')
            for dtype in types:
                domain = [('company_id', '=', company.id), ('state', '=', 'active')]
                if dtype == 'marine':
                    domain.append(('is_marine', '=', True))
                else:
                    domain.append(('is_fire_burglary', '=', True))
                policies = self.env['insurance.policy'].search(domain)
                for policy in policies:
                    existing = self.env['insurance.declaration'].search([
                        ('policy_id', '=', policy.id),
                        ('date_from', '=', self.date_from),
                        ('date_to', '=', self.date_to),
                        ('declaration_type', '=', dtype),
                    ], limit=1)
                    if not existing:
                        decl = self.env['insurance.declaration'].create({
                            'policy_id': policy.id,
                            'company_id': company.id,
                            'declaration_type': dtype,
                            'date_from': self.date_from,
                            'date_to': self.date_to,
                        })
                        if dtype == 'marine':
                            decl._compute_marine_sales()
                        elif dtype == 'fire_burglary' and policy.floater_location_ids:
                            decl.warehouse_id = policy.floater_location_ids[0]
                            decl._compute_avg_inventory()
                        created |= decl
                    else:
                        created |= existing
        if not created:
            raise UserError("No active policies found for the selected criteria.")
        return self.env.ref(
            'ks_insurance_management.action_report_declaration_letter'
        ).report_action(created)
