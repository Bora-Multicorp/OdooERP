# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # Link to Sale Order for advance payments
    ks_sale_order_id = fields.Many2one(
        comodel_name='sale.order',
        string='Sale Order',
        copy=False,
        help='The Sale Order this advance payment is linked to',
        index=True,
    )

