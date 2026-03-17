# -*- coding: utf-8 -*-

from odoo import models, fields


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    # Packing list fields for each move line
    ks_no_kin_of_pkg = fields.Char(string="No. and Kind of Pkg")
    ks_remark = fields.Text(string="Remark")

