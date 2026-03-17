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

    @api.model_create_multi
    def create(self, vals_list):
        """Set approval_type from PO when not provided; prevent duplicate draft/pending per (PO, approval_type)."""
        for vals in vals_list:
            po_id = vals.get('purchase_order_id')
            approval_type = vals.get('approval_type')
            if po_id:
                po = self.env['purchase.order'].browse(po_id)
                if po.exists():
                    if not approval_type:
                        vals['approval_type'] = 'with_bill' if po.has_vendor_bill else 'without_bill'
                    approval_type = vals.get('approval_type')
                existing = self.search([
                    ('purchase_order_id', '=', po_id),
                    ('state', 'in', ('draft', 'pending_approval', 'approved')),
                    ('approval_type', '=', approval_type),
                ], limit=1)
                if existing:
                    raise ValidationError(
                        _(
                            'A payment approval request of this type already exists for Purchase Order %s (status: %s). '
                            'Each PO can only have one request per approval type.'
                        )
                        % (existing.purchase_order_id.name, dict(existing._fields['state'].selection).get(existing.state, existing.state))
                    )
        return super().create(vals_list)

    @api.constrains('purchase_order_id', 'approval_type', 'state')
    def _check_one_active_request_per_po_per_type(self):
        """Only one non-rejected request per (purchase order, approval_type)."""
        for rec in self:
            if rec.state == 'rejected':
                continue
            other = self.search([
                ('purchase_order_id', '=', rec.purchase_order_id.id),
                ('approval_type', '=', rec.approval_type),
                ('state', '!=', 'rejected'),
                ('id', '!=', rec.id),
            ], limit=1)
            if other:
                raise ValidationError(
                    _(
                        'Only one payment approval request of type "%s" can exist per Purchase Order. '
                        'A request already exists for %s (status: %s). '
                        'If it was rejected, use "Reset to Draft" to resubmit.'
                    )
                    % (
                        dict(rec._fields['approval_type'].selection).get(rec.approval_type, rec.approval_type),
                        rec.purchase_order_id.name,
                        dict(other._fields['state'].selection).get(other.state, other.state),
                    )
                )

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
                ('approval_type', '=', rec.approval_type),
            ], order='sequence, approver_type')
            if not configs:
                raise UserError(
                    _(
                        'No approvers configured for "%s". '
                        'Please set up Vendor Payment Approval Settings (Purchase → Configuration) for this approval type.'
                    )
                    % dict(rec._fields['approval_type'].selection).get(rec.approval_type, rec.approval_type)
                )
            approver_types = configs.mapped('approver_type')
            if set(approver_types) != {'approver1', 'approver2'}:
                raise UserError(
                    _(
                        'For "%s" both Approver 1 and Approver 2 must be configured in Vendor Payment Approval Settings. '
                        'Currently missing: %s'
                    )
                    % (
                        dict(rec._fields['approval_type'].selection).get(rec.approval_type, rec.approval_type),
                        ', '.join({'approver1', 'approver2'} - set(approver_types)),
                    )
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
        """Open approve wizard (single or bulk)."""
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
        else:
            self.activity_unlink(['mail.mail_activity_data_todo'])
            self._notify_next_approver()
        return True

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
