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

class SaleOrder(models.Model):
    """This class extends the base 'sale.order' model to introduce a
    new field, 'is_exchange',which allows users to manually apply an exchange
    rate for a transaction. When this option is enabled,users can specify the
    exchange rate through the 'rate' field."""
    _inherit = 'sale.order'

    company_currency_id = fields.Many2one(
        string='Company Currency',
        related='company_id.currency_id', readonly=True,help='Store the Company Currency'
    )

    is_exchange = fields.Boolean(string='Apply Manual Currency',
                                 help='Enable the boolean field to display '
                                      'rate field')
    rate = fields.Float(string='Exchange Rate', help='1 [foreign currency] = X [company currency]. Example: 1 USD = 100 INR → enter 100', default=0.0)

    @api.constrains('company_currency_id', 'currency_id')
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

    @api.onchange('currency_id', 'date_order')
    def _onchange_currency_id_fetch_rate(self):
        self._fetch_rate_from_currency()

    def _fetch_rate_from_currency(self):
        if self.currency_id and self.company_currency_id and self.currency_id != self.company_currency_id:
            try:
                self.rate = self.env['res.currency']._get_conversion_rate(
                    from_currency=self.currency_id,
                    to_currency=self.company_currency_id,
                    company=self.company_id,
                    date=self.date_order or fields.Date.context_today(self),
                )
            except Exception:
                self.rate = 0.0
        else:
            self.rate = 0.0
