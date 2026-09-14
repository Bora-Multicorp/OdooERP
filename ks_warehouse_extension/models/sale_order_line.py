# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_cash_handling_rate_deviation = fields.Boolean(
        string='Cash Handling Rate Changed',
        default=False,
    )
