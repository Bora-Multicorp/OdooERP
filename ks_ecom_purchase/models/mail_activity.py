# -*- coding: utf-8 -*-

from odoo import api, models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def init(self):
        super().init()
        # Update existing purchase order activities so their Document Name (res_name)
        # displays in the format "PO_NAME - VENDOR_NAME"
        self.env.cr.execute("""
            UPDATE mail_activity ma
            SET res_name = CASE
                WHEN rp.name IS NOT NULL AND rp.name != '' THEN po.name || ' - ' || rp.name
                ELSE po.name
            END
            FROM purchase_order po
            LEFT JOIN res_partner rp ON po.partner_id = rp.id
            WHERE (ma.res_model = 'purchase.order' OR ma.res_model_id = (SELECT id FROM ir_model WHERE model = 'purchase.order'))
              AND ma.res_id = po.id;
        """)

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
