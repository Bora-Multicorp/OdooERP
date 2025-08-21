
# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import UserError

class QACheckForDelivery(models.Model):
    _inherit = 'stock.picking'

    is_qc_done = fields.Boolean(
        string='QC check status',
        help="A boolean field to track the state of the QC.",
        tracking=True
    )

    def action_toggle_qc_button(self):
        for picking in self:
            picking.is_qc_done = not picking.is_qc_done

            if picking.is_qc_done:
                self._send_notification('QC check done', 'success')
            else:
                self._send_notification('QC revert done', 'warning')


    def _send_notification(self, message, type):
        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'simple_notification',
            {
                'type': type,
                'title': '',
                'message': message,
                'sticky': False,
            },
        )

    def button_validate(self):
        if not self.is_qc_done:
            raise UserError("Please confirm QC status.")
        return super().button_validate()


