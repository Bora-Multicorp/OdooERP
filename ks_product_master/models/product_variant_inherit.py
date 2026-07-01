# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductProductVariant(models.Model):
    _inherit = 'product.product'

    part_code = fields.Char(
        string='Part Code / Manual Ref',
        help='Variant-level part code or marketplace identifier (ASIN, FSN, etc.). '
             'Stored per variant and not shared with other variants of the same product.',
        tracking=True,
        index=True,
    )
