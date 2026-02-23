# -*- coding: utf-8 -*-

import json
import logging

import requests
from odoo.exceptions import ValidationError

from odoo import fields, models, _

_logger = logging.getLogger(__name__)

# FIXME: is this model used where ???
class KsAIDashboardFetch(models.TransientModel):
    _name = 'ks_dashboard_ninja.fetch_key'
    _description = 'Fetch API key'

    ks_email_id = fields.Char(string="Email ID")
    ks_api_key =fields.Char(string="Generated AI API Key")
    ks_show_api_key = fields.Boolean(string="Show key", default=False)

    def ks_fetch_details(self):
        url = self.env['ir.config_parameter'].sudo().get_param('ks_dashboard_ninja.url')
        # FIXME: check url have slashes at the end of , if so remove them
        if url and self.ks_email_id:
            url = url + "/api/v1/ks_dn_fetch_api"
            ks_ai_response = requests.post(url, data={'email': self.ks_email_id})
            if ks_ai_response.status_code == 200:
                ks_ai_response = json.loads(ks_ai_response.text)
                self.ks_api_key = ks_ai_response
                self.ks_show_api_key = True
                # FIXME: does we have to send mail ?? cant we directly set api key in the database???
            else:
                raise ValidationError(_("Error generates with following status %s"), ks_ai_response.status_code)
