# -*- coding: utf-8 -*-
from odoo import api, models


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    @api.model_create_multi
    def create(self, vals_list):
        warehouses = super().create(vals_list)
        for wh in warehouses:
            if not wh.partner_id or wh.partner_id == wh.company_id.partner_id:
                partner = self.env['res.partner'].sudo().create({
                    'name': wh.name,
                    'company_id': wh.company_id.id,
                    'type': 'contact',
                })
                wh.sudo().write({'partner_id': partner.id})
        return warehouses
