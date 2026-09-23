# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Farook Al Ameen (odoo@cybrosys.info)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
from odoo import api, fields, models


class AccountMove(models.Model):
    """This class extends the base 'purchase.order' model to introduce a new
     field, 'is_exchange',which allows users to manually apply an exchange
     rate for a transaction. When this option is enabled,users can specify
    the exchange rate through the 'rate' field."""
    _inherit = 'account.move'

    is_exchange = fields.Boolean(string="Apply Manual Exchange", compute="_compute_is_exchange",
                                 inverse="_inverse_is_exchange",
                                 store=True, help='Check this box if you want to manually '
                                                  'apply an exchange rate for this '
                                                  'transaction.')

    rate = fields.Float(string="Exchange Rate", compute="_compute_rate", inverse="_inverse_rate", store=True,
                        help='specify the rate')

    sale_order_id = fields.Many2one('sale.order', string="Sale Order", compute="_compute_sale_order",
                                    store=True,help="Linking corresponding Sale Order")
    purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order",
                                        compute="_compute_purchase_order", store=True,help="Linking Purchase Order")

    @api.constrains('company_currency_id', 'currency_id')
    def _onchange_different_currency(self):
        """ When the Currency is changed back to company currency, the boolean field is disabled """
        for move in self:
            if move.company_currency_id == move.currency_id:
                if move.is_exchange:
                    move.is_exchange = False

    @api.depends('line_ids.sale_line_ids.order_id')
    def _compute_sale_order(self):
        """ Compute Function to Update the Corresponding Sale Order """
        for move in self:
            sale_orders = move.line_ids.mapped('sale_line_ids.order_id')
            move.sale_order_id = sale_orders and sale_orders[0] or False

    @api.depends('line_ids.purchase_line_id.order_id')
    def _compute_purchase_order(self):
        """ Compute Function to Update the Corresponding Purchase Order """
        for move in self:
            purchase_orders = move.line_ids.mapped('purchase_line_id.order_id')
            move.purchase_order_id = purchase_orders and purchase_orders[0] or False

    @api.depends('currency_id', 'company_currency_id', 'company_id', 'invoice_date', 'rate', 'is_exchange')
    def _compute_invoice_currency_rate(self):
        """Overriding the Default Compute function to include the Manual Rate Also.

        Odoo's invoice_currency_rate = how many invoice-currency units per 1 company-currency unit.
        Our manual `rate` means: 1 invoice-currency unit = X company-currency units (e.g. 1 USD = 100 INR).
        So invoice_currency_rate = 1 / rate.
        """
        for move in self:
            if move.is_invoice(include_receipts=True):
                if move.currency_id:
                    if move.is_exchange and move.rate:
                        # rate = 100 means 1 USD = 100 INR
                        # invoice_currency_rate = 1/100 = 0.01 (1 INR = 0.01 USD)
                        move.invoice_currency_rate = 1.0 / move.rate
                        continue
                    move.invoice_currency_rate = self.env['res.currency']._get_conversion_rate(
                        from_currency=move.company_currency_id,
                        to_currency=move.currency_id,
                        company=move.company_id,
                        date=move._get_invoice_currency_rate_date(),
                    )
                else:
                    move.invoice_currency_rate = 1

    @api.depends('sale_order_id.is_exchange', 'purchase_order_id.is_exchange')
    def _compute_is_exchange(self):
        """ Compute Function to Update the Exchange Boolean based on Sale Order and Purchase Order"""
        for move in self:
            if move.sale_order_id:
                move.is_exchange = move.sale_order_id.is_exchange
            elif move.purchase_order_id:
                move.is_exchange = move.purchase_order_id.is_exchange
            else:
                # Retain manually toggled/existing value safely
                move.is_exchange = move.is_exchange or False

    def _inverse_is_exchange(self):
        """ Allow manual editing of is_exchange in account.move """
        pass

    @api.depends('sale_order_id.rate', 'purchase_order_id.rate')
    def _compute_rate(self):
        """ Compute The rate based on sale order and purchase order"""
        for move in self:
            if move.sale_order_id:
                move.rate = move.sale_order_id.rate
            elif move.purchase_order_id:
                move.rate = move.purchase_order_id.rate
            else:
                # Retain manually toggled/existing value safely
                move.rate = move.rate or 0.0

    def _inverse_rate(self):
        """ Allow manual editing of rate in account.move """
        pass

    def _compute_tax_totals(self):
        super()._compute_tax_totals()
        for move in self:
            if move.tax_totals and isinstance(move.tax_totals, dict) and 'amount_total_cc' in move.tax_totals:
                tax_totals = dict(move.tax_totals)
                tax_totals.pop('amount_total_cc', None)
                move.tax_totals = tax_totals

