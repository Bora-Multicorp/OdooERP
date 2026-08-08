# -*- coding: utf-8 -*-
from odoo import api, fields, models

class PurchaseTDS(models.Model):
    _name = 'purchase.tds'
    _description = 'Purchase TDS'
    _rec_name = 'reference'

    purchase_id = fields.Many2one('purchase.order', required=True, ondelete='cascade')
    date = fields.Date(string='Date', required=True)
    tax_id = fields.Many2one('account.tax', required=True)
    base = fields.Monetary(string="Base Amount")
    amount = fields.Monetary(string="TDS Amount", compute='_compute_amount', store=True)
    currency_id = fields.Many2one(
        related='purchase_id.currency_id',
        store=True,
    )
    reference = fields.Char(string="Reference")

    @api.depends('tax_id', 'base')
    def _compute_amount(self):
        # Recomputes amount according to "base amount" and tax percentage
        for wizard in self:
            tax_amount = 0.0
            if wizard.tax_id:
                tax_amount = wizard._tax_compute_all_helper(wizard.base, wizard.tax_id)
            wizard.amount = tax_amount

    # === Helper methods ====
    @api.model
    def _tax_compute_all_helper(self, base, tax_id):
        # Computes the withholding tax amount provided a base and a tax
        # It is equivalent to: amount = self.base * self.tax_id.amount / 100
        taxes_res = tax_id.compute_all(
            base,
            currency=tax_id.company_id.currency_id,
            quantity=1.0,
            product=False,
            partner=False,
            is_refund=False,
        )
        tax_amount = taxes_res['total_included'] - taxes_res['total_excluded']
        tax_amount = abs(tax_amount)
        return tax_amount
