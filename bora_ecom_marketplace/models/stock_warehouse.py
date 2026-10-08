# -*- coding: utf-8 -*-
from odoo import fields, models


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    is_ecommerce_warehouse = fields.Boolean(
        string='E-commerce warehouse',
        default=False,
        help="If checked, this warehouse will be defaulted on new RFQs and Purchase Orders.",
    )
