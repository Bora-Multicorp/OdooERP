# -*- coding: utf-8 -*-

from odoo import models, _


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def action_open_landing_cost_report(self):
        """Open Net Landing Cost report (PU-003) in fullscreen."""
        self.ensure_one()
        ctx = dict(
            self.env.context,
            active_model="purchase.order",
            active_id=self.id,
            active_ids=self.ids,
        )
        report = self.env["purchase.landing.cost.report"].with_context(ctx).create({
            "purchase_order_id": self.id,
        })
        return {
            "name": _("Net Landing Cost - %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "purchase.landing.cost.report",
            "res_id": report.id,
            "view_mode": "form",
            "view_id": self.env.ref("purchase_landing_cost.view_purchase_landing_cost_report_form").id,
            "target": "fullscreen",
            "context": ctx,
        }
