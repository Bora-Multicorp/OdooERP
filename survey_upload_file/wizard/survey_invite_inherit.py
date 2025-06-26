# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import requests
import json
from odoo.exceptions import UserError, ValidationError


class InheritSurveyInvite(models.TransientModel):
    _inherit = 'survey.invite'
    _description = 'Survey Invite Inherit'


    send_by_sms = fields.Boolean("Send By SMS")
    sms_recipient = fields.Many2one("res.partner", "SMS Recipients")
    mobile_no = fields.Char("Mobile Number")

    @api.onchange('sms_recipient')
    def _onchange_recipient(self):
        self.mobile_no = self.sms_recipient.mobile

    # Overide subject
    @api.depends('template_id', 'partner_ids')
    def _compute_subject(self):
        for invite in self:
            if invite.subject:
                continue
            else:
                invite.subject = _("%(survey_name)s", survey_name=invite.survey_id.display_name)

    def send_sms(self):
        # account_sid = self.env['ir.config_parameter'].sudo().get_param(
        #     'survey_management.account_sid') or False

        auth_token = self.env['ir.config_parameter'].sudo().get_param(
            'survey_management.auth_token') or False

        send_from = self.env['ir.config_parameter'].sudo().get_param(
            'survey_management.send_from') or False

        url = "https://api.gunisms.com.au/api/v1/gateway"

        payload = json.dumps({
            "sender": send_from,
            "message": self.survey_start_url + "\n Do not reply to this number",
            "contacts": [
                self.mobile_no
            ]
        })
        headers = {
            'Authorization': 'Bearer %s' % auth_token,
            'Content-Type': 'application/json'
        }

        response = requests.request("POST", url, headers=headers, data=payload)

        print(response.text)
        resp = json.loads(response.text)

        if resp['message'] and resp['message'] == 'Token expired':
            raise ValidationError(_("Token expired"))

        if len(resp['error']) != 0:
            raise ValidationError(_("Invalid Number %s. They should start with 0 or 61 followed by 9 digits") % self.mobile_no)
        else:
            self.env['sms.history'].sudo().create({
                'message_id': resp['data']['queueResponse'][0]['MessageId'] if resp['data']['queueResponse'] else '',
                'contact_number': self.mobile_no,
                'create_date': fields.datetime.now(),
                'create_uid': self.env.user,
                'survey_id': self.survey_id.id
            })

            message = _(
                "SMS Sent Successfully")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'target': 'new',
                'params': {
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }