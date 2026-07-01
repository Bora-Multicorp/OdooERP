# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from odoo.exceptions import UserError, ValidationError
from pygments.lexer import default

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

# Default percentage for Dubai cash handling charges (1.2%)
KS_DUBAI_CASH_HANDLING_PERCENT = 1.2


class KSSaleOrder(models.Model):
    _inherit = "sale.order"

    mail_count = fields.Integer("mail count", defualt=0, tracking=True)
    stock_decifient = fields.Boolean("Stock Decifient?", default=False, tracking=True)


    def _ks_get_cash_handling_product(self):
        """Get the Cash handling charges product (for Dubai zone)."""
        template = self.env.ref(
            'ks_warehouse_extension.product_template_cash_handling_charges',
            raise_if_not_found=False
        )
        if not template or not template.product_variant_ids:
            return self.env['product.product']
        return template.product_variant_ids[0]


    def _ks_order_amount_untaxed_without_charge_line(self):
        """Amount untaxed excluding the cash handling charge line (for Dubai)."""
        self.ensure_one()
        product = self._ks_get_cash_handling_product()
        if not product:
            return self.amount_untaxed
        lines = self.order_line.filtered(
            lambda l: l.product_id != product and not l.display_type
        )
        return sum(lines.mapped('price_subtotal'))


    def _ks_recalc_dubai_cash_handling_line(self):
        """If Dubai zone and the Cash handling charge line already exists, recalculate its amount.
        Does NOT auto-create the line — user must add it manually via 'Add a product'."""
        for order in self:
            if getattr(order, 'ks_zone', None) != 'dubai':
                continue
            product = order._ks_get_cash_handling_product()
            if not product:
                continue
            charge_line = order.order_line.filtered(lambda l: l.product_id == product)
            if not charge_line:
                continue  # Not added yet — do nothing
            base_amount = order._ks_order_amount_untaxed_without_charge_line()
            charge_amount = base_amount * (KS_DUBAI_CASH_HANDLING_PERCENT / 100.0)
            if abs((charge_line.price_subtotal or 0) - charge_amount) > 0.01:
                charge_line.with_context(ks_dubai_charge_update=True).write({
                    'product_uom_qty': 1,
                    'price_unit': charge_amount,
                })


    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get('ks_dubai_charge_update'):
            return res
        if 'order_line' in vals or vals.get('ks_zone'):
            for order in self:
                order._ks_recalc_dubai_cash_handling_line()
        return res


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
