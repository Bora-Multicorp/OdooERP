# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    debit_amount = fields.Monetary(
        string='Debit',
        compute='_compute_debit_credit_amounts',
        currency_field='currency_id',
        readonly=True,
        help="Shows positive amount entered on the bank statement line."
    )
    credit_amount = fields.Monetary(
        string='Credit',
        compute='_compute_debit_credit_amounts',
        currency_field='currency_id',
        readonly=True,
        help="Shows negative amount entered on the bank statement line as a positive credit value."
    )

    @api.depends('amount')
    def _compute_debit_credit_amounts(self):
        for line in self:
            if line.amount > 0:
                line.debit_amount = line.amount
                line.credit_amount = 0.0
            elif line.amount < 0:
                line.debit_amount = 0.0
                line.credit_amount = abs(line.amount)
            else:
                line.debit_amount = 0.0
                line.credit_amount = 0.0
