from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    ks_ecom_order_id = fields.Char(
        string="E-com Order ID",
        copy=False,
        index=True,
        help="E-commerce Order ID linked to this delivery.",
    )
