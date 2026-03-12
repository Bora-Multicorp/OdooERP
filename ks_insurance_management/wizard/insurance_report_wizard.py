# -*- coding: utf-8 -*-

from odoo import fields, models


class InsuranceReportWizard(models.TransientModel):
    _name = 'insurance.report.wizard'
    _description = 'Insurance Report Wizard'

    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    company_ids = fields.Many2many(
        'res.company',
        string='Companies',
        default=lambda self: self.env.company,
    )
    report_type = fields.Selection([
        ('fire_burglary', 'Fire & Burglary'),
        ('marine', 'Marine'),
        ('misc', 'Miscellaneous'),
    ], string='Report Type', default='fire_burglary')

    def _get_policies(self):
        domain = [('state', '=', 'active')]
        if self.company_ids:
            domain.append(('company_id', 'in', self.company_ids.ids))
        if self.report_type == 'fire_burglary':
            domain.append(('is_fire_burglary', '=', True))
        elif self.report_type == 'marine':
            domain.append(('is_marine', '=', True))
        elif self.report_type == 'misc':
            domain.append(('is_misc', '=', True))
        return self.env['insurance.policy'].search(domain)

    def action_print_fire_burglary(self):
        self.report_type = 'fire_burglary'
        return self.env.ref(
            'ks_insurance_management.action_report_fire_burglary'
        ).report_action(self)

    def action_print_marine(self):
        self.report_type = 'marine'
        return self.env.ref(
            'ks_insurance_management.action_report_marine'
        ).report_action(self)

    def action_print_misc(self):
        self.report_type = 'misc'
        return self.env.ref(
            'ks_insurance_management.action_report_misc'
        ).report_action(self)
