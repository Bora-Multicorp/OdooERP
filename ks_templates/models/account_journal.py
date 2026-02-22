# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    # New fields for bank information
    bank_ad_code = fields.Char(
        string='Bank AD Code',
        help='Bank AD Code (e.g., 6390532-6200019)'
    )
    
    ifsc_code = fields.Char(
        string='IFSC Code',
        help='IFSC Code (e.g., HDFC0000104)'
    )
    
    branch_sol_id = fields.Char(
        string='Branch Sol ID',
        help='Branch Sol ID (e.g., 001 - Sberbank, New Delhi or 1144)'
    )

    branch = fields.Char(
        string='Branch',
        help='Branch (e.g., 675 / KHALED BIN WALEED STREET)'
    )

