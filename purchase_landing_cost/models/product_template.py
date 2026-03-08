# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_foc = fields.Boolean(
        string="FOC (Free of Cost)",
        default=False,
        help="Free of Cost item; duty is still applicable on assessable value.",
    )
