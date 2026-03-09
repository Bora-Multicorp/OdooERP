# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class VendorPaymentApprovalRequest(models.Model):
    _name = 'vendor.payment.approval.request'
    _description = 'Vendor Payment Approval Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        required=True,
        ondelete='cascade',
        index=True,
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

    def action_submit(self):
        """Submit for approval: create lines from config and set state to pending."""
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft requests can be submitted.'))
            configs = self.env['vendor.payment.approval.config'].search([
                ('active', '=', True),
            ], order='sequence, approver_type')
            if not configs:
                raise UserError(
                    _('No approvers configured. Please set up Vendor Payment Approval Settings (Purchase → Configuration).')
                )
            lines = [(5, 0, 0)]
            for cfg in configs:
                lines.append((0, 0, {
                    'user_id': cfg.user_id.id,
                    'approver_type': cfg.approver_type,
                    'sequence': cfg.sequence,
                }))
            rec.write({
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
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=next_line.user_id.id,
                note=_('Vendor payment approval requested for PO %s.') % self.purchase_order_id.name,
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
