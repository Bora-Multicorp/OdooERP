# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class VendorPaymentApprovalRequest(models.Model):
    _inherit = 'vendor.payment.approval.request'

    payment_id = fields.Many2one(
        comodel_name='account.payment',
        string='Vendor Payment',
        copy=False,
        help='The Vendor Payment created from this approval request.',
    )
    payment_ids = fields.One2many(
        comodel_name='account.payment',
        inverse_name='payment_approval_request_id',
        string='Vendor Payments',
    )
    payment_count = fields.Integer(
        string='Payment Count',
        compute='_compute_payment_count',
    )

    @api.depends('payment_ids', 'payment_id')
    def _compute_payment_count(self):
        for req in self:
            payments = req.payment_ids | req.payment_id
            req.payment_count = len(payments)

    def _create_vendor_payment(self):
        """Create draft account.payment for this approved request."""
        self.ensure_one()
        if self.payment_id:
            return self.payment_id

        po = self.purchase_order_id
        partner = self.partner_id or (po and po.partner_id)
        accounting_partner = self.env['res.partner']._find_accounting_partner(partner)
        company = self.company_id or (po and po.company_id) or self.env.company
        destination_account = accounting_partner.with_company(
            company
        ).property_account_payable_id

        currency = self.currency_id or (po and po.currency_id) or company.currency_id

        # Search for a bank/cash journal with sudo to bypass multi-company restrictions
        journal = False
        if currency:
            journal = self.env['account.journal'].sudo().search([
                ('company_id', '=', company.id),
                ('type', '=', 'bank'),
                ('currency_id', '=', currency.id),
            ], limit=1)
        if not journal:
            journal = self.env['account.journal'].sudo().search([
                ('company_id', '=', company.id),
                ('type', 'in', ('bank', 'cash')),
            ], limit=1)
        if not journal and self.env.company.id != company.id:
            journal = self.env['account.journal'].sudo().search([
                ('company_id', '=', self.env.company.id),
                ('type', 'in', ('bank', 'cash')),
            ], limit=1)
        if not journal:
            journal = self.env['account.journal'].sudo().search([
                ('type', 'in', ('bank', 'cash')),
            ], limit=1)
        if not journal:
            journal = self.env['account.journal'].sudo().search([
                ('company_id', '=', company.id),
            ], limit=1) or self.env['account.journal'].sudo().search([], limit=1)

        if not journal:
            raise UserError(_(
                "No bank or cash journal found for company '%s'. "
                "Please configure a payment journal in Accounting → Configuration → Journals."
            ) % company.name)

        memo = _('Payment for purchase order %s') % (po.name or '') if po else ''

        payment_vals = {
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': accounting_partner.id or (partner.id if partner else False),
            'amount': self.amount_for_approval,
            'currency_id': currency.id,
            'company_id': company.id,
            'date': fields.Date.context_today(self),
            'ks_purchase_order_id': po.id if po else False,
            'payment_approval_request_id': self.id,
            'ks_payment_approved': False,
            'request_user_id': self.request_user_id.id if self.request_user_id else self.env.user.id,
            'memo': memo,
            'journal_id': journal.id,
        }
        outbound_methods = journal.outbound_payment_method_line_ids
        if outbound_methods:
            payment_vals['payment_method_line_id'] = outbound_methods[0].id
        if destination_account:
            payment_vals['destination_account_id'] = destination_account.id
        if self.approval_type in ('regular', 'part_payment', 'with_bill') and self.vendor_bill_id:
            payment_vals['ref'] = self.vendor_bill_id.name or (po.name if po else '')
            payment_vals['invoice_ids'] = [(6, 0, [self.vendor_bill_id.id])]

        payment = self.env['account.payment'].create(payment_vals)
        self.payment_id = payment.id

        self.message_post(
            body=_(
                'Vendor payment <a href="#" data-oe-model="account.payment" data-oe-id="%d">%s</a> created from approval request.'
            ) % (payment.id, payment.name or _('Draft Payment')),
        )
        return payment

    def _do_approve(self, reason):
        res = super()._do_approve(reason)
        for req in self:
            if req.state == 'approved' and not req.payment_id:
                req._create_vendor_payment()
        return res

    def write(self, vals):
        res = super().write(vals)
        if vals.get('state') == 'approved':
            for req in self:
                if not req.payment_id:
                    req._create_vendor_payment()
        return res

    def action_view_vendor_payment(self):
        """Open the linked vendor payment(s)."""
        self.ensure_one()
        payments = self.payment_ids | self.payment_id
        if not payments:
            raise UserError(_('No payment has been created for this request yet.'))
        form_view_id = self.env.ref('account.view_account_payment_form', raise_if_not_found=False)
        if len(payments) == 1:
            action = {
                'name': _('Vendor Payment'),
                'type': 'ir.actions.act_window',
                'res_model': 'account.payment',
                'view_mode': 'form',
                'res_id': payments.id,
                'target': 'current',
            }
            if form_view_id:
                action['views'] = [(form_view_id.id, 'form')]
            return action
        return {
            'name': _('Vendor Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('id', 'in', payments.ids)],
            'context': {'default_payment_approval_request_id': self.id},
            'target': 'current',
        }
