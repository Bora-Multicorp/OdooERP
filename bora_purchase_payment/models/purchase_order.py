# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_view_advance_payments(self):
        """View all payments linked to this Purchase Order"""
        self.ensure_one()
        form_view_id = self.env.ref('account.view_account_payment_form', raise_if_not_found=False)
        action = {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {
                'create': False,
                'default_payment_type': 'outbound',
                'default_partner_type': 'supplier',
                'default_partner_id': self.partner_id.id,
                'default_ks_purchase_order_id': self.id,
                'default_memo': _('Payment for purchase order %s') % (self.name or ''),
            },
        }
        if self.ks_advance_payment_count == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.ks_advance_payment_ids.id
            if form_view_id:
                action['views'] = [(form_view_id.id, 'form')]
        else:
            action['view_mode'] = 'list,form'
            action['domain'] = [('id', 'in', self.ks_advance_payment_ids.ids)]
            list_view_id = self.env.ref('account.view_account_payment_tree', raise_if_not_found=False)
            if list_view_id and form_view_id:
                action['views'] = [(list_view_id.id, 'list'), (form_view_id.id, 'form')]
        return action

    def action_create_advance_payment(self):
        """Open wizard to create payment directly"""
        res = super().action_create_advance_payment()
        res['name'] = _('Create Payment')
        return res
