# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    default_code = fields.Char(
        string='Internal Reference',
        index=True,
        required=True,
        copy=False,
        help='Unique internal reference (e.g. SKU) for the product. Required and must be unique across all products.',
    )

    @api.constrains('default_code')
    def _check_default_code_unique_and_filled(self):
        for product in self:
            if not (product.default_code or '').strip():
                raise ValidationError(
                    _('Internal Reference is required for every product.')
                )
            duplicate = self.search([
                ('default_code', '=', product.default_code),
                ('id', '!=', product.id),
            ], limit=1)
            if duplicate:
                raise ValidationError(
                    _(
                        'Internal Reference "%(ref)s" is already used by product "%(name)s". '
                        'It must be unique.',
                        ref=product.default_code,
                        name=duplicate.display_name,
                    )
                )
