from odoo import models, fields

class IncoTermsField(models.Model):
    _inherit = 'account.move'

    contract_date = fields.Datetime(string='Contract Date')
    contract_number = fields.Char(string='Contract No.')
    incoterm_description = fields.Text(string="Incoterm Description")
