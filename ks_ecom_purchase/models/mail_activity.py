# -*- coding: utf-8 -*-

from odoo import api, models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    @api.depends("res_model", "res_id")
    def _compute_res_name(self):
        super()._compute_res_name()
        for activity in self:
            res_model = activity.res_model or (activity.res_model_id and activity.res_model_id.model)
            if res_model == "purchase.order" and activity.res_id:
                order = self.env["purchase.order"].browse(activity.res_id)
                if order.exists():
                    if order.partner_id and order.partner_id.name:
                        activity.res_name = f"{order.name} - {order.partner_id.name}"
                    else:
                        activity.res_name = order.name
