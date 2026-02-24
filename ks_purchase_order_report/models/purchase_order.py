# -*- coding: utf-8 -*-

from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    fob = fields.Float(
        string='FOB (Exchange Rate)',
        digits=(16, 6),
        help="FOB exchange rate for the purchase order"
    )
    
    advance_payment = fields.Monetary(
        string='Advance Payment',
        currency_field='currency_id',
        help="Advance payment amount for the purchase order"
    )
    
    conversion_rate = fields.Float(
        string='Conversion Rate',
        digits=(16, 6),
        default=1.0,
        help="Conversion rate for converting payment to INR"
    )
