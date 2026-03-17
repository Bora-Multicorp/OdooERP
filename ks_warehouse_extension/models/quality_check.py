# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from odoo.exceptions import UserError, ValidationError
from pygments.lexer import default

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class QualityCheck(models.Model):
    _inherit = "quality.check"

    qc_sku_mismatch = fields.Boolean(default=True, tracking=True)
    qc_qty_mismatch = fields.Boolean(default=True, tracking=True)
    qc_color_mismatch = fields.Boolean(default=True, tracking=True)
    qc_damage = fields.Boolean(default=True, tracking=True)
    qc_wrong_device_type = fields.Boolean(default=True, tracking=True)
    qc_notes = fields.Text(tracking=True)

    def perform_qc(self):
        mismatches = []

        picking = self.picking_id  # quality check belongs to a picking
        # move = self.move_id        # safer: QC usually applies to ONE move line

        if picking:  # If QC is tied to a specific move line
            for move in self.picking_id.move_ids_without_package:
                # SKU mismatch
                if move.product_id.default_code != move.purchase_line_id.product_id.default_code if move.purchase_line_id else False:
                    self.qc_sku_mismatch = False
                    mismatches.append("SKU mismatch")
                elif move.product_id.default_code != move.sale_line_id.product_id.default_code if move.sale_line_id else False:
                    self.qc_sku_mismatch = False
                    mismatches.append("SKU mismatch")

                # Quantity mismatch
                if move.purchase_line_id and move.purchase_line_id.product_qty != move.quantity:
                    self.qc_qty_mismatch = False
                    mismatches.append("Quantity mismatch")
                elif move.sale_line_id and move.sale_line_id.product_uom_qty != move.quantity:
                    self.qc_qty_mismatch = False
                    mismatches.append("Quantity mismatch")

        # Damage
        if self.qc_damage:
            self.qc_damage = False
            mismatches.append("Box Damaged")

        # No mismatches message
        if not mismatches:
            mismatches.append("No mismatches found")

        return mismatches

    def send_qc_notification(self, mismatch_details):
        template = self.env.ref('ks_warehouse_extension.qc_notification_dynamic_template', raise_if_not_found=False)

        users = self.env['res.users'].sudo().search([('share', '=', False)])
        partners = users.mapped('partner_id').ids

        # chatter notification
        self.message_post(
            body=f"QC Results:<br/>{'<br/>'.join(mismatch_details)}",
            partner_ids=partners
        )

        # email
        if template:
            template.with_context(
                mismatch_details=mismatch_details,
                qc=self
            ).send_mail(self.id, force_send=True)

    def do_pass(self):
        res = super().do_pass()

        mismatches = self.perform_qc()
        self.send_qc_notification(mismatches)

        return res

    def do_fail(self):
        res = super().do_fail()

        mismatches = self.perform_qc()
        self.send_qc_notification(mismatches)

        return res
