# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    iec_no = fields.Char(
        string="IEC No",
        help="Import Export Code number (India).",
    )

    ks_sale_procurement_team_user_ids = fields.Many2many(
        comodel_name='res.users',
        relation='ks_sale_order_company_procurement_team_rel',
        column1='company_id',
        column2='user_id',
        string='Procurement Team',
        help='Users who will receive email notifications when a product with '
             'insufficient stock is added to a sales order. '
             'The system will block the addition and notify these users.',
    )

