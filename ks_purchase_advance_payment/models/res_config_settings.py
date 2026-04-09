# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    banking_team_user_ids = fields.Many2many(
        'res.users',
        'ks_banking_team_config_users_rel',
        'config_id',
        'user_id',
        string='Banking Team Users',
        help='Users who will be notified by email when a payment approval request is approved.',
    )

    def get_values(self):
        res = super().get_values()
        param = self.env['ir.config_parameter'].sudo().get_param(
            'ks_purchase_advance_payment.banking_team_user_ids', ''
        )
        user_ids = [int(i) for i in param.split(',') if i.strip().isdigit()]
        res['banking_team_user_ids'] = [(6, 0, user_ids)]
        return res

    def set_values(self):
        super().set_values()
        user_ids = self.banking_team_user_ids.ids
        self.env['ir.config_parameter'].sudo().set_param(
            'ks_purchase_advance_payment.banking_team_user_ids',
            ','.join(str(uid) for uid in user_ids),
        )
