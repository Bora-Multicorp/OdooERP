# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def write(self, vals):
        """Block normal users from changing taxes_id on confirmed/locked POs."""
        if 'taxes_id' in vals:
            for line in self:
                if not line.order_id:
                    continue
                if line.order_id.state not in ('purchase', 'pending_approval', 'cancel_pending', 'edit_pending'):
                    continue
                if not line.order_id._has_approval_config():
                    continue
                all_approvers = line.order_id._get_approval_config().get_all_approvers()
                if self.env.user in all_approvers:
                    continue
                edit_approved = (
                    line.order_id.ks_edit_approved and
                    line.order_id.ks_edit_request_user_id == self.env.user
                )
                if not edit_approved:
                    raise UserError(_(
                        "You do not have permission to change taxes on order lines. "
                        "Please use 'Request Edit' to get edit approval first."
                    ))
        return super().write(vals)
