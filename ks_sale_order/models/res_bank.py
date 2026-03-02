# -*- coding: utf-8 -*-

from odoo import fields, models


class ResBank(models.Model):
    _inherit = 'res.bank'

    # Rename Bank Identifier Code to Account Number (override label only)
    bic = fields.Char(
        string='Account Number',
        index=True,
        help='Account Number (sometimes called BIC or Swift).',
    )
    swift_code = fields.Char(string='Swift Code', copy=False)
    bank_ad_code = fields.Char(string='Bank AD Code', copy=False)
    ifsc_code = fields.Char(string='IFSC Code', copy=False)
    branch_sol_id = fields.Char(string='Branch Sol ID', copy=False)
    branch = fields.Char(string='Branch', copy=False)
