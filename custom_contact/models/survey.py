# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import base64
import re
import werkzeug

FIELDS_TO_HIDE_FROM_FILTER = [
    'certification_badge_id',
    'certification_mail_template_id',
    'certification_report_layout',
    'color',
    'session_question_id',
    'session_start_time',
    'session_question_start_time',
    'progression_mode',
    'certification_give_badge',
    'certification',
    'is_attempts_limited',
    'attempts_limit',
    'session_speed_rating',
    'session_code',
    'session_state',
    'scoring_type',
    'is_time_limited',
    'users_can_go_back',
    'message_needaction',
    'activity_exception_decoration',
    'certification_badge_id_dummy',
    'message_has_error',
    'scoring_success_min',
    'time_limit',
    'website_message_ids',
    'message_has_sms_error',
    'activity_ids',
    'activity_state',
    'activity_type_icon',
    'background_image',
    'message_follower_ids',
    'message_partner_ids',
    'has_message',
    'message_is_follower',
    'message_ids',
    'my_activity_date_deadline',
    'activity_date_deadline',
    'activity_summary',
    'activity_type_id',

]

class InheritSurvey(models.Model):
    _inherit = 'survey.survey'
    _description = 'Form'


    survey_image = fields.Image("Survey Image")
    #quotation_content = fields.Html("Quotation Content", tracking=True)
    sms_history = fields.One2many("sms.history", "survey_id", string="Sms History", tracking=True)

    # Hide survey fields from searchable and filterable(group by) fields
    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """ Hide survey fields from filterable/searchable fields"""
        res = super(InheritSurvey, self).fields_get(allfields, attributes)
        fields_to_hide = FIELDS_TO_HIDE_FROM_FILTER
        for field in fields_to_hide:
            if res.get(field):
                res[field]['searchable'] = False
                res[field]['sortable'] = False
        return res

    # Inherit Share method for change Share a Survey name to share a Fact Find Form
    def action_send_survey(self):
        """ Inherit the original method """
        result = super(InheritSurvey, self).action_send_survey()
        if 'name' in result:
            result['name'] = "Share KYC Form"
        return result

    # Overide Start Survey method for change Start Survey name to start
    def action_start_survey(self, answer=None):
        print('11111111111')
        """ Open the website page with the survey form """
        self.ensure_one()
        url = '%s?%s' % (self.get_start_url(),
                         werkzeug.urls.url_encode({'answer_token': answer and answer.access_token or None}))
        return {
            'type': 'ir.actions.act_url',
            'name': "Start",
            'target': 'self',
            'url': url,
        }

class SMSHistoryMaintain(models.Model):
    _name = 'sms.history'
    _description = 'Maintain SMS History'

    contact_number = fields.Char("Contact Number")
    # Message_id = fields.Char("Message ID")
    message_id = fields.Char("Message ID")
    survey_id = fields.Many2one('survey.survey', string="Survey")
