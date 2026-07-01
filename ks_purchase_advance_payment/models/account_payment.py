# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # Link to Purchase Order for advance payments
    ks_purchase_order_id = fields.Many2one(
        comodel_name='purchase.order',
        string='Purchase Order',
        copy=False,
        help='The Purchase Order this advance payment is linked to',
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        payments = super().create(vals_list)
        payments._invalidate_purchase_order_advance_amount()
        payments._ks_sync_payment_tracker()
        return payments

    def _ks_get_linked_purchase_order(self):
        """Return the purchase order linked to this payment, if any.
        Checks direct link (advance) first, then falls back to bill → PO.
        """
        self.ensure_one()
        if self.ks_purchase_order_id:
            return self.ks_purchase_order_id
        # Bill payment: find PO via reconciled vendor bills
        for move in self.reconciled_bill_ids:
            if move.purchase_id:
                return move.purchase_id
        return self.env['purchase.order']

    def _ks_sync_payment_tracker(self):
        """Create or update ks.payment.tracker records for each payment linked to a PO."""
        if 'ks.payment.tracker' not in self.env:
            return

        adv_product_tmpl = self.env.ref(
            'ks_purchase_advance_payment.product_template_advance_deduction',
            raise_if_not_found=False,
        )
        adv_variant_ids = set(
            adv_product_tmpl.sudo().product_variant_ids.ids
        ) if adv_product_tmpl else set()

        for payment in self:
            po = payment._ks_get_linked_purchase_order()
            if not po:
                continue

            # If tracker records already exist for this payment, just link them
            existing = self.env['ks.payment.tracker'].search([
                ('ks_account_payment_id', '=', payment.id),
            ])
            if existing:
                continue

            # If tracker records exist from approval request, link them
            approval_request = self.env['vendor.payment.approval.request'].search([
                ('purchase_order_id', '=', po.id),
                ('state', '=', 'approved'),
            ], limit=1)
            if approval_request:
                unlinked = self.env['ks.payment.tracker'].search([
                    ('payment_approval_request_id', '=', approval_request.id),
                    ('ks_account_payment_id', '=', False),
                ])
                if unlinked:
                    unlinked.write({'ks_account_payment_id': payment.id})
                    continue

            # No existing tracker records — create them for all product lines
            product_lines = po.order_line.filtered(
                lambda l: not l.display_type
                          and l.product_id
                          and l.product_id.id not in adv_variant_ids
            )
            if not product_lines:
                continue

            vals_list = []
            for line in product_lines:
                vals_list.append({
                    'company_id': po.company_id.id,
                    'purchase_order_id': po.id,
                    'purchase_line_id': line.id,
                    'ks_account_payment_id': payment.id,
                    'user_id': po.user_id.id or False,
                    'product_id': line.product_id.id,
                    'product_qty': line.product_qty,
                    'price_unit': line.price_unit,
                    'price_subtotal': line.price_subtotal,
                    'purchase_date': po.date_order.date() if po.date_order else False,
                    'ks_destination': getattr(po, 'ks_destination', False) or False,
                    'ks_despatched_through': getattr(po, 'ks_despatched_through', False) or False,
                    'ks_remarks': getattr(po, 'ks_remarks', False) or False,
                    'ks_invoice': getattr(po, 'ks_invoice', False) or False,
                    'ks_e_invoices': getattr(po, 'ks_e_invoices', False) or False,
                    'ks_e_way_bill': getattr(po, 'ks_e_way_bill', False) or False,
                    'ks_imei_serial_no': getattr(po, 'ks_imei_serial_no', False) or False,
                    'ks_docket': getattr(po, 'ks_docket', False) or False,
                    'ks_ewaybill_no': getattr(po, 'ks_ewaybill_no', False) or False,
                    'ks_docket_no': getattr(po, 'ks_docket_no', False) or False,
                    'ks_vehicle_no': getattr(po, 'ks_vehicle_no', False) or False,
                    'ks_transporter': getattr(po, 'ks_transporter', False) or False,
                    'approved': True,
                })
            if vals_list:
                self.env['ks.payment.tracker'].create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if any(
            f in vals
            for f in ('ks_purchase_order_id', 'amount', 'state', 'currency_id')
        ):
            self._invalidate_purchase_order_advance_amount()
        return res

    def unlink(self):
        for payment in self:
            if payment.ks_purchase_order_id:
                raise UserError(_(
                    'You cannot delete payment "%s" because it is linked to Purchase Order %s.'
                ) % (payment.name, payment.ks_purchase_order_id.name))
        orders = self.mapped('ks_purchase_order_id').filtered('id')
        res = super().unlink()
        if orders:
            orders._compute_ks_advance_payment_amount()
        return res

    def _invalidate_purchase_order_advance_amount(self):
        """Recompute advance payment amount on linked purchase orders."""
        orders = self.mapped('ks_purchase_order_id').filtered('id')
        if orders:
            orders._compute_ks_advance_payment_amount()
