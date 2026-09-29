# -*- coding: utf-8 -*-
from odoo import api, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        for company in companies:
            try:
                self.env['account.account'].sudo()._setup_bora_coa_all()
            except Exception:
                pass
        return companies
