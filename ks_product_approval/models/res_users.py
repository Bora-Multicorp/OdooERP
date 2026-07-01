# -*- coding: utf-8 -*-

from odoo import api, fields, models

class ResUsers(models.Model):
    _inherit = 'res.users'

    is_custom_admin = fields.Boolean(string="Is Admin", default=False)