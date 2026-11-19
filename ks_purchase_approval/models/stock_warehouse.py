# -*- coding: utf-8 -*-
from odoo import api, models


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    @api.model_create_multi
    def create(self, vals_list):
        warehouses = super().create(vals_list)
        purchase_group = self.env.ref('purchase.group_purchase_user', raise_if_not_found=False)
        purchase_users = purchase_group.users if purchase_group else self.env['res.users']
        exec_user_ids = list(set(purchase_users.ids + ([self.env.uid] if self.env.uid else [])))

        for wh in warehouses:
            if not wh.partner_id or wh.partner_id == wh.company_id.partner_id:
                partner_vals = {
                    'name': wh.name,
                    'company_id': wh.company_id.id,
                    'type': 'contact',
                }
                if hasattr(self.env['res.partner'], 'purchase_executive_ids') and exec_user_ids:
                    partner_vals['purchase_executive_ids'] = [(6, 0, exec_user_ids)]

                partner = self.env['res.partner'].sudo().create(partner_vals)
                wh.sudo().write({'partner_id': partner.id})
            elif hasattr(wh.partner_id, 'purchase_executive_ids') and exec_user_ids:
                missing_uids = [uid for uid in exec_user_ids if uid not in wh.partner_id.purchase_executive_ids.ids]
                if missing_uids:
                    wh.partner_id.sudo().write({
                        'purchase_executive_ids': [(4, uid) for uid in missing_uids]
                    })
        return warehouses
