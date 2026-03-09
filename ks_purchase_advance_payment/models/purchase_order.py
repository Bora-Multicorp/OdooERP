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
    has_approved_payment_request = fields.Boolean(
        string='Has Approved Payment Request',
        compute='_compute_has_approved_payment_request',
        store=True,
        help='True if at least one vendor payment approval request is approved for this PO.',
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

    @api.depends('payment_approval_request_ids', 'payment_approval_request_ids.state')
    def _compute_has_approved_payment_request(self):
        for order in self:
            order.has_approved_payment_request = any(
                r.state == 'approved' for r in order.payment_approval_request_ids
            )

    @api.depends('payment_approval_request_ids')
    def _compute_payment_approval_request_count(self):
        for order in self:
            order.payment_approval_request_count = len(order.payment_approval_request_ids)

    def action_create_payment_approval_request(self):
        """Create a new draft payment approval request for this PO (or open existing draft)."""
        self.ensure_one()
        if self.state not in ('purchase', 'done'):
            raise UserError(_('Only confirmed or locked Purchase Orders can request payment approval.'))
        draft = self.payment_approval_request_ids.filtered(lambda r: r.state == 'draft')[:1]
        if draft:
            return {
                'name': _('Payment Approval Request'),
                'type': 'ir.actions.act_window',
                'res_model': 'vendor.payment.approval.request',
                'view_mode': 'form',
                'res_id': draft.id,
                'target': 'current',
            }
        request = self.env['vendor.payment.approval.request'].create({
            'purchase_order_id': self.id,
        })
        return {
            'name': _('Payment Approval Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'vendor.payment.approval.request',
            'view_mode': 'form',
            'res_id': request.id,
            'target': 'current',
        }

    def action_view_payment_approval_requests(self):
        """View payment approval requests for this PO."""
        self.ensure_one()
        return {
            'name': _('Payment Approval Requests'),
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
