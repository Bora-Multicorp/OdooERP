# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class VendorPaymentApprovalRequest(models.Model):
    _name = 'vendor.payment.approval.request'
    _description = 'Vendor Payment Approval Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'purchase_order_id'

    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        required=True,
        ondelete='cascade',
        index=True,
    )
    approval_type = fields.Selection(
        [
            ('without_bill', 'Payment approval without bill for purchase'),
            ('with_bill', 'Payment approval with bill for purchase'),
        ],
        string='Approval Type',
        required=True,
        default='without_bill',
        copy=False,
        help='Set automatically from PO: with bill if vendor bill exists, otherwise without bill.',
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('pending_approval', 'Pending Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True,
        copy=False,
    )
    request_user_id = fields.Many2one(
        'res.users',
        string='Requested By',
        default=lambda self: self.env.user,
        readonly=True,
    )
    request_date = fields.Datetime(string='Request Date', default=fields.Datetime.now, readonly=True)
    approval_line_ids = fields.One2many(
        'vendor.payment.approval.line',
        'request_id',
        string='Approval Lines',
        copy=False,
    )
    approve_reason = fields.Text(string='Approval Reason', readonly=True)
    reject_reason = fields.Text(string='Rejection Reason', readonly=True)
    reject_user_id = fields.Many2one('res.users', string='Rejected By', readonly=True)
    reject_date = fields.Datetime(string='Rejection Date', readonly=True)
    company_id = fields.Many2one(
        'res.company',
        related='purchase_order_id.company_id',
        store=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        related='purchase_order_id.partner_id',
        string='Vendor',
        store=True,
    )
    po_amount_total = fields.Monetary(
        related='purchase_order_id.amount_total',
        string='PO Total',
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        related='purchase_order_id.currency_id',
        string='Currency',
    )
    po_state = fields.Selection(
        related='purchase_order_id.state',
        string='PO Status',
    )
    assigned_approver_id = fields.Many2one(
        'res.users',
        string='Assigned Approver',
        copy=False,
        tracking=True,
        help='The user responsible for approving this request. Only this user can click Approve.',
    )
    amount_for_approval = fields.Monetary(
        string='Amount for Approval',
        currency_field='currency_id',
        tracking=True,
        help='The amount that needs to be paid. Used when creating the vendor bill.',
    )
    vendor_bill_id = fields.Many2one(
        'account.move',
        string='Vendor Bill',
        copy=False,
        readonly=True,
        ondelete='set null',
    )
    rest_after_payment = fields.Boolean(
        string='Rest After Payment',
        default=False,
        help='If checked, supporting documents are not required for approval.',
    )
    ks_can_approve = fields.Boolean(
        compute='_compute_ks_can_approve',
        help='True only for the current user if it is their turn to approve.',
    )
    document_ids = fields.One2many(
        'vendor.payment.approval.document',
        'request_id',
        string='Documents',
        copy=False,
    )

    @api.depends('state', 'approval_line_ids.state', 'approval_line_ids.user_id',
                 'approval_line_ids.approver_type')
    @api.depends_context('uid')
    def _compute_ks_can_approve(self):
        current_user = self.env.user
        for rec in self:
            if rec.state != 'pending_approval':
                rec.ks_can_approve = False
                continue
            # Find current user's pending line
            my_line = rec.approval_line_ids.filtered(
                lambda l: l.user_id == current_user and l.state == 'pending'
            )[:1]
            if not my_line:
                rec.ks_can_approve = False
                continue
            # If approver2, approver1 must have approved first
            if my_line.approver_type == 'approver2':
                approver1_done = rec.approval_line_ids.filtered(
                    lambda l: l.approver_type == 'approver1' and l.state == 'approved'
                )
                rec.ks_can_approve = bool(approver1_done)
            else:
                rec.ks_can_approve = True

    @api.model_create_multi
    def create(self, vals_list):
        """Set approval_type from PO when not provided."""
        for vals in vals_list:
            po_id = vals.get('purchase_order_id')
            if po_id and not vals.get('approval_type'):
                po = self.env['purchase.order'].browse(po_id)
                if po.exists():
                    vals['approval_type'] = 'with_bill' if po.has_vendor_bill else 'without_bill'
        requests = super().create(vals_list)
        requests._create_payment_tracker_records()
        return requests

    @api.constrains('amount_for_approval', 'purchase_order_id', 'state')
    def _check_total_amount_within_po_total(self):
        """Total amount_for_approval across all non-rejected requests must not exceed the original PO total.

        We use the sum of actual product lines (excluding advance deduction lines) as the
        reference total, because po.amount_total decreases each time an advance deduction
        line is added and would produce false positives.
        """
        adv_product_tmpl = self.env.ref(
            'ks_purchase_advance_payment.product_template_advance_deduction',
            raise_if_not_found=False,
        )
        adv_variant_ids = set(
            adv_product_tmpl.sudo().product_variant_ids.ids
        ) if adv_product_tmpl else set()

        for rec in self:
            if rec.state == 'rejected':
                continue
            po = rec.purchase_order_id
            if not po:
                continue

            # Original PO total = product lines only, excluding advance deduction lines
            original_lines = po.order_line.filtered(
                lambda l: not l.display_type
                          and l.product_id
                          and l.product_id.id not in adv_variant_ids
            )
            original_total = sum(original_lines.mapped('price_total'))
            if not original_total:
                continue

            all_active = self.search([
                ('purchase_order_id', '=', po.id),
                ('state', '!=', 'rejected'),
            ])
            total_requested = sum(all_active.mapped('amount_for_approval'))
            if total_requested >= original_total:
                raise ValidationError(
                    _(
                        'Payment approval request cannot be created for Purchase Order %s.\n'
                        'The full PO amount (%s %.2f) has already been requested for approval.\n'
                        'Total already requested: %s %.2f.'
                    ) % (
                        po.name,
                        po.currency_id.symbol, original_total,
                        po.currency_id.symbol, total_requested,
                    )
                )

    def action_submit_and_open_wizard(self):
        """Open the submit wizard so the user picks Approver 1 and Approver 2 before submitting."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft requests can be submitted.'))
        if self.amount_for_approval <= 0:
            raise UserError(_('Amount for Approval should be greater than 0.'))
        return {
            'name': _('Send for Approval'),
            'type': 'ir.actions.act_window',
            'res_model': 'vendor.payment.approval.submit.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'default_request_id': self.id,
            },
        }

    def action_submit(self):
        """Submit for approval: create lines from config and set state to pending."""
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft requests can be submitted.'))
            if rec.approval_type == 'with_bill' and not rec.purchase_order_id.has_vendor_bill:
                raise UserError(
                    _(
                        'Cannot submit "Payment approval with bill" request: Purchase Order %s does not have a posted vendor bill yet. '
                        'Create and validate a vendor bill for this PO first.'
                    )
                    % rec.purchase_order_id.name
                )
            configs = self.env['vendor.payment.approval.config'].search([
                ('active', '=', True),
            ], order='sequence, approver_type')
            if not configs:
                raise UserError(
                    _(
                        'No approvers configured. '
                        'Please set up Vendor Payment Approval Settings (Purchase → Configuration).'
                    )
                )
            approver_types = configs.mapped('approver_type')
            if set(approver_types) != {'approver1', 'approver2'}:
                raise UserError(
                    _(
                        'Both Approver 1 and Approver 2 must be configured in Vendor Payment Approval Settings. '
                        'Currently missing: %s'
                    )
                    % ', '.join({'approver1', 'approver2'} - set(approver_types))
                )
            lines = [(5, 0, 0)]
            for cfg in configs:
                lines.append((0, 0, {
                    'user_id': cfg.user_id.id,
                    'approver_type': cfg.approver_type,
                    'sequence': cfg.sequence,
                }))
            rec.sudo().write({
                'state': 'pending_approval',
                'approval_line_ids': lines,
            })
            rec._notify_next_approver()
        return True

    def _notify_next_approver(self):
        """Assign activity to the first pending approver."""
        self.ensure_one()
        next_line = self.approval_line_ids.filtered(lambda l: l.state == 'pending').sorted('sequence')[:1]
        if next_line and next_line.user_id:
            type_label = dict(self._fields['approval_type'].selection).get(self.approval_type, self.approval_type)
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=next_line.user_id.id,
                note=_('Vendor payment approval (%s) requested for PO %s.') % (type_label, self.purchase_order_id.name),
                summary=_('Vendor Payment Approval: %s') % self.purchase_order_id.name,
            )

    def action_approve_wizard(self):
        """Open approve wizard. Only the current approver-in-turn may proceed."""
        for rec in self:
            if not rec.ks_can_approve:
                raise UserError(
                    _('You are not the current approver for this request or it is not your turn yet.')
                )
            if not rec.rest_after_payment:
                required_types = {'vendor_invoice', 'eway_bill', 'lr_docket', 'imei_sheet'}
                attached = {d.document_type for d in rec.document_ids if d.document_attachment}
                missing = required_types - attached
                if missing:
                    type_labels = dict(
                        self.env['vendor.payment.approval.document']._fields['document_type'].selection
                    )
                    raise UserError(
                        _('The following documents with attachments are required before approving:\n%s')
                        % '\n'.join('• ' + type_labels.get(t, t) for t in sorted(missing))
                    )
        return {
            'name': _('Approve Payment Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'vendor.payment.approval.approve.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_ids': [(6, 0, self.ids)],
                'active_ids': self.ids,
            },
        }

    def action_reject_wizard(self):
        """Open reject wizard (single or bulk)."""
        return {
            'name': _('Reject Payment Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'vendor.payment.approval.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_ids': [(6, 0, self.ids)],
                'active_ids': self.ids,
            },
        }

    def _do_approve(self, reason):
        """Approve this request (called from wizard). Current user must be next approver."""
        self.ensure_one()
        if self.state != 'pending_approval':
            raise UserError(_('Only pending requests can be approved.'))
        current_user = self.env.user
        my_line = self.approval_line_ids.filtered(
            lambda l: l.user_id == current_user and l.state == 'pending'
        )[:1]
        if not my_line:
            raise UserError(
                _('You are not the next approver for this request, or it has already been processed.')
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
            self.write({
                'state': 'approved',
                'approve_reason': reason,
            })
            self.activity_unlink(['mail.mail_activity_data_todo'])
            self._notify_banking_team()
            self._create_payment_tracker_records()
        else:
            self.activity_unlink(['mail.mail_activity_data_todo'])
            self._notify_next_approver()
        return True

    def _create_payment_tracker_records(self):
        """Called on request creation — always create fresh tracker records (approved=False).
        Called again after both approvals — update approved=True on this request's records only.
        """
        if 'ks.payment.tracker' not in self.env:
            return

        for req in self:
            po = req.purchase_order_id
            if not po:
                continue

            fully_approved = req.state == 'approved'

            if fully_approved:
                existing = self.env['ks.payment.tracker'].search([
                    ('payment_approval_request_id', '=', req.id)
                ])
                if existing:
                    existing.write({'approved': True})
                continue

            product_lines = po.order_line.filtered(lambda l: l.product_id)
            if not product_lines:
                continue

            vals_list = []
            for line in product_lines:
                vals_list.append({
                    'company_id': po.company_id.id,
                    'purchase_order_id': po.id,
                    'purchase_line_id': line.id,
                    'payment_approval_request_id': req.id,
                    'user_id': po.user_id.id or False,
                    'product_id': line.product_id.id,
                    'product_qty': line.product_qty,
                    'price_unit': line.price_unit,
                    'price_subtotal': line.price_unit_incl,
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
                    'approved': False,
                })

            self.env['ks.payment.tracker'].create(vals_list)

    def _do_reject(self, reason):
        """Reject this request (called from wizard)."""
        self.ensure_one()
        if self.state != 'pending_approval':
            raise UserError(_('Only pending requests can be rejected.'))
        current_user = self.env.user
        my_line = self.approval_line_ids.filtered(
            lambda l: l.user_id == current_user and l.state == 'pending'
        )[:1]
        if not my_line:
            raise UserError(_('You are not an approver for this request, or it has already been processed.'))
        my_line.write({
            'state': 'rejected',
            'remark': reason or '',
            'action_date': fields.Datetime.now(),
        })
        self.approval_line_ids.filtered(lambda l: l.state == 'pending').write({
            'state': 'cancelled',
            'remark': _('Request rejected by another approver'),
        })
        self.write({
            'state': 'rejected',
            'reject_reason': reason or '',
            'reject_user_id': current_user.id,
            'reject_date': fields.Datetime.now(),
        })
        self.activity_unlink(['mail.mail_activity_data_todo'])
        return True

    def _auto_create_bill(self):
        """Automatically create a draft vendor bill when the request is fully approved.
        Bill lines mirror the PO product lines. The unit prices are scaled proportionally
        so that the bill total equals amount_for_approval.
        The bill is linked back to the originating PO via purchase_id and invoice_origin.
        Skips silently if a bill already exists or amount is not set.
        """
        self.ensure_one()
        if self.vendor_bill_id or not self.amount_for_approval or self.amount_for_approval <= 0:
            return

        po = self.purchase_order_id
        product_lines = po.order_line.filtered(lambda l: not l.display_type and l.product_id)
        if not product_lines:
            return

        po_total = sum(product_lines.mapped('price_subtotal'))
        # Scale factor so that bill total == amount_for_approval
        scale = (self.amount_for_approval / po_total) if po_total else 1.0

        invoice_line_vals = []
        for line in product_lines:
            account = line.product_id.product_tmpl_id.get_product_accounts().get('expense')
            if not account:
                account = self.env['account.account'].search([
                    ('account_type', '=', 'expense'),
                    ('company_ids', 'in', [po.company_id.id]),
                    ('deprecated', '=', False),
                ], limit=1)
            if not account:
                continue
            invoice_line_vals.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.name,
                'quantity': line.product_qty,
                'product_uom_id': line.product_uom.id,
                'price_unit': line.price_unit * scale,
                'account_id': account.id,
                'purchase_line_id': line.id,
                'currency_id': self.currency_id.id,
            }))

        if not invoice_line_vals:
            return

        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_id.id,
            'currency_id': self.currency_id.id,
            'company_id': self.company_id.id,
            'invoice_origin': po.name,
            'purchase_id': po.id,
            'ref': po.name,
            'invoice_line_ids': invoice_line_vals,
        })
        self.vendor_bill_id = bill.id

    def _notify_banking_team(self):
        """Send an email to all Banking Team users configured in Purchase Settings
        when the approval request reaches the 'approved' state.
        """
        self.ensure_one()
        param = self.env['ir.config_parameter'].sudo().get_param(
            'ks_purchase_advance_payment.banking_team_user_ids', ''
        )
        user_ids = [int(i) for i in param.split(',') if i.strip().isdigit()]
        if not user_ids:
            return

        users = self.env['res.users'].sudo().browse(user_ids).exists()
        recipients = users.filtered(lambda u: u.email)
        if not recipients:
            return

        template = self.env.ref(
            'ks_purchase_advance_payment.mail_template_banking_team_notification',
            raise_if_not_found=False,
        )
        if not template:
            return

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for user in recipients:
            template.with_context(base_url=base_url).send_mail(
                self.id,
                email_values={'email_to': user.email, 'email_cc': False},
                force_send=True,
            )

    def action_view_vendor_bill(self):
        """Smart button: open the linked vendor bill."""
        self.ensure_one()
        return {
            'name': _('Vendor Bill'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.vendor_bill_id.id,
        }

    def _cancel_for_po_edit(self, po_name):
        """Cancel this request because the linked PO has been approved for editing.
        Sends an activity to each pending approver so they are aware of the cancellation.
        """
        self.ensure_one()
        pending_approvers = self.approval_line_ids.filtered(
            lambda l: l.state == 'pending'
        ).mapped('user_id')
        for user in pending_approvers:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=user.id,
                summary=_('Payment Request Cancelled: %s') % po_name,
                note=_(
                    'The payment approval request for Purchase Order %s has been cancelled '
                    'because the PO has been approved for editing.'
                ) % po_name,
            )
        self.write({'state': 'cancelled'})
        self.message_post(
            body=_(
                'Payment approval request cancelled: Purchase Order <b>%s</b> '
                'has been approved for editing.'
            ) % po_name,
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

    def action_reset_to_draft(self):
        for rec in self:
            if rec.state not in ('pending_approval', 'rejected'):
                raise UserError(_('Only pending or rejected requests can be reset.'))
        self.write({
            'state': 'draft',
            'approval_line_ids': [(5, 0, 0)],
            'approve_reason': False,
            'reject_reason': False,
            'reject_user_id': False,
            'reject_date': False,
        })
        self.activity_unlink(['mail.mail_activity_data_todo'])
        return True


class VendorPaymentApprovalLine(models.Model):
    _name = 'vendor.payment.approval.line'
    _description = 'Vendor Payment Approval Line'
    _order = 'sequence, id'

    request_id = fields.Many2one(
        'vendor.payment.approval.request',
        string='Request',
        required=True,
        ondelete='cascade',
    )
    user_id = fields.Many2one('res.users', string='Approver', required=True)
    approver_type = fields.Selection(
        [('approver1', 'Approver 1'), ('approver2', 'Approver 2')],
        string='Type',
        required=True,
    )
    sequence = fields.Integer(default=10)
    state = fields.Selection(
        [
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='pending',
        required=True,
    )
    remark = fields.Text(string='Reason')
    action_date = fields.Datetime(string='Date')


class VendorPaymentApprovalDocument(models.Model):
    _name = 'vendor.payment.approval.document'
    _description = 'Payment Approval Request Document'
    _order = 'document_type, id'

    request_id = fields.Many2one(
        'vendor.payment.approval.request',
        string='Payment Request',
        required=True,
        ondelete='cascade',
    )
    document_type = fields.Selection(
        [
            ('vendor_invoice', 'Vendor Invoice'),
            ('eway_bill', 'E-Way Bill'),
            ('lr_docket', 'LR / Docket'),
            ('imei_sheet', 'IMEI Sheet'),
            ('other', 'Other'),
        ],
        string='Document Type',
        required=True,
    )
    document_number = fields.Char(string='Document Number', required=True)
    document_attachment = fields.Binary(string='Attachment', attachment=True, required=True)
    document_filename = fields.Char(string='Filename')
