# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    ks_can_register_vendor_payment = fields.Boolean(
        string='Can Register Vendor Payment',
        compute='_compute_ks_can_register_vendor_payment',
        help='True if this vendor bill can show the Pay button (all linked POs have approved "with bill" payment request).',
    )

    @api.depends('move_type', 'state', 'line_ids.purchase_line_id.order_id', 'line_ids.purchase_line_id.order_id.has_approved_bill_payment_request')
    def _compute_ks_can_register_vendor_payment(self):
        for move in self:
            if move.move_type != 'in_invoice' or move.state != 'posted':
                move.ks_can_register_vendor_payment = True
                continue
            purchase_lines = move.line_ids.mapped('purchase_line_id').filtered(lambda l: l)
            pos = purchase_lines.mapped('order_id').filtered(lambda o: o)
            if not pos:
                move.ks_can_register_vendor_payment = True
            else:
                move.ks_can_register_vendor_payment = all(po.has_approved_bill_payment_request for po in pos)
