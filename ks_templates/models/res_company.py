# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    stamp_image = fields.Binary(
        string="Company Stamp",
        attachment=True,
        help="Upload/save company stamp image to be displayed on PDF reports.",
    )
