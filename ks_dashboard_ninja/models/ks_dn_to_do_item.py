# -*- coding: utf-8 -*-

import json
import re

from odoo.exceptions import ValidationError
from odoo.addons.ks_dashboard_ninja.common_lib.dn_utils import clean_dict_in_place
from odoo import models, fields, api, _


class KsDashboardNinjaItems(models.Model):
    _inherit = 'ks_dashboard_ninja.item'

    ks_to_do_preview = fields.Char("To Do Preview", default="To Do Preview")
    ks_dn_header_lines = fields.One2many('ks_to.do.headers', 'ks_dn_item_id')
    ks_to_do_data = fields.Char(string="To Do Data in JSon", compute='ks_get_to_do_view_data', compute_sudo=False)
    ks_header_bg_color = fields.Char(string="Header Background Color", default="#8e24aa,0.99",
                                     help=' Select the background color with transparency. ')

    @api.depends('ks_dn_header_lines', 'ks_dashboard_item_type')
    def ks_get_to_do_view_data(self):
        for rec in self:
            ks_to_do_data = json.dumps(rec.get_todo_data())
            rec.ks_to_do_data = ks_to_do_data

    def get_todo_data(self):
        data = []
        for header_line in self.ks_dn_header_lines:
            header_lines_dict = header_line.read(['ks_to_do_header', 'ks_to_do_description_lines'])[0]
            clean_dict_in_place(header_lines_dict)
            header_lines_dict['ks_to_do_description_lines'] = header_line.ks_to_do_description_lines.read(['ks_description', 'ks_active'])
            for description_line in header_lines_dict['ks_to_do_description_lines']:
                clean_dict_in_place(description_line)
            data.append(header_lines_dict)
        return data

    def clean_dict_in_place(data):
        """Removes non-serializable keys from a dictionary in place."""
        for key in list(data.keys()):
            try:
                json.dumps(data[key])
            except (TypeError, OverflowError):
                del data[key]


class KsToDoheaders(models.Model):
    _name = 'ks_to.do.headers'
    _description = "to do headers"
    _order = 'id desc'

    ks_dn_item_id = fields.Many2one('ks_dashboard_ninja.item')
    ks_to_do_header = fields.Char('Header')
    ks_to_do_description_lines = fields.One2many('ks_to.do.description', 'ks_to_do_header_id')

    # FIXME: no need for on constrains
    @api.constrains('ks_to_do_header')
    def ks_to_do_header_check(self):
        for rec in self:
            if rec.ks_to_do_header:
                ks_check = bool(re.match('^[A-Z, a-z,0-9,_]+$', rec.ks_to_do_header))
                if not ks_check:
                    raise ValidationError(_("Special characters are not allowed only string and digits allow for section header"))

    # FIXME: no need for on changes
    @api.onchange('ks_to_do_header')
    def ks_to_do_header_onchange(self):
        for rec in self:
            if rec.ks_to_do_header:
                ks_check = bool(re.match('^[A-Z, a-z,0-9,_]+$', rec.ks_to_do_header))
                if not ks_check:
                    raise ValidationError(_("Special characters are not allowed only string and digits allow for section header"))

class KsToDODescription(models.Model):
    _name = 'ks_to.do.description'
    _description = 'to do description'
    _order = 'id desc'

    ks_to_do_header_id = fields.Many2one('ks_to.do.headers')
    ks_description = fields.Text('Description')
    ks_active = fields.Boolean('Active Description', default=False)
