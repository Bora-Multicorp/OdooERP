# -*- coding: utf-8 -*-
from odoo import api, fields, models

class AccountPayment(models.Model):
    """Extend account.payment to add exchanged amount calculation based on exchange rate"""
    _inherit = 'account.payment'

    is_exchange = fields.Boolean(string='Apply Manual Currency', help='allows users to manually apply an exchange rate')
    rate = fields.Float(string='Exchange Rate', help='1 [foreign currency] = X [company currency]. Example: 1 USD = 100 INR → enter 100', default=0.0)
    exchanged_amount = fields.Monetary(
        string='Exchanged Currency Amount',
        compute='_compute_exchanged_amount',
        store=True,
        currency_field='company_currency_id',
        help='Calculated as: Total Amount × Exchange Rate. '
             'Example: If total is 200 USD and rate is 50 (1 USD = 50 INR), then exchanged currency amount = 200 × 50 = 10,000 INR',
    )

    @api.onchange('company_currency_id', 'currency_id')
    def _onchange_different_currency(self):
        """ When the Currency is changed back to company currency, the boolean field is disabled """
        for order in self:
            if order.company_currency_id == order.currency_id:
                if order.is_exchange:
                    order.is_exchange = False

    @api.onchange('is_exchange')
    def _onchange_is_exchange(self):
        if not self.is_exchange:
            self._fetch_rate_from_currency()

    @api.onchange('currency_id', 'date')
    def _onchange_currency_id_fetch_rate(self):
        self._fetch_rate_from_currency()

    def _fetch_rate_from_currency(self):
        if self.currency_id and self.company_currency_id and self.currency_id != self.company_currency_id:
            try:
                self.rate = self.env['res.currency']._get_conversion_rate(
                    from_currency=self.currency_id,
                    to_currency=self.company_currency_id,
                    company=self.company_id,
                    date=self.date or fields.Date.context_today(self),
                )
            except Exception:
                self.rate = 0.0
        else:
            self.rate = 0.0

    @api.depends('amount', 'rate', 'currency_id', 'company_currency_id')
    def _compute_exchanged_amount(self):
        """Calculate exchanged amount based on total amount and exchange rate

        Formula: exchanged_amount = amount_total / rate
        Example: If Payment total is 200 USD and rate is 50, then exchanged_amount = 200 / 50 = 4
        """
        for record in self:
            exchanged_amount = 0.0
            if (record.currency_id != record.company_currency_id and
                    record.rate and record.rate > 0 and
                    record.amount):
                # Calculate: document_total / exchange_rate
                # Example: 200 USD / 50 = 4
                exchanged_amount = record.amount * record.rate
            record.exchanged_amount = exchanged_amount

