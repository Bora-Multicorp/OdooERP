# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # ===== Vendor Payment Approval =====
    payment_approval_request_ids = fields.One2many(
        'vendor.payment.approval.request',
        'purchase_order_id',
        string='Payment Approval Requests',
        copy=False,
    )
    has_approved_advance_payment_request = fields.Boolean(
        string='Has Approved Advance Payment Request',
        compute='_compute_has_approved_payment_requests',
        store=True,
        help='True if at least one approved request of type "without bill" exists (allows advance payment).',
    )
    has_approved_bill_payment_request = fields.Boolean(
        string='Has Approved Bill Payment Request',
        compute='_compute_has_approved_payment_requests',
        store=True,
        help='True if at least one approved request of type "with bill" exists (allows payment from vendor bill).',
    )
    has_any_advance_request = fields.Boolean(
        string='Has Any Advance Payment Request',
        compute='_compute_has_approved_payment_requests',
        store=True,
        help='True if any non-rejected advance payment request (draft/pending/approved) exists for this PO.',
    )
    has_any_bill_request = fields.Boolean(
        string='Has Any Bill Payment Request',
        compute='_compute_has_approved_payment_requests',
        store=True,
        help='True if any non-rejected bill payment request (draft/pending/approved) exists for this PO.',
    )
    payment_approval_request_count = fields.Integer(
        string='Payment Approval Count',
        compute='_compute_payment_approval_request_count',
    )
    has_vendor_bill = fields.Boolean(
        string='Has Vendor Bill',
        compute='_compute_has_vendor_bill',
        store=True,
        help='True if at least one posted vendor bill exists for this PO.',
    )

    @api.depends('invoice_ids', 'invoice_ids.state')
    def _compute_has_vendor_bill(self):
        for order in self:
            order.has_vendor_bill = bool(
                order.invoice_ids.filtered(lambda inv: inv.state == 'posted')
            )

    @api.depends('payment_approval_request_ids', 'payment_approval_request_ids.state', 'payment_approval_request_ids.approval_type')
    def _compute_has_approved_payment_requests(self):
        for order in self:
            requests = order.payment_approval_request_ids
            order.has_approved_advance_payment_request = any(
                r.state == 'approved' and r.approval_type == 'without_bill' for r in requests
            )
            order.has_approved_bill_payment_request = any(
                r.state == 'approved' and r.approval_type == 'with_bill' for r in requests
            )
            order.has_any_advance_request = any(
                r.state != 'rejected' and r.approval_type == 'without_bill' for r in requests
            )
            order.has_any_bill_request = any(
                r.state != 'rejected' and r.approval_type == 'with_bill' for r in requests
            )

    @api.depends('payment_approval_request_ids')
    def _compute_payment_approval_request_count(self):
        for order in self:
            order.payment_approval_request_count = len(order.payment_approval_request_ids)

    def action_create_payment_approval_request(self):
        """Create a new payment approval request. Type is set from PO (with bill if vendor bill exists, else without bill)."""
        self.ensure_one()
        if self.state not in ('purchase', 'done'):
            raise UserError(_('Only confirmed or locked Purchase Orders can request payment approval.'))
        approval_type = 'with_bill' if self.has_vendor_bill else 'without_bill'
        request = self.env['vendor.payment.approval.request'].create({
            'purchase_order_id': self.id,
            'approval_type': approval_type,
        })
        return {
            'name': _('Payment Approval Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'vendor.payment.approval.request',
            'view_mode': 'form',
            'res_id': request.id,
            'target': 'current',
        }

    def action_bulk_request_payment(self):
        """Bulk: create payment approval requests for selected confirmed POs.
        Approval type is set per PO: 'with_bill' if a posted vendor bill exists, else 'without_bill'.
        """
        orders = self.filtered(lambda o: o.state in ('purchase', 'done'))
        if not orders:
            raise UserError(_('No confirmed or locked Purchase Orders selected.'))
        created = self.env['vendor.payment.approval.request']
        for order in orders:
            approval_type = 'with_bill' if order.has_vendor_bill else 'without_bill'
            req = self.env['vendor.payment.approval.request'].create({
                'purchase_order_id': order.id,
                'approval_type': approval_type,
            })
            created |= req
        if len(created) == 1:
            return {
                'name': _('Payment Approval Request'),
                'type': 'ir.actions.act_window',
                'res_model': 'vendor.payment.approval.request',
                'view_mode': 'form',
                'res_id': created.id,
                'target': 'current',
            }
        return {
            'name': _('Payment Approval Requests'),
            'type': 'ir.actions.act_window',
            'res_model': 'vendor.payment.approval.request',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created.ids)],
            'target': 'current',
        }

    def action_view_payment_approval_requests(self):
        """View payment approval requests for this PO."""
        self.ensure_one()
        return {
            'name': _('Payment Approval Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'vendor.payment.approval.request',
            'view_mode': 'list,form',
            'domain': [('purchase_order_id', '=', self.id)],
            'context': {'default_purchase_order_id': self.id},
        }

    # ===== Advance Payment Fields =====
    ks_advance_payment_ids = fields.One2many(
        comodel_name='account.payment',
        inverse_name='ks_purchase_order_id',
        string='Advance Payments',
        copy=False,
        help='Advance payments linked to this Purchase Order',
    )
    ks_advance_payment_count = fields.Integer(
        string='Advance Payment Count',
        compute='_compute_ks_advance_payment_count',
    )
    ks_advance_payment_amount = fields.Monetary(
        string='Advance Payment Amount',
        compute='_compute_ks_advance_payment_amount',
        currency_field='currency_id',
        store=True,
        help='Total amount of advance payments made for this Purchase Order',
    )
    ks_advance_payment_balance = fields.Monetary(
        string='Balance Due',
        compute='_compute_ks_advance_payment_amount',
        currency_field='currency_id',
        store=True,
        help='Remaining balance after advance payments',
    )
    total_invoice_payment_made = fields.Monetary(
        string="Total Bill Payment Made",
        compute="_compute_total_payment_made",
        store=True,
        currency_field='currency_id',
    )

    @api.depends(
        'invoice_ids',
        'invoice_ids.state',
        'invoice_ids.reconciled_payment_ids',
        'invoice_ids.reconciled_payment_ids.state',
        'invoice_ids.reconciled_payment_ids.amount',
    )
    def _compute_total_payment_made(self):
        for order in self:
            total = 0.0
            invoices = order.invoice_ids.filtered(lambda inv: inv.state == 'posted')
            for inv in invoices:
                valid_payments = inv.reconciled_payment_ids.filtered(
                    lambda p: p.state == 'paid'
                )
                invoice_payment_sum = sum(valid_payments.mapped('amount'))
                if inv.move_type == 'in_invoice':
                    total += invoice_payment_sum
                elif inv.move_type == 'in_refund':
                    total -= invoice_payment_sum
            order.total_invoice_payment_made = total

    @api.depends('ks_advance_payment_ids')
    def _compute_ks_advance_payment_count(self):
        for order in self:
            order.ks_advance_payment_count = len(order.ks_advance_payment_ids)

    @api.depends(
        'ks_advance_payment_ids',
        'ks_advance_payment_ids.amount',
        'ks_advance_payment_ids.state',
        'ks_advance_payment_ids.currency_id',
        'amount_total',
    )
    def _compute_ks_advance_payment_amount(self):
        for order in self:
            payments = self.env['account.payment'].search([
                ('ks_purchase_order_id', '=', order.id),
                ('state', '=', 'paid'),
            ])
            total_advance = sum(payments.mapped('amount')) if payments else 0.0
            order.ks_advance_payment_amount = total_advance
            order.ks_advance_payment_balance = (order.amount_total or 0.0) - total_advance

    def action_create_advance_payment(self):
        """Open wizard to create advance payment directly"""
        self.ensure_one()
        return {
            'name': _('Create Advance Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.advance.payment',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_purchase_order_id': self.id,
            },
        }

    def copy(self, default=None):
        """Exclude advance payment deduction lines from the duplicated PO (handled in copy_data)."""
        return super().copy(default)

    def copy_data(self, default=None):
        """Exclude advance payment deduction lines so they are not duplicated to the new PO."""
        vals_list = super().copy_data(default=default)
        adv_product_tmpl = self.env.ref(
            'ks_purchase_advance_payment.product_template_advance_deduction',
            raise_if_not_found=False,
        )
        adv_variant_ids = set()
        if adv_product_tmpl:
            adv_variant_ids = set(adv_product_tmpl.sudo().product_variant_ids.ids)
        for vals in vals_list:
            order_line = vals.get('order_line') or []
            if not order_line or not adv_variant_ids:
                continue
            new_lines = []
            for cmd in order_line:
                if cmd[0] != 0 or len(cmd) < 3:
                    new_lines.append(cmd)
                    continue
                line_vals = cmd[2]
                product_id = line_vals.get('product_id')
                if isinstance(product_id, (list, tuple)):
                    product_id = product_id[0] if product_id else None
                if product_id and product_id in adv_variant_ids:
                    continue
                new_lines.append(cmd)
            vals['order_line'] = new_lines
        return vals_list

    def action_view_advance_payments(self):
        """View all advance payments linked to this Purchase Order"""
        self.ensure_one()
        action = {
            'name': _('Advance Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }
        if self.ks_advance_payment_count == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.ks_advance_payment_ids.id
        else:
            action['view_mode'] = 'list,form'
            action['domain'] = [('id', 'in', self.ks_advance_payment_ids.ids)]
        return action
