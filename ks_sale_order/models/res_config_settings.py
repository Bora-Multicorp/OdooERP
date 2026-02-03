# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ks_sale_procurement_team_user_ids = fields.Many2many(
        related='company_id.ks_sale_procurement_team_user_ids',
        readonly=False,
        string='Procurement Team',
        help='Users who will receive email notifications when a product with '
             'insufficient stock is added to a sales order. '
             'The system will block the addition and notify these users.',
    )
