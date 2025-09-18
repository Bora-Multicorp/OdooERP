from odoo import models, fields

class ResPartnerBank(models.Model):
    _inherit = 'account.incoterms'

    description = fields.Text(string="Description")




class IncoTermsField(models.Model):
    _inherit = 'account.move'

    contract_date = fields.Datetime(string='Contract Date')
    contract_number = fields.Char(string='Contract No.')