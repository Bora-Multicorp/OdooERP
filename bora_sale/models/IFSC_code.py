# models/res_partner_bank.py
from odoo import models, fields, api

class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    ifsc_code = fields.Char(string='IFSC Code', size=11, help='Indian Financial System Code (11 alphanumeric characters)')
    branch = fields.Char(string='Branch', help='Name of the branch')
    sol_number = fields.Char(string="SOL Number", help="Bank branch Service Outlet Number")
    ad_code = fields.Char(string="AD Code", help="Authorized Dealer Code for export/import")
    

    show_IFSC_code = fields.Boolean(
        compute='_compute_show_ifsc_code',
        store=True
    )


    @api.depends('partner_id.country_id')
    def _compute_show_ifsc_code(self):
        for bank_account in self:
            if bank_account.partner_id and bank_account.partner_id.country_id and bank_account.partner_id.country_id.code == 'IN':
                bank_account.show_IFSC_code = True
            else:
                bank_account.show_IFSC_code = False


