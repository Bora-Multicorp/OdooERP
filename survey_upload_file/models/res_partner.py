# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.osv import expression


class Partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    survey_ids = fields.One2many('survey.user_input', 'partner_id', string='Surveys')
    survey_count = fields.Integer(string="Survey Count",
                                  groups='sales_team.group_sale_salesman',
                                  compute='_compute_survey_count')

    def _compute_survey_count(self):
        for partner in self:
            if not self.env.user._has_group('sales_team.group_sale_salesman'):
                partner.survey_count = 0
                continue

            # Get self and child partners
            all_partners = self.with_context(active_test=False).search([('id', 'child_of', partner.id)])
            partner_ids = all_partners.ids
            partner_emails = [p.email for p in all_partners if p.email]

            # Search for surveys by partner_id or email
            domain = ['|',
                      ('partner_id', 'in', partner_ids),
                      ('email', 'in', partner_emails)]

            survey_count = self.env['survey.user_input'].with_context(active_test=False).search_count(domain)
            partner.survey_count = survey_count

    def action_view_survey_response(self):
        '''
        This function returns an action that displays the survey response from partner.
        '''
        action = self.env['ir.actions.act_window']._for_xml_id('survey.action_survey_user_input')
        action['domain'] = ['|',('partner_id', '=', self.id), ('email', '=', self.email)]
        return action
