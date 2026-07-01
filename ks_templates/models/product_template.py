# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_advance_payment_product = fields.Boolean(
        string='Is Advance Payment Product',
        default=False,
        help='Mark this product as an advance payment product. Lines using this product will be excluded from printed PDFs.',
    )
