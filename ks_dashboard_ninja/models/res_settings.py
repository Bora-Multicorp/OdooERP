# -*- coding: utf-8 -*-

import json

import requests
from odoo.exceptions import ValidationError

from odoo import fields, models, _


class ResConfig(models.TransientModel):
    _inherit = "res.config.settings"

    dn_api_key = fields.Char(string="Dashboard AI API Key",store=True, config_parameter='ks_dashboard_ninja.dn_api_key')
    enable_chart_zoom = fields.Boolean(string="Enable Zooming for charts", store=True, config_parameter='ks_dashboard_ninja.enable_chart_zoom')
    enable_auto_update = fields.Boolean(string="Enable Auto Update", store=True, config_parameter='ks_dashboard_ninja.enable_auto_update', default=False,
                                        help="Enable automatic dashboard updates when records are created or modified. When disabled, notifications will only be sent if a client is actively subscribed to the dashboard channel.")

    url = fields.Char(string="URL", store=True, config_parameter="ks_dashboard_ninja.url")
    ks_email_id = fields.Char(string="Email ID",store=True,config_parameter="ks_dashboard_ninja.ks_email_id")
    ks_analysis_word_length = fields.Selection([("50", "50 words"),("100", "100 words"),("150", "150 words"),("200", "200 words")], default ="100",
                                               string="AI Analysis length", store=True,config_parameter="ks_dashboard_ninja.ks_analysis_word_length")

    # FIXME: does we have to send mail ?? cant we directly set api key in the database???
    def Open_wizard(self):
        if self.url and self.ks_email_id:
            try:
                # FIXME: check url have slashes at the end of , if so remove them
                url = self.url + "/api/v1/ks_dn_fetch_api"
                json_data = {'email':self.ks_email_id,
                         'url': self.env['ir.config_parameter'].sudo().get_param('web.base.url'),
                         'db_name': self.env.cr.dbname
                            }
                ks_ai_response = requests.post(url,data=json_data)
            except Exception as e:
                raise ValidationError(_("Please enter correct URL"))
            if ks_ai_response.status_code == 200:
                try:
                    ks_ai_response = json.loads(ks_ai_response.text)
                except Exception as e:
                    ks_ai_response = False
                if ks_ai_response == "success":
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Success'),
                            'message': 'API key sent on Email ID',
                            'sticky': False,
                        }
                    }
                elif ks_ai_response == 'key already generated':
                    raise ValidationError(_("Key already generated.If you need assistance, feel free to contact at sales@ksolves.com"))
                else:
                    raise ValidationError(_("Either you have entered wrong URL path or there is some problem in sending request. If you need assistance, feel free to contact at sales@ksolves.com"))
            else:
                raise ValidationError(_("Some problem in sending request.Please contact at sales@ksolves.com"))
        else:
            raise ValidationError(_("Please enter URL and Email ID"))
