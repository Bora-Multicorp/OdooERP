# -*- coding: utf-8 -*-
from odoo import _
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import groupby


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    # Disable automatic company checks to allow company-independent accounts
    _check_company_auto = False

    # Remove default company_id to allow company-independent accounts
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        # No default - allows company-independent accounts
    )

    # Make currency_id computed instead of related since company_id can be False
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        compute='_compute_currency_id',
        store=False,
    )

    @api.depends('company_id')
    def _compute_currency_id(self):
        """Compute currency from company, or use current company's currency if no company set"""
        for account in self:
            if account.company_id:
                account.currency_id = account.company_id.currency_id
            else:
                # For company-independent accounts, use the current company's currency
                # This allows the account to work across all companies
                account.currency_id = self.env.company.currency_id

    @api.constrains('company_id')
    def _check_company_consistency(self):
        """
        Override to allow company-independent accounts (company_id = False).
        Only validate consistency when a company is explicitly set.
        """
        # Allow company-independent accounts (company_id = False)
        accounts_with_company = self.filtered(lambda a: a.company_id)
        if not accounts_with_company:
            return

        # Use the parent's constraint logic only for accounts with a company
        for company, accounts in groupby(accounts_with_company, lambda account: account.company_id):
            if company:
                account_ids = [account.id for account in accounts]
                # Check if there are analytic lines with different company
                if self.env['account.analytic.line'].sudo().search_count([
                    ('auto_account_id', 'in', account_ids),
                    '!', ('company_id', 'child_of', company.id),
                ], limit=1):
                    raise UserError(_("You can't set a different company on your analytic account since there are some analytic items linked to it."))

