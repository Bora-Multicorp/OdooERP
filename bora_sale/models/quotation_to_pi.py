from odoo import models, fields


SALE_ORDER_STATE = [
    ('draft', "Proforma Invoice"),
    ('sent', "Proforma Invoice Sent"),
    ('sale', "Sales Order"),
    ('cancel', "Cancelled"),
]


class SaleOrder(models.Model):
    _inherit = 'sale.order' # Inherit the existing 'sale.order' model

    state = fields.Selection(
    selection=SALE_ORDER_STATE,
    string="Status",
    readonly=True, copy=False, index=True,
    tracking=3,
    default='draft')