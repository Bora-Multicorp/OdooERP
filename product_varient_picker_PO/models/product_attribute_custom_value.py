# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductAttributeCustomValue(models.Model):
    _inherit = 'product.attribute.custom.value'

    purchase_order_line_id = fields.Many2one(
        comodel_name='purchase.order.line',
        string="Purchase Order Line",
        ondelete='cascade',
        index=True
    )
