# -*- coding: utf-8 -*-

from odoo import _, fields, models


class KsPoImportResultWizard(models.TransientModel):
    _name = "ks.po.import.result.wizard"
    _description = "Purchase Order Import Result"

    result_message = fields.Html(string="Import Result", readonly=True)
    created_order_ids = fields.Many2many(
        "purchase.order",
        string="Created Purchase Orders",
        readonly=True,
    )

    def action_view_orders(self):
        self.ensure_one()
        if not self.created_order_ids:
            return {"type": "ir.actions.act_window_close"}
        if len(self.created_order_ids) == 1:
            return {
                "type": "ir.actions.act_window",
                "name": _("Purchase Order"),
                "res_model": "purchase.order",
                "view_mode": "form",
                "res_id": self.created_order_ids.id,
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("Imported Purchase Orders"),
            "res_model": "purchase.order",
            "view_mode": "list,form",
            "domain": [("id", "in", self.created_order_ids.ids)],
            "target": "current",
        }
