# -*- coding: utf-8 -*-

from odoo import models, fields


class StockMove(models.Model):
    _inherit = 'stock.move'

    # Line-wise manual entries for Delivery Packing List
    x_dimensions = fields.Char(
        string="Dimensions (L*B*H)",
        help="Enter dimensions manually e.g. 10*20*30",
    )
    x_package_info = fields.Char(
        string="No. & Kind of Packages",
        help="Enter e.g. 10 BOXES (1-10)",
    )
    x_line_remark = fields.Char(
        string="Remark",
    )
    made_in_country_id = fields.Many2one(
        comodel_name='res.country',
        string='Made In',
        help='Country of origin (e.g. Made in India). Propagated from Sale Order Line or Purchase Order Line.',
    )
