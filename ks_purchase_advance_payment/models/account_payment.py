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

    state = fields.Selection(
        selection_add=[
            ('pending_approval', 'Pending Approval'),
            ('rejected', 'Rejected'),
        ],
        ondelete={
            'pending_approval': 'set default',
            'rejected': 'set default',
        },
    )

    approval_line_ids = fields.One2many(
        'vendor.payment.approval.line',
        'payment_id',
        string='Approval Lines',
        copy=False,
    )
    ks_payment_approved = fields.Boolean(
        string='Payment Approved',
        default=False,
        copy=False,
        tracking=True,
    )
    request_user_id = fields.Many2one(
        'res.users',
        string='Requested By',
        default=lambda self: self.env.user,
        readonly=True,
        copy=False,
    )
    request_date = fields.Datetime(string='Request Date', default=fields.Datetime.now, readonly=True, copy=False)
    approve_reason = fields.Text(string='Approval Reason', readonly=True, copy=False)
    reject_reason = fields.Text(string='Rejection Reason', readonly=True, copy=False)
    reject_user_id = fields.Many2one('res.users', string='Rejected By', readonly=True, copy=False)
    reject_date = fields.Datetime(string='Rejection Date', readonly=True, copy=False)

    ks_can_approve = fields.Boolean(
        compute='_compute_ks_can_approve',
        help='True only for the current user if it is their turn to approve.',
    )
    ks_is_requester = fields.Boolean(
        compute='_compute_ks_is_requester',
        help='True if the current user is the one who requested this approval.',
    )

    @api.depends('request_user_id')
    @api.depends_context('uid')
    def _compute_ks_is_requester(self):
        for rec in self:
            rec.ks_is_requester = rec.request_user_id == self.env.user

    @api.depends('state', 'approval_line_ids.state', 'approval_line_ids.user_id',
                 'approval_line_ids.approver_type')
    @api.depends_context('uid')
    def _compute_ks_can_approve(self):
        current_user = self.env.user
        for rec in self:
            if rec.state != 'pending_approval':
                rec.ks_can_approve = False
                continue
            my_line = rec.approval_line_ids.filtered(
                lambda l: l.user_id == current_user and l.state == 'pending'
            )[:1]
            if not my_line:
                rec.ks_can_approve = False
                continue
            if my_line.approver_type == 'approver2':
                approver1_done = rec.approval_line_ids.filtered(
                    lambda l: l.approver_type == 'approver1' and l.state == 'approved'
                )
                rec.ks_can_approve = bool(approver1_done)
            else:
                rec.ks_can_approve = True

    def action_submit_and_open_wizard(self):
        """Open the submit wizard so the user picks Approver 1 and Approver 2 before submitting."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft payments can be submitted for approval.'))
        if self.amount <= 0:
            raise UserError(_('Payment amount should be greater than 0.'))
        return {
            'name': _('Send for Approval'),
            'type': 'ir.actions.act_window',
            'res_model': 'vendor.payment.approval.submit.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'default_payment_id': self.id,
            },
        }

    def action_update_approvals(self):
        """Open the Update Approvals wizard. Only the requester can call this."""
        self.ensure_one()
        if self.state != 'pending_approval':
            raise UserError(_('Update Approvals is only available for pending payments.'))
        if self.request_user_id != self.env.user:
            raise UserError(_('Only the user who requested this approval can update the approvers.'))
        return {
            'name': _('Update Approvers'),
            'type': 'ir.actions.act_window',
            'res_model': 'vendor.payment.approval.update.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_payment_id': self.id},
        }

    def action_approve_wizard(self):
        """Open approve wizard. Only the current approver-in-turn may proceed."""
        for rec in self:
            if not rec.ks_can_approve:
                raise UserError(
                    _('You are not the current approver for this payment or it is not your turn yet.')
                )
        return {
            'name': _('Approve Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'vendor.payment.approval.approve.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_payment_ids': [(6, 0, self.ids)],
                'active_ids': self.ids,
            },
        }

    def action_reject_wizard(self):
        """Open reject wizard (single or bulk)."""
        return {
            'name': _('Reject Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'vendor.payment.approval.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_payment_ids': [(6, 0, self.ids)],
                'active_ids': self.ids,
            },
        }

    def _notify_next_approver(self):
        """Assign activity to the first pending approver."""
        self.ensure_one()
        next_line = self.approval_line_ids.filtered(lambda l: l.state == 'pending').sorted('sequence')[:1]
        if next_line and next_line.user_id:
            display_ref = self.name or (self.ks_purchase_order_id and self.ks_purchase_order_id.name) or _('Draft Payment')
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=next_line.user_id.id,
                note=_('Payment approval requested for %s.') % display_ref,
                summary=_('Payment Approval: %s') % display_ref,
            )

    def _do_approve(self, reason):
        """Approve this payment (called from wizard). Current user must be next approver."""
        self.ensure_one()
        if self.state != 'pending_approval':
            raise UserError(_('Only pending payments can be approved.'))
        current_user = self.env.user
        my_line = self.approval_line_ids.filtered(
            lambda l: l.user_id == current_user and l.state == 'pending'
        )[:1]
        if not my_line:
            raise UserError(
                _('You are not the next approver for this payment, or it has already been processed.')
            )
        if my_line.approver_type == 'approver2':
            approver1_done = self.approval_line_ids.filtered(
                lambda l: l.approver_type == 'approver1' and l.state == 'approved'
            )
            if not approver1_done:
                raise UserError(_('Approver 1 must approve before Approver 2 can approve.'))
        my_line.write({
            'state': 'approved',
            'remark': reason or '',
            'action_date': fields.Datetime.now(),
        })
        next_pending = self.approval_line_ids.filtered(lambda l: l.state == 'pending').sorted('sequence')[:1]
        if not next_pending:
            self.activity_unlink(['mail.mail_activity_data_todo'])
            self.write({
                'ks_payment_approved': True,
                'approve_reason': reason,
                'state': 'draft',
            })
            return super().action_post()
        else:
            self.activity_unlink(['mail.mail_activity_data_todo'])
            self._notify_next_approver()
        return True

    def _do_reject(self, reason):
        """Reject this payment (called from wizard)."""
        self.ensure_one()
        if self.state != 'pending_approval':
            raise UserError(_('Only pending payments can be rejected.'))
        current_user = self.env.user
        my_line = self.approval_line_ids.filtered(
            lambda l: l.user_id == current_user and l.state == 'pending'
        )[:1]
        if not my_line:
            raise UserError(_('You are not an approver for this payment, or it has already been processed.'))
        my_line.write({
            'state': 'rejected',
            'remark': reason or '',
            'action_date': fields.Datetime.now(),
        })
        self.approval_line_ids.filtered(lambda l: l.state == 'pending').write({
            'state': 'cancelled',
            'remark': _('Payment rejected by another approver'),
        })
        self.write({
            'state': 'rejected',
            'reject_reason': reason or '',
            'reject_user_id': current_user.id,
            'reject_date': fields.Datetime.now(),
        })
        self.activity_unlink(['mail.mail_activity_data_todo'])
        return True

    def action_reset_to_draft(self):
        for rec in self:
            if rec.state not in ('pending_approval', 'rejected'):
                raise UserError(_('Only pending or rejected payments can be reset to draft.'))
        self.write({
            'state': 'draft',
            'ks_payment_approved': False,
            'approval_line_ids': [(5, 0, 0)],
            'approve_reason': False,
            'reject_reason': False,
            'reject_user_id': False,
            'reject_date': False,
        })
        self.activity_unlink(['mail.mail_activity_data_todo'])
        return True

    def action_post(self):
        for payment in self:
            if payment.state == 'pending_approval':
                raise UserError(_('This payment is pending approval and cannot be posted yet.'))
            if payment.state == 'draft' and not payment.ks_payment_approved:
                po = payment._ks_get_linked_purchase_order()
                if po:
                    has_req = self.env['vendor.payment.approval.request'].search([
                        ('purchase_order_id', '=', po.id),
                        ('state', '=', 'approved'),
                    ], limit=1)
                    if has_req:
                        payment.ks_payment_approved = True
                        continue
                if self.env.context.get('skip_payment_approval'):
                    continue
                return payment.action_submit_and_open_wizard()
        return super().action_post()

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
