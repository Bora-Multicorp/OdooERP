# -*- coding: utf-8 -*-
from odoo import api, models


class PurchaseOrder(models.Model):
    """Extend purchase.order to auto-assign the current user to a partner's
    purchase_executive_ids when a new order is created.

    The visibility filter itself lives in ResPartner._search (see
    res_partner.py) and is activated by the context flag
    'filter_by_purchase_executive' that the view sets on the partner_id
    field.
    """

    _inherit = 'purchase.order'

    @api.model_create_multi
    def create(self, vals_list):
        """After creating purchase orders, ensure the current user is in
        the partner's purchase_executive_ids.
        """
        records = super().create(vals_list)

        if self.env.su:
            return records

        for order in records:
            partner = order.partner_id
            if not partner:
                continue
            if self.env.uid not in partner.purchase_executive_ids.ids:
                partner.sudo().write({
                    'purchase_executive_ids': [(4, self.env.uid)],
                })

        return records
