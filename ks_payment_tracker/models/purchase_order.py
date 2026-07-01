# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_submit_payment_approval(self):
        return self.action_add_for_approval()

    def action_add_for_approval(self):
        """Open the 'Add for Approval' wizard so the user can assign an approver
        before the vendor.payment.approval.request records are created.
        """
        return {
            'name': _('Add for Approval'),
            'type': 'ir.actions.act_window',
            'res_model': 'ks.add.for.approval.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_ids': self.ids,
                'active_model': 'purchase.order',
            },
        }
