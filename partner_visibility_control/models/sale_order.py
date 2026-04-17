# -*- coding: utf-8 -*-
from odoo import api, models


class SaleOrder(models.Model):
    """Extend sale.order to auto-assign the current user to a partner's
    salesperson_ids when a new order is created.

    The visibility filter itself lives in ResPartner._search (see
    res_partner.py) and is activated by the context flag
    'filter_by_salesperson' that the view sets on the partner_id field.
    """

    _inherit = 'sale.order'

    @api.model_create_multi
    def create(self, vals_list):
        """After creating sale orders, ensure the current user is in
        the partner's salesperson_ids.

        Uses sudo() for the partner write so that the action succeeds
        regardless of whether the salesperson has direct write access to
        res.partner.  The write is guarded by an ID-check to avoid
        unnecessary DB round-trips.
        """
        records = super().create(vals_list)

        # Skip auto-assignment when running as the technical superuser
        # (e.g. data imports, scheduled actions) to avoid polluting every
        # partner with the admin user account.
        if self.env.su:
            return records

        for order in records:
            partner = order.partner_id
            if not partner:
                continue
            if self.env.uid not in partner.salesperson_ids.ids:
                partner.sudo().write({
                    'salesperson_ids': [(4, self.env.uid)],
                })

        return records
