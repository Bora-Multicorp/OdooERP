# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_submit_payment_approval(self):
        """Create payment tracker records for selected POs (one record per order line).
        When user selects multiple POs and clicks "Submit for Payment Approval", one tracker
        record is created per product line across all selected POs.
        Only POs in state 'purchase' or 'done' are processed.
        """
        invalid = self.filtered(lambda o: o.state not in ('purchase', 'done'))
        if invalid:
            raise UserError(_(
                'Only confirmed or locked Purchase Orders can be submitted for payment approval. '
                'The following are not in a valid state: %s',
                ', '.join(invalid.mapped('name')),
            ))
        Tracker = self.env['ks.payment.tracker']
        vals_list = []
        for order in self:
            lines = order.order_line.filtered(lambda l: not l.display_type and l.product_id)
            if not lines:
                raise UserError(_('No product lines to submit for payment approval on PO %s.', order.name))
            for line in lines:
                vals_list.append({
                    'purchase_order_id': order.id,
                    'purchase_line_id': line.id,
                    'user_id': (order.user_id or order.create_uid).id,
                    'company_id': order.company_id.id,
                    'product_id': line.product_id.id,
                    'product_qty': line.product_qty,
                    'price_unit': line.price_unit,
                    'price_subtotal': line.price_subtotal,
                    'purchase_date': order.date_order.date() if order.date_order else fields.Date.today(),
                })
        if not vals_list:
            raise UserError(_('No order lines to submit for payment approval.'))
        trackers = Tracker.create(vals_list)
        return self._action_view_payment_tracker(trackers)

    def _action_view_payment_tracker(self, trackers):
        """Return window action to open created payment tracker records."""
        action = self.env['ir.actions.act_window']._for_xml_id(
            'ks_payment_tracker.ks_payment_tracker_action'
        )
        if len(trackers) == 1:
            action['res_id'] = trackers.id
            action['view_mode'] = 'form'
        else:
            action['domain'] = [('id', 'in', trackers.ids)]
            action['view_mode'] = 'list,form'
        return action
