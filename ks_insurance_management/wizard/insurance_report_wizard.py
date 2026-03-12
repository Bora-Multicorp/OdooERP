# -*- coding: utf-8 -*-

from odoo import fields, models, _
from odoo.exceptions import UserError


# Map report_type to (xml_id, report_name) for fallback lookup
REPORT_ACTIONS = {
    'fire_burglary': (
        'ks_insurance_management.action_report_fire_burglary',
        'ks_insurance_management.report_fire_burglary_template',
    ),
    'marine': (
        'ks_insurance_management.action_report_marine',
        'ks_insurance_management.report_marine_template',
    ),
    'misc': (
        'ks_insurance_management.action_report_misc',
        'ks_insurance_management.report_misc_template',
    ),
}


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

    def _get_report_action(self, report_type):
        """Resolve report action by xml_id or report_name (avoids External ID not found)."""
        xml_id, report_name = REPORT_ACTIONS[report_type]
        report = self.env.ref(xml_id, raise_if_not_found=False)
        if not report or report._name != 'ir.actions.report':
            report = self.env['ir.actions.report'].search(
                [('report_name', '=', report_name)], limit=1
            )
        if not report:
            raise UserError(
                _('Report "%s" not found. Please upgrade the Insurance Management module (Apps → KS Insurance Management → Upgrade).')
                % report_name
            )
        return report.report_action(self)

    def action_print_fire_burglary(self):
        self.report_type = 'fire_burglary'
        return self._get_report_action('fire_burglary')

    def action_print_marine(self):
        self.report_type = 'marine'
        return self._get_report_action('marine')

    def action_print_misc(self):
        self.report_type = 'misc'
        return self._get_report_action('misc')
