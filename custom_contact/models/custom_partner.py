# -*- coding: utf-8 -*-
from email.policy import default

from odoo import api, fields, models


class CustomContact(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)

        action_id = options.get('action_id')
        contact_action = self.env.ref('contacts.action_contacts', raise_if_not_found=False)

        if action_id and contact_action and action_id != contact_action.id:
            if view_type in ('kanban', 'list', 'form'):
                for node in arch.xpath('//form | //kanban | //list'):
                    node.set('create', 'false')
        return arch, view

    custom_type = fields.Many2one('res.partner.location.type', string="Type", tracking=True,
                                  help='Contact Location Type', copy=False)
    custom_address_type = fields.Many2one('res.partner.address.type', string="Address Type", tracking=True,
                                          help='Contact Address Type', copy=False)
    tally_name = fields.Char(string="Tally Name", tracking=True)
    purpose = fields.Char(string="Purpose", tracking=True)
    # Customer/Vendor KYC Details
    is_vendor = fields.Boolean(string="Is Vendor?", tracking=True)
    is_customer = fields.Boolean(string="Is Customer?", tracking=True)
    is_kyc = fields.Boolean(string="Is KYC?", tracking=True)
    is_approved = fields.Boolean(string="Is Approved?", tracking=True)
    deadline = fields.Date('KYC Deadline', tracking=True)

    kyc_details = fields.One2many('res.partner.kyc.approval', 'partner_id', string="KYC Details", tracking=True)

    def write(self, vals):
        res = super().write(vals)
        if vals.get('is_approved') is True:
            for record in self:
                if record.is_vendor:
                    record.supplier_rank = (record.supplier_rank or 0) + 1
                if record.is_customer:
                    record.customer_rank = (record.customer_rank or 0) + 1
        return res

    def confirm_rekyc(self):
        self.write({'is_kyc': False, 'is_approved': False, 'deadline': False})
        if self.is_vendor:
             self.write({'supplier_rank': 0})
        if self.is_customer:
             self.write({'customer_rank': 0})

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
        action['domain'] = ['|', ('partner_id', '=', self.id), ('email', '=', self.email)]
        return action




