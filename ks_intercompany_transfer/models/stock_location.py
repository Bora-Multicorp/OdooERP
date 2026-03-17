# -*- coding: utf-8 -*-

from odoo import fields, models


class StockLocation(models.Model):
    _inherit = 'stock.location'

    virtual_locations = fields.Boolean(string="Virtual Locations")
    x_is_virtual = fields.Boolean(
        string="Virtual Location",
        help="When set, this location is considered a virtual destination for "
             "inter-company transfer quantity calculation.",
    )