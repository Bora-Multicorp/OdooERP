# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PurchaseAdvancePayment(models.TransientModel):
    _inherit = 'purchase.advance.payment'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'purchase_order_id' in res and res['purchase_order_id']:
            order = self.env['purchase.order'].browse(res['purchase_order_id'])
            if 'memo' in fields_list and not res.get('memo'):
                res['memo'] = _('Payment for purchase order %s') % (order.name or '')
        return res

    def action_create_payment(self):
        if not self.memo and self.purchase_order_id:
            self.memo = _('Payment for purchase order %s') % (self.purchase_order_id.name or '')
        res = super().action_create_payment()
        po = self.purchase_order_id
        if po:
            payment = po.ks_advance_payment_ids.sorted('id', reverse=True)[:1]
            if payment and ('advance' in (payment.memo or '').lower()):
                payment.write({'memo': _('Payment for purchase order %s') % (po.name or '')})
        return res
