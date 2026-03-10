# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def _create_payments(self):
        """Block payment for vendor bills whose PO has no approved "Payment approval with bill" request."""
        moves = self.line_ids.mapped('move_id')
        vendor_bills = moves.filtered(lambda m: m.move_type == 'in_invoice' and m.state == 'posted')
        for move in vendor_bills:
            purchase_lines = move.line_ids.mapped('purchase_line_id').filtered(lambda l: l)
            pos = purchase_lines.mapped('order_id').filtered(lambda o: o)
            for po in pos:
                if not po.has_approved_bill_payment_request:
                    raise UserError(
                        _(
                            'Payment for vendor bill %s is not allowed: Purchase Order %s does not have an approved "Payment approval with bill" request. '
                            'Please create a Payment Approval Request (Request Bill Payment Approval) and get it approved first.'
                        )
                        % (move.name, po.name)
                    )
        return super()._create_payments()
