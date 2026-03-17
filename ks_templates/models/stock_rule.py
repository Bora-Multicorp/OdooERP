# -*- coding: utf-8 -*-
from odoo import models


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_custom_move_fields(self):
        fields = super()._get_custom_move_fields()
        fields += ['made_in_country_id']
        return fields
