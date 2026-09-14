# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from odoo.exceptions import UserError, ValidationError
from pygments.lexer import default

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

class KSSaleOrder(models.Model):
    _inherit = "sale.order"

    mail_count = fields.Integer("mail count", defualt=0, tracking=True)
    stock_decifient = fields.Boolean("Stock Decifient?", default=False, tracking=True)


    def mail_to_3pl(self):
        template = self.env.ref('ks_warehouse_extension.sale_order_3pl_notification_template', raise_if_not_found=False)

        users = self.env['res.users'].sudo().search([('share', '=', False)])
        partners = users.mapped('partner_id').ids

        # chatter notification
        self.message_post(
            body=f"Sale Order Stock:<br/>{'<br/>'.join(' ')}",
            partner_ids=partners
        )

        # email
        if template:
            self.mail_count = self.mail_count + 1
            template.with_context(
                qc=self
            ).send_mail(self.id, force_send=True)
