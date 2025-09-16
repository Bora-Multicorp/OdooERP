from odoo import models, fields

SALE_ORDER_STATE = [
    ('draft', "Quotation"),
    ("confirmation_pending", "Confirmation Pending"),
    ('cancellation_pending', 'Cancellation Pending'),
    ('unlock_pending', 'Unlock Pending'),
    ('sent', "Quotation Sent"),
    ('sale', "Proforma Invoice"),
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