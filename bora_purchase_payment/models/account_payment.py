# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payment_approval_request_id = fields.Many2one(
        comodel_name='vendor.payment.approval.request',
        string='Payment Approval Request',
        copy=False,
        help='The Payment Approval Request linked to this payment',
        index=True,
    )

    def action_view_payment_approval_request(self):
        """Open the linked payment approval request."""
        self.ensure_one()
        if not self.payment_approval_request_id:
            raise UserError(_('No payment approval request is linked to this payment.'))
        action = {
            'name': _('Payment Approval Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'vendor.payment.approval.request',
            'view_mode': 'form',
            'res_id': self.payment_approval_request_id.id,
            'target': 'current',
        }
        form_view_id = self.env.ref(
            'ks_purchase_advance_payment.view_vendor_payment_approval_request_form',
            raise_if_not_found=False,
        )
        if form_view_id:
            action['views'] = [(form_view_id.id, 'form')]
        return action

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        po_id = res.get('ks_purchase_order_id') or self.env.context.get('default_ks_purchase_order_id')
        req_id = res.get('payment_approval_request_id') or self.env.context.get('default_payment_approval_request_id')
        if not po_id and req_id:
            req = self.env['vendor.payment.approval.request'].browse(req_id)
            if req.exists() and req.purchase_order_id:
                po_id = req.purchase_order_id.id
                res['ks_purchase_order_id'] = po_id
        if po_id:
            po = self.env['purchase.order'].browse(po_id)
            if po.exists() and (not res.get('memo') or 'advance' in (res.get('memo') or '').lower()):
                res['memo'] = _('Payment for purchase order %s') % (po.name or '')
        if 'journal_id' in fields_list and not res.get('journal_id'):
            company_id = res.get('company_id') or self.env.company.id
            journal = self.env['account.journal'].sudo().search([
                ('company_id', '=', company_id),
                ('type', 'in', ('bank', 'cash')),
            ], limit=1)
            if not journal:
                journal = self.env['account.journal'].sudo().search([
                    ('type', 'in', ('bank', 'cash')),
                ], limit=1)
            if journal:
                res['journal_id'] = journal.id
        return res

    @api.onchange('payment_approval_request_id')
    def _onchange_payment_approval_request_id(self):
        if self.payment_approval_request_id:
            req = self.payment_approval_request_id
            if req.purchase_order_id:
                self.ks_purchase_order_id = req.purchase_order_id.id
                if not self.memo or 'payment' in (self.memo or '').lower():
                    self.memo = _('Payment for purchase order %s') % (req.purchase_order_id.name or '')
            if req.partner_id:
                self.partner_id = req.partner_id.id
            if req.amount_for_approval:
                self.amount = req.amount_for_approval
            if req.currency_id:
                self.currency_id = req.currency_id.id
            self.payment_type = 'outbound'
            self.partner_type = 'supplier'
            if req.state == 'approved':
                self.ks_payment_approved = True

    @api.onchange('ks_purchase_order_id')
    def _onchange_ks_purchase_order_id(self):
        if self.ks_purchase_order_id:
            po = self.ks_purchase_order_id
            if not self.partner_id and po.partner_id:
                self.partner_id = po.partner_id.id
            if not self.currency_id and po.currency_id:
                self.currency_id = po.currency_id.id
            if not self.memo or 'payment' in (self.memo or '').lower():
                self.memo = _('Payment for purchase order %s') % (po.name or '')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            req_id = vals.get('payment_approval_request_id')
            if req_id and not vals.get('ks_payment_approved'):
                req = self.env['vendor.payment.approval.request'].browse(req_id)
                if req.exists() and req.state == 'approved':
                    vals['ks_payment_approved'] = True
            po_id = vals.get('ks_purchase_order_id')
            if req_id and not po_id:
                req = self.env['vendor.payment.approval.request'].browse(req_id)
                if req.exists() and req.purchase_order_id:
                    po_id = req.purchase_order_id.id
                    vals['ks_purchase_order_id'] = po_id
            if po_id and (not vals.get('memo') or 'advance' in (vals.get('memo') or '').lower()):
                po = self.env['purchase.order'].browse(po_id)
                if po.exists():
                    vals['memo'] = _('Payment for purchase order %s') % (po.name or '')
            if not vals.get('journal_id'):
                company_id = vals.get('company_id') or self.env.company.id
                journal = self.env['account.journal'].sudo().search([
                    ('company_id', '=', company_id),
                    ('type', 'in', ('bank', 'cash')),
                ], limit=1)
                if not journal:
                    journal = self.env['account.journal'].sudo().search([
                        ('type', 'in', ('bank', 'cash')),
                    ], limit=1) or self.env['account.journal'].sudo().search([], limit=1)
                if journal:
                    vals['journal_id'] = journal.id
                    if not vals.get('payment_method_line_id'):
                        outbound = journal.outbound_payment_method_line_ids
                        if outbound:
                            vals['payment_method_line_id'] = outbound[0].id
        return super().create(vals_list)

    def action_post(self):
        for payment in self:
            if payment.state == 'draft' and not payment.ks_payment_approved:
                if payment.payment_approval_request_id and payment.payment_approval_request_id.state == 'approved':
                    payment.ks_payment_approved = True
                    continue
                po = payment.ks_purchase_order_id or (payment.payment_approval_request_id and payment.payment_approval_request_id.purchase_order_id)
                if po:
                    has_req = self.env['vendor.payment.approval.request'].search([
                        ('purchase_order_id', '=', po.id),
                        ('state', '=', 'approved'),
                    ], limit=1)
                    if has_req:
                        payment.ks_payment_approved = True
                        continue
        return super().action_post()
