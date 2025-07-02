# -*- coding: utf-8 -*-

from odoo import api, fields, models

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Customer",
        required=True, change_default=True, index=True,
        tracking=1,
        check_company=True)