# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payment_approval_request_id = fields.Many2one(
        comodel_name='vendor.payment.approval.request',
        string='Payment Approval Request',
        copy=False,
        help='The Payment Approval Request linked to this payment',
        index=True,
    )
    ks_payment_done_notified = fields.Boolean(
        string='Payment Done Notification Sent',
        default=False,
        copy=False,
        help='Technical field to prevent duplicate activity notifications upon payment completion.',
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

    def write(self, vals):
        res = super().write(vals)
        if vals.get('state') in ('in_process', 'paid'):
            for payment in self:
                if not payment.ks_payment_done_notified:
                    payment._create_payment_done_activities()
        return res

    def action_draft(self):
        res = super().action_draft()
        self.write({'ks_payment_done_notified': False})
        return res

    def action_post(self):
        for payment in self:
            if payment.state == 'pending_approval':
                raise UserError(_('This payment is pending approval and cannot be posted yet.'))
            if payment.state == 'draft' and not payment.ks_payment_approved:
                if self.env.context.get('skip_payment_approval'):
                    continue
                return payment.action_submit_and_open_wizard()
        res = super(AccountPayment, self.with_context(skip_payment_approval=True)).action_post()
        for payment in self:
            if payment.state in ('in_process', 'paid') and not payment.ks_payment_done_notified:
                payment._create_payment_done_activities()
        return res

    def _do_approve(self, reason):
        res = super()._do_approve(reason)
        for payment in self:
            if payment.state in ('in_process', 'paid') and not payment.ks_payment_done_notified:
                payment._create_payment_done_activities()
        return res

    @api.model
    def _get_or_create_processed_activity_type(self):
        """Get or dynamically duplicate/create the 'Processed' activity type from 'To-Do'."""
        processed_type = self.env.ref('bora_purchase_payment.mail_activity_data_processed', raise_if_not_found=False)
        if not processed_type:
            processed_type = self.env['mail.activity.type'].sudo().search([('name', '=', 'Processed')], limit=1)
        if not processed_type:
            todo_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
            vals = {
                'name': 'Processed',
                'icon': todo_type.icon if todo_type else 'fa-check',
                'sequence': (todo_type.sequence + 1) if todo_type else 13,
                'category': todo_type.category if todo_type else 'default',
                'delay_count': 0,
                'delay_unit': todo_type.delay_unit if todo_type else 'days',
                'chaining_type': todo_type.chaining_type if todo_type else 'suggest',
                'active': True,
            }
            processed_type = self.env['mail.activity.type'].sudo().create(vals)
            data_rec = self.env['ir.model.data'].sudo().search([
                ('module', '=', 'bora_purchase_payment'),
                ('name', '=', 'mail_activity_data_processed'),
            ], limit=1)
            if not data_rec:
                self.env['ir.model.data'].sudo().create({
                    'module': 'bora_purchase_payment',
                    'name': 'mail_activity_data_processed',
                    'model': 'mail.activity.type',
                    'res_id': processed_type.id,
                    'noupdate': True,
                })
        return processed_type

    def _create_payment_done_activities(self):
        """Create activities for PO followers and Payment Approval Request followers/approvers
        when payment transitions to 'in_process'."""
        for payment in self:
            if payment.ks_payment_done_notified:
                continue

            po = payment.ks_purchase_order_id
            if not po and payment.payment_approval_request_id:
                po = payment.payment_approval_request_id.purchase_order_id
            if not po and hasattr(payment, '_ks_get_linked_purchase_order'):
                po = payment._ks_get_linked_purchase_order()

            req = payment.payment_approval_request_id
            if not req and po:
                req = self.env['vendor.payment.approval.request'].search([
                    ('purchase_order_id', '=', po.id)
                ], order='id desc', limit=1)

            # If no PO and no Req, nothing to notify
            if not po and not req:
                payment.ks_payment_done_notified = True
                continue

            # Format activity details
            currency_symbol = payment.currency_id.symbol or payment.currency_id.name or ''
            formatted_amount = f"{currency_symbol} {payment.amount:,.2f}".strip()
            po_name = po.name if po else _('N/A')

            req_name = _('N/A')
            if req:
                req_name = f"Request #{req.id}"
                if req.purchase_order_id and req.purchase_order_id.name:
                    req_name += f" ({req.purchase_order_id.name})"
                elif req.display_name:
                    req_name += f" ({req.display_name})"

            payment_name = payment.name or _('Draft Payment')
            vendor_name = payment.partner_id.display_name or (po.partner_id.display_name if po else _('N/A'))
            payment_memo = payment.memo or _('N/A')
            payment_date = str(payment.date or fields.Date.context_today(payment))

            summary = _('Vendor Payment Done: %s') % (po.name if po else payment_name)
            note = _(
                "<p><strong>Vendor Payment has been processed and is now in process.</strong></p>"
                "<ul>"
                "<li><strong>Purchase Order:</strong> %s</li>"
                "<li><strong>Payment Request:</strong> %s</li>"
                "<li><strong>Payment Reference:</strong> %s</li>"
                "<li><strong>Vendor:</strong> %s</li>"
                "<li><strong>Payment Amount:</strong> %s</li>"
                "<li><strong>Memo:</strong> %s</li>"
                "<li><strong>Payment Date:</strong> %s</li>"
                "</ul>"
            ) % (
                po_name,
                req_name,
                payment_name,
                vendor_name,
                formatted_amount,
                payment_memo,
                payment_date,
            )

            processed_type = self._get_or_create_processed_activity_type()
            activity_type_id = processed_type.id if processed_type else False
            act_type_xmlid = 'bora_purchase_payment.mail_activity_data_processed' if processed_type else 'mail.mail_activity_data_todo'

            # 1. Create an activity for all followers of the same Purchase Order
            if po:
                po_users = po.message_follower_ids.mapped('partner_id.user_ids').filtered(
                    lambda u: u.active and not u.share
                )
                if po.user_id and po.user_id.active and not po.user_id.share:
                    po_users |= po.user_id

                for user in po_users:
                    existing = po.activity_ids.filtered(
                        lambda a: a.user_id == user and (payment_name in (a.summary or '') or (a.note and payment_name in a.note))
                    )
                    if not existing:
                        try:
                            po.activity_schedule(
                                act_type_xmlid=act_type_xmlid,
                                activity_type_id=activity_type_id,
                                user_id=user.id,
                                summary=summary,
                                note=note,
                            )
                        except Exception as e:
                            _logger.warning("Failed to schedule payment done activity on PO %s for user %s: %s", po.id, user.id, e)

                try:
                    po.message_post(
                        body=note,
                        subject=summary,
                    )
                except Exception as e:
                    _logger.warning("Failed to post payment done message on PO %s: %s", po.id, e)

            # 2. Create an activity for all followers and approvers of the Payment Approval Request
            if req:
                req_users = req.message_follower_ids.mapped('partner_id.user_ids').filtered(
                    lambda u: u.active and not u.share
                )
                req_users |= req.approval_line_ids.mapped('user_id').filtered(
                    lambda u: u.active and not u.share
                )
                if req.assigned_approver_id and req.assigned_approver_id.active and not req.assigned_approver_id.share:
                    req_users |= req.assigned_approver_id
                if req.request_user_id and req.request_user_id.active and not req.request_user_id.share:
                    req_users |= req.request_user_id
                req_users |= payment.approval_line_ids.mapped('user_id').filtered(
                    lambda u: u.active and not u.share
                )
                if payment.request_user_id and payment.request_user_id.active and not payment.request_user_id.share:
                    req_users |= payment.request_user_id

                for user in req_users:
                    existing = req.activity_ids.filtered(
                        lambda a: a.user_id == user and (payment_name in (a.summary or '') or (a.note and payment_name in a.note))
                    )
                    if not existing:
                        try:
                            req.activity_schedule(
                                act_type_xmlid=act_type_xmlid,
                                activity_type_id=activity_type_id,
                                user_id=user.id,
                                summary=summary,
                                note=note,
                            )
                        except Exception as e:
                            _logger.warning("Failed to schedule payment done activity on Request %s for user %s: %s", req.id, user.id, e)

                try:
                    req.message_post(
                        body=note,
                        subject=summary,
                    )
                except Exception as e:
                    _logger.warning("Failed to post payment done message on Request %s: %s", req.id, e)

            elif payment.approval_line_ids:
                payment_approvers = payment.approval_line_ids.mapped('user_id').filtered(
                    lambda u: u.active and not u.share
                )
                if payment.request_user_id and payment.request_user_id.active and not payment.request_user_id.share:
                    payment_approvers |= payment.request_user_id

                for user in payment_approvers:
                    existing = payment.activity_ids.filtered(
                        lambda a: a.user_id == user and (payment_name in (a.summary or '') or (a.note and payment_name in a.note))
                    )
                    if not existing:
                        try:
                            payment.activity_schedule(
                                act_type_xmlid=act_type_xmlid,
                                activity_type_id=activity_type_id,
                                user_id=user.id,
                                summary=summary,
                                note=note,
                            )
                        except Exception as e:
                            _logger.warning("Failed to schedule payment done activity on payment %s for user %s: %s", payment.id, user.id, e)

            payment.ks_payment_done_notified = True
