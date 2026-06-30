# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # UC-A01: Maximum depth level setting
    layered_coa_max_depth = fields.Integer(
        string='Limit Layered COA',
        config_parameter='layered_coa.max_depth',
        default=0,
        help='Set the maximum number of parent-child hierarchy depth levels allowed '
             'for the Chart of Accounts. Set to 0 for unlimited depth.\n\n'
             'Example: a value of 3 means accounts can be nested at most 3 levels deep '
             '(e.g., Assets > Current Assets > Cash).\n\n'
             'Navigation: Accounting > Configuration > Settings > Accounting Configuration > '
             'Limit Layered COA',
    )

    @api.constrains('layered_coa_max_depth')
    def _check_layered_coa_max_depth(self):
        for rec in self:
            if rec.layered_coa_max_depth < 0:
                raise ValidationError(_(
                    'The Limit Layered COA value must be 0 (unlimited) or a positive integer.'
                ))
