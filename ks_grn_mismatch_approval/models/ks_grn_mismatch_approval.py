# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class KsGrnMismatchApproval(models.Model):
    _name = 'ks.grn.mismatch.approval'
    _description = 'GRN Mismatch Approval Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    picking_id = fields.Many2one(
        'stock.picking',
        string='Receipt',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True,
    )
    purchase_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True,
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
        tracking=True,
    )
    request_user_id = fields.Many2one(
        'res.users',
        string='Requested By',
        default=lambda self: self.env.user,
        copy=False,
        tracking=True,
    )
    request_date = fields.Datetime(
        string='Request Date',
        default=fields.Datetime.now,
        copy=False,
    )
    mismatch_details = fields.Text(
        string='Mismatch Details',
        help='Description of quantity or product mismatches',
        tracking=True,
    )
    approve_user_id = fields.Many2one(
        'res.users',
        string='Approved By',
        copy=False,
        readonly=True,
        tracking=True,
    )
    approve_date = fields.Datetime(
        string='Approval Date',
        copy=False,
        readonly=True,
    )
    approve_reason = fields.Text(
        string='Approval Reason',
        copy=False,
        readonly=True,
    )
    reject_user_id = fields.Many2one(
        'res.users',
        string='Rejected By',
        copy=False,
        readonly=True,
    )
    reject_date = fields.Datetime(
        string='Rejection Date',
        copy=False,
        readonly=True,
    )
    reject_reason = fields.Text(
        string='Rejection Reason',
        copy=False,
        readonly=True,
    )
    warehouse_notified = fields.Boolean(
        string='Warehouse Notified',
        default=False,
        copy=False,
        help='True after warehouse responsible person has been notified on approval.',
    )

    @api.constrains('picking_id', 'state')
    def _check_one_approved_per_picking(self):
        """Only one approved request per picking to avoid confusion."""
        for rec in self:
            if rec.state != 'approved':
                continue
            other = self.search([
                ('picking_id', '=', rec.picking_id.id),
                ('id', '!=', rec.id),
                ('state', '=', 'approved'),
            ], limit=1)
            if other:
                raise ValidationError(
                    _('Another approval request for this receipt is already approved.')
                )

    def action_send_for_approval(self):
        """Create request and notify PO approvers (Approver 1 and optionally Approver 2)."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft requests can be sent for approval.'))
        po = self.purchase_id
        if not po.ks_approver_1_id:
            raise UserError(
                _('Purchase Order %s has no Approver 1 set. Cannot send GRN mismatch approval request.')
                % po.name
            )
        self.write({'state': 'pending_approval'})
        # Notify Approver 1 (and Approver 2 if two-level)
        partner_ids = [po.ks_approver_1_id.partner_id.id]
        if po.ks_approver_2_id:
            partner_ids.append(po.ks_approver_2_id.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)
        note = _(
            'GRN (Receipt) %s has quantity or product mismatches with Purchase Order %s. '
            'Please review and approve or reject. Details: %s'
        ) % (self.picking_id.name, po.name, self.mismatch_details or _('See receipt and PO.'))
        # One activity for Approver 1
        self.activity_schedule(
            act_type_xmlid='mail.mail_activity_data_todo',
            summary=_('GRN Mismatch Approval: %s') % self.picking_id.name,
            note=note,
            user_id=po.ks_approver_1_id.id,
        )
        # If two-level, create activity for Approver 2 as well (they can approve after PM1 or in parallel depending on your policy)
        if po.ks_approver_2_id and po.ks_approver_2_id.id != po.ks_approver_1_id.id:
            self.activity_schedule(
                act_type_xmlid='mail.mail_activity_data_todo',
                summary=_('GRN Mismatch Approval: %s (Approver 2)') % self.picking_id.name,
                note=note,
                user_id=po.ks_approver_2_id.id,
            )
        self.message_post(
            body=_('GRN mismatch approval request sent to PO approvers: %s.')
            % ', '.join(po.ks_approver_1_id.name + (po.ks_approver_2_id.name if po.ks_approver_2_id else '')),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        return True

    def action_approve(self):
        """Open wizard to approve with reason."""
        self.ensure_one()
        if self.state != 'pending_approval':
            raise UserError(_('Only pending requests can be approved.'))
        return {
            'name': _('Approve GRN Mismatch'),
            'type': 'ir.actions.act_window',
            'res_model': 'ks.grn.mismatch.approve.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_ks_grn_mismatch_approval_id': self.id,
                'default_approve': True,
            },
        }

    def action_reject(self):
        """Open wizard to reject with reason."""
        self.ensure_one()
        if self.state != 'pending_approval':
            raise UserError(_('Only pending requests can be rejected.'))
        return {
            'name': _('Reject GRN Mismatch'),
            'type': 'ir.actions.act_window',
            'res_model': 'ks.grn.mismatch.approve.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_ks_grn_mismatch_approval_id': self.id,
                'default_approve': False,
            },
        }

    def _do_approve(self, reason, user):
        """Set state to approved and notify warehouse responsible."""
        self.ensure_one()
        self.write({
            'state': 'approved',
            'approve_user_id': user.id,
            'approve_date': fields.Datetime.now(),
            'approve_reason': reason,
        })
        # Mark activities as done
        self.env['mail.activity'].search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
        ]).action_done()
        self.message_post(
            body=_('GRN mismatch approved by %s. Reason: %s') % (user.name, reason or ''),
            message_type='notification',
            subtype_xmlid='mail.mt_comment',
        )
        self._notify_warehouse_responsible()
        return True

    def _do_reject(self, reason, user):
        """Set state to rejected."""
        self.ensure_one()
        self.write({
            'state': 'rejected',
            'reject_user_id': user.id,
            'reject_date': fields.Datetime.now(),
            'reject_reason': reason,
        })
        self.env['mail.activity'].search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
        ]).action_done()
        self.message_post(
            body=_('GRN mismatch rejected by %s. Reason: %s') % (user.name, reason or ''),
            message_type='notification',
            subtype_xmlid='mail.mt_comment',
        )
        return True

    def _notify_warehouse_responsible(self):
        """Notify configured warehouse responsible user(s) that GRN mismatch was approved."""
        for rec in self:
            if rec.warehouse_notified:
                continue
            company = rec.picking_id.company_id or rec.purchase_id.company_id
            # Use company-level GRN responsible user if set (from settings)
            responsible_users = self.env['res.users']
            if hasattr(company, 'ks_grn_responsible_user_id') and company.ks_grn_responsible_user_id:
                responsible_users |= company.ks_grn_responsible_user_id
            # Fallback: notify the user who requested the approval
            if not responsible_users and rec.request_user_id:
                responsible_users |= rec.request_user_id
            if not responsible_users:
                continue
            rec.picking_id.message_subscribe(partner_ids=responsible_users.mapped('partner_id').ids)
            for u in responsible_users:
                rec.picking_id.activity_schedule(
                    act_type_xmlid='mail.mail_activity_data_todo',
                    summary=_('GRN Mismatch Approved: Update PO and validate receipt %s') % rec.picking_id.name,
                    note=_(
                        'Receipt %s had quantity/product mismatches which have been approved by PO approver. '
                        'Please update the Purchase Order if needed and then validate the receipt.'
                    ) % rec.picking_id.name,
                    user_id=u.id,
                )
            rec.write({'warehouse_notified': True})
            rec.picking_id.message_post(
                body=_('Warehouse responsible (%s) has been notified. Please update PO and validate receipt.')
                % ', '.join(responsible_users.mapped('name')),
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
