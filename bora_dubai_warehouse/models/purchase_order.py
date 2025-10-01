from odoo import models, api, fields
from datetime import date, timedelta

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    backdate_po = fields.Datetime(string="Purchase Order Date")

    # def _send_wh_notification(self):
    #     for order in self:
    #         warehouse = order.picking_type_id.warehouse_id
    #         if warehouse.email:  # Directly using your warehouse email field
    #             template = self.env.ref('bora_dubai_warehouse.email_template_3pl_po_notification')
    #             template.email_to = warehouse.email  # Ensure the right recipient
    #             template.send_mail(order.id, force_send=True)
    #
    # def button_confirm(self):
    #     res = super(PurchaseOrder, self).button_confirm()
    #     self._send_wh_notification()
    #     return res