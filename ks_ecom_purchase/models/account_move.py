# -*- coding: utf-8 -*-

from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        res = super().action_post()
        self._ks_update_warehouse_tracking_invoice_no()
        return res

    def _ks_update_warehouse_tracking_invoice_no(self):
        """When a vendor bill is posted, set invoice_no on linked PO warehouse tracking."""
        for move in self:
            if move.move_type != "in_invoice" or move.state != "posted":
                continue
            order_ids = move.invoice_line_ids.mapped("purchase_line_id.order_id").filtered(
                lambda o: o.ks_ecom_imported and o.ks_ecom_order_id
            )
            if not order_ids:
                continue
            ecom_order_ids = order_ids.mapped("ks_ecom_order_id")
            self.env["ks.po.warehouse.tracking"].search([
                ("order_id", "in", ecom_order_ids),
            ]).write({"invoice_no": move.name or ""})
