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
    vendor_reg_url = fields.Char("Vendor Registration URL")
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
class InheritSurveyQuestion(models.Model):
    _inherit = "survey.question"

    is_pan = fields.Boolean("Is PAN")
    #is_mobile = fields.Boolean("Is Mobile")
    #is_pincode = fields.Boolean("Is Pincode")
    is_gstin = fields.Boolean("Is GSTIN")
    is_udyam = fields.Boolean("Is Udyam")
    is_cin = fields.Boolean("Is CIN number")

    def _validate_char_box(self, answer):
        errors = {}

        if self.is_pan:
            if answer and not re.fullmatch(r'[A-Z]{5}[0-9]{4}[A-Z]', answer.upper()):
                errors[self.id] = _(
                    'Invalid PAN: "%s". Format must be 5 uppercase letters, 4 digits, 1 letter (e.g., ABCDE1234F).'
                ) % answer

        # if self.is_mobile:
        #     if answer and not re.fullmatch(r'[6-9]\d{9}', answer):
        #         errors[self.id] = _(
        #             'Invalid Mobile Number: "%s". It must be exactly 10 digits and start with 6-9 (e.g., 9876543210).'
        #         ) % answer
        #
        # if self.is_pincode:
        #     if answer and not re.fullmatch(r'\d{6}', answer):
        #         errors[self.id] = _(
        #             'Invalid Pincode: "%s". It must be exactly 6 digits (e.g., 400001).'
        #         ) % answer

        if self.is_gstin:
            if answer and not re.fullmatch(r'\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}Z[A-Z\d]{1}', answer.upper()):
                errors[self.id] = _(
                    'Invalid GSTIN: "%s". Format must be 15 characters-(e.g.,12ABCDE1234F1Z5).'
                ) % answer

        if self.is_udyam:
            if answer and not re.fullmatch(r'^UDYAM-[A-Z]{2}-\d{2}-\d{7}$', answer.upper()):
                errors[self.id] = _(
                    'Invalid Udyam No: "%s". Format is UDYAM-XX-00-0000000(e.g.,UDYAM-MH-12-1234567).'
                ) % answer

        if self.is_cin:
            if answer and not re.fullmatch(r'[UL][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}', answer.upper()):
                errors[self.id] = _(
                    'Invalid CIN: "%s".\nExpected format: U12345MH2000PLC123456\n'
                    #'(1 letter + 5 digits + 2 letters + 4 digits + 3 letters + 6 digits).'
                ) % answer
        return errors


class SMSHistoryMaintain(models.Model):
    _name = 'sms.history'
    _description = 'Maintain SMS History'

    contact_number = fields.Char("Contact Number")
    # Message_id = fields.Char("Message ID")
    message_id = fields.Char("Message ID")
    survey_id = fields.Many2one('survey.survey', string="Survey")
