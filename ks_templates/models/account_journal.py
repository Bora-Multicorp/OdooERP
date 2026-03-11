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

    # Cash Credit (CC) journal: limit / borrow limit
    is_cash_credit = fields.Boolean(
        string='Is Cash Credit Journal',
        default=False,
        help='Enable for cash credit type journals to set CC/borrow limit.',
    )
    ks_cc_limit = fields.Monetary(
        string='CC / Borrow Limit',
        currency_field='company_currency_id',
        help='Allocated limit for cash credit or borrow limit (in company currency).',
    )
    company_currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        string='Company Currency',
    )

