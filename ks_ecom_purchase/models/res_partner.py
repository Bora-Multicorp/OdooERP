# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    created_for_ecom = fields.Boolean(
        string="Created for E-com Import",
        default=False,
        help="Set to True when the partner (vendor) was created via the E-com Purchase Order XLSX import.",
    )
