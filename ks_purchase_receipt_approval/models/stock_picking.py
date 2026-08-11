# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # ks_sale_approval already adds 'approval_pending' — only add if not present
    state = fields.Selection(
        selection_add=[
            ('receipt_approval_pending', 'Receipt Approval Pending'),
        ],
        ondelete={'receipt_approval_pending': lambda recs: recs.write({'state': 'draft'})},
    )

    # Stores the picking state before entering receipt_approval_pending
    ks_receipt_pre_approval_state = fields.Char(copy=False)

    # True after all required PMs approve — bypasses the approval gate
    ks_receipt_approved = fields.Boolean(default=False, copy=False, tracking=True)

    # ---- Approval tracking fields ----
    ks_receipt_pm1_id = fields.Many2one('res.users', string='Receipt Approver PM1', copy=False)
    ks_receipt_pm2_id = fields.Many2one('res.users', string='Receipt Approver PM2', copy=False)
    ks_receipt_pm1_approved = fields.Boolean(default=False, copy=False, tracking=True)
    ks_receipt_pm2_approved = fields.Boolean(default=False, copy=False, tracking=True)
    ks_receipt_request_reason = fields.Text(string='Request Reason', copy=False)
    ks_receipt_request_user_id = fields.Many2one('res.users', string='Requested By', copy=False)
    ks_receipt_request_date = fields.Datetime(string='Request Date', copy=False)

    # ---- Computed UI fields ----
    ks_is_receipt_pm_user = fields.Boolean(compute='_compute_ks_receipt_pm_user')
    ks_is_receipt_admin = fields.Boolean(compute='_compute_ks_receipt_admin')
    ks_is_receipt_dual_approval = fields.Boolean(compute='_compute_ks_receipt_dual_approval')

    ks_show_receipt_approve_button = fields.Boolean(compute='_compute_receipt_button_visibility')
    ks_show_receipt_reject_button = fields.Boolean(compute='_compute_receipt_button_visibility')
    ks_show_receipt_update_button = fields.Boolean(compute='_compute_receipt_button_visibility')

    # -------------------------------------------------------------------------
    # Config helpers
    # -------------------------------------------------------------------------
    def _get_receipt_approval_config(self):
        config = self.env['ks.purchase.receipt.approval.config'].get_config()
        if not config:
            raise UserError(_(
                'No active purchase receipt approval configuration found. '
                'Please configure approvers in Purchase > Configuration > '
                'Purchase Receipt Approval Configuration.'
            ))
        return config

    def _has_receipt_approval_config(self):
        return bool(self.env['ks.purchase.receipt.approval.config'].get_config())

    def _is_receipt_admin_user(self):
        return bool(self.env.user.sudo().is_custom_admin)

    # -------------------------------------------------------------------------
    # Computed fields
    # -------------------------------------------------------------------------
    @api.depends_context('uid')
    def _compute_ks_receipt_admin(self):
        is_admin = self._is_receipt_admin_user()
        for rec in self:
            rec.ks_is_receipt_admin = is_admin if rec.picking_type_code == 'incoming' else False

    @api.depends_context('uid')
    def _compute_ks_receipt_pm_user(self):
        for rec in self:
            if rec.picking_type_code == 'incoming' and rec._has_receipt_approval_config():
                config = rec._get_receipt_approval_config()
                rec.ks_is_receipt_pm_user = self.env.user in config.get_all_pm_users()
            else:
                rec.ks_is_receipt_pm_user = False

    @api.depends('state')
    def _compute_ks_receipt_dual_approval(self):
        for rec in self:
            if rec.picking_type_code == 'incoming' and rec._has_receipt_approval_config():
                rec.ks_is_receipt_dual_approval = rec._get_receipt_approval_config().is_dual_approval()
            else:
                rec.ks_is_receipt_dual_approval = False

    @api.depends(
        'state', 'picking_type_code',
        'ks_is_receipt_pm_user',
        'ks_receipt_pm1_id', 'ks_receipt_pm2_id',
        'ks_receipt_pm1_approved', 'ks_receipt_pm2_approved',
        'ks_receipt_request_user_id',
    )
    @api.depends_context('uid')
    def _compute_receipt_button_visibility(self):
        current_user = self.env.user
        for rec in self:
            rec.ks_show_receipt_approve_button = False
            rec.ks_show_receipt_reject_button = False
            rec.ks_show_receipt_update_button = False

            if rec.picking_type_code != 'incoming':
                continue

            is_admin = rec._is_receipt_admin_user()
            is_pm = rec.ks_is_receipt_pm_user

            if is_admin:
                if rec.state == 'receipt_approval_pending':
                    rec.ks_show_receipt_approve_button = True
                    rec.ks_show_receipt_reject_button = True
                continue

            if not rec._has_receipt_approval_config():
                continue

            if not is_pm:
                # Original requester can update approvers while pending
                if (rec.state == 'receipt_approval_pending'
                        and rec.ks_receipt_request_user_id == current_user):
                    rec.ks_show_receipt_update_button = True

            if is_pm and rec.state == 'receipt_approval_pending':
                # PM1 can approve if not yet done
                if (rec.ks_receipt_pm1_id and current_user == rec.ks_receipt_pm1_id
                        and not rec.ks_receipt_pm1_approved):
                    rec.ks_show_receipt_approve_button = True
                    rec.ks_show_receipt_reject_button = True
                # PM2 can approve only after PM1 (sequential)
                elif (rec.ks_receipt_pm2_id and current_user == rec.ks_receipt_pm2_id
                      and rec.ks_receipt_pm1_approved and not rec.ks_receipt_pm2_approved):
                    rec.ks_show_receipt_approve_button = True
                    rec.ks_show_receipt_reject_button = True

    # -------------------------------------------------------------------------
    # Override button_validate + _action_done
    # -------------------------------------------------------------------------
    def button_validate(self):
        result = super().button_validate()

        if isinstance(result, dict):
            return result

        # Fallback: _action_done set receipt_approval_pending but return was lost
        pending = self.filtered(
            lambda p: p.state == 'receipt_approval_pending' and not p.ks_receipt_pm1_id
        )
        if pending:
            return pending[0]._ks_open_receipt_approval_wizard()

        return result

    def _action_done(self, **kwargs):
        """Intercept AFTER all Odoo dialogs for incoming receipts needing approval."""
        needs_approval = self.env['stock.picking']
        can_proceed = self.env['stock.picking']

        for picking in self:
            if (picking.picking_type_code == 'incoming'
                    and picking.state == 'assigned'
                    and picking._has_receipt_approval_config()
                    and not picking._is_receipt_admin_user()
                    and not picking.ks_receipt_approved):
                config = picking._get_receipt_approval_config()
                if self.env.user not in config.get_all_pm_users():
                    needs_approval |= picking
                    continue
            can_proceed |= picking

        for picking in needs_approval:
            picking.write({
                'ks_receipt_pre_approval_state': 'assigned',
                'state': 'receipt_approval_pending',
            })

        if can_proceed:
            super(StockPicking, can_proceed)._action_done(**kwargs)

        if needs_approval:
            return needs_approval[0]._ks_open_receipt_approval_wizard()

        return True

    def _ks_open_receipt_approval_wizard(self, is_update=False):
        view_id = self.env.ref(
            'ks_purchase_receipt_approval.ks_purchase_receipt_approval_request_wizard_form'
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Update Receipt Approvals') if is_update else _('Request for Approval'),
            'res_model': 'ks.purchase.receipt.approval.request.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'context': {
                'default_ks_picking_id': self.id,
                'ks_is_update': is_update,
                'default_ks_is_update_mode': is_update,
                'default_ks_approver1_user': self.ks_receipt_pm1_id.id or False if is_update else False,
                'default_ks_approver2_user': self.ks_receipt_pm2_id.id or False if is_update else False,
            },
        }

    # -------------------------------------------------------------------------
    # Workflow: send to receipt_approval_pending
    # -------------------------------------------------------------------------
    def ks_do_request_receipt_approval(self, pm1_user, pm2_user=None, reason=None):
        """Normal user submits receipt for approval. Called from wizard OK."""
        self.ensure_one()
        if self.state not in ('assigned', 'receipt_approval_pending'):
            raise UserError(_('Approval can only be requested for receipts in Ready state.'))
        if not pm1_user:
            raise UserError(_('Approver 1 must be selected.'))

        config = self._get_receipt_approval_config()
        if config.is_dual_approval() and not pm2_user:
            raise UserError(_('Approver 2 is required for dual approval mode.'))

        vals = {
            'state': 'receipt_approval_pending',
            'ks_receipt_pm1_id': pm1_user.id,
        }
        if not self.ks_receipt_pre_approval_state:
            vals['ks_receipt_pre_approval_state'] = 'assigned'

        self.write({
            **vals,
            'ks_receipt_pm2_id': pm2_user.id if pm2_user else False,
            'ks_receipt_pm1_approved': False,
            'ks_receipt_pm2_approved': False,
            'ks_receipt_request_reason': reason or '',
            'ks_receipt_request_user_id': self.env.user.id,
            'ks_receipt_request_date': fields.Datetime.now(),
        })

        # Subscribe PMs to chatter
        partner_ids = [pm1_user.partner_id.id]
        if pm2_user:
            partner_ids.append(pm2_user.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)

        if config.is_dual_approval():
            msg = _('Receipt approval request submitted by <strong>%s</strong>. '
                    'Waiting for approval from <strong>%s</strong> (PM1) and <strong>%s</strong> (PM2).') % (
                self.env.user.name, pm1_user.name, pm2_user.name if pm2_user else '')
        else:
            msg = _('Receipt approval request submitted by <strong>%s</strong>. '
                    'Waiting for approval from <strong>%s</strong> (PM1).') % (
                self.env.user.name, pm1_user.name)

        if reason:
            msg += _('<br/>Reason: %s') % reason

        self.message_post(body=msg, message_type='notification', subtype_xmlid='mail.mt_note')

        # Create activity for PM1 only (PM2 activity created after PM1 approves — sequential)
        self._create_receipt_approval_activity(pm1_user, 'Validate')

    # -------------------------------------------------------------------------
    # Update Approvals
    # -------------------------------------------------------------------------
    def action_update_receipt_approvals(self):
        """Requester updates approvers while pending."""
        self.ensure_one()
        if self.state != 'receipt_approval_pending':
            raise UserError(_(
                "Update Approvals is only available while the receipt is in 'Receipt Approval Pending' state."
            ))
        if (self.ks_receipt_request_user_id
                and self.ks_receipt_request_user_id != self.env.user
                and not self._is_receipt_admin_user()):
            raise UserError(_('Only the original requester can update the approval request.'))
        return self._ks_open_receipt_approval_wizard(is_update=True)

    def ks_action_request_receipt_approval(self):
        """Re-open approval wizard when stuck in receipt_approval_pending with no PM1 (e.g. user closed modal with X)."""
        self.ensure_one()
        return self._ks_open_receipt_approval_wizard()

    # -------------------------------------------------------------------------
    # Approve / Reject buttons (open reason wizard)
    # -------------------------------------------------------------------------
    def ks_action_approve_receipt(self):
        self.ensure_one()
        if self.state != 'receipt_approval_pending':
            raise UserError(_("Can only approve receipts in 'Receipt Approval Pending' state."))
        view_id = self.env.ref(
            'ks_purchase_receipt_approval.ks_purchase_receipt_approval_reason_wizard_form'
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Approve Receipt Validation'),
            'res_model': 'ks.purchase.receipt.approval.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'context': {
                'default_ks_picking_id': self.id,
                'default_ks_action_type': 'approve',
            },
        }

    def ks_action_reject_receipt(self):
        self.ensure_one()
        if self.state != 'receipt_approval_pending':
            raise UserError(_("Can only reject receipts in 'Receipt Approval Pending' state."))
        view_id = self.env.ref(
            'ks_purchase_receipt_approval.ks_purchase_receipt_approval_reason_wizard_form'
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Receipt Validation'),
            'res_model': 'ks.purchase.receipt.approval.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'context': {
                'default_ks_picking_id': self.id,
                'default_ks_action_type': 'reject',
            },
        }

    # -------------------------------------------------------------------------
    # Approve logic (called from reason wizard)
    # -------------------------------------------------------------------------
    def _ks_do_approve_receipt_with_reason(self, reason, current_user):
        self.ensure_one()
        config = self._get_receipt_approval_config()

        if current_user == self.ks_receipt_pm1_id and not self.ks_receipt_pm1_approved:
            self.ks_receipt_pm1_approved = True
            self._mark_receipt_activity_done(current_user, feedback=_('✅ Approved: %s') % reason)
            self.message_post(
                body=_('✅ Receipt Approved\nApproved by: PM1 - %s\nReason: %s') % (
                    current_user.name, reason),
                message_type='notification', subtype_xmlid='mail.mt_note',
            )
            if config.is_dual_approval() and self.ks_receipt_pm2_id:
                # Sequential: create PM2 activity now
                self._create_receipt_approval_activity(self.ks_receipt_pm2_id, 'Validate')
                return
            # Single mode — complete
            self._ks_complete_receipt_approval()

        elif current_user == self.ks_receipt_pm2_id and not self.ks_receipt_pm2_approved:
            if not self.ks_receipt_pm1_approved:
                raise UserError(_('PM1 must approve first before PM2 can approve.'))
            self.ks_receipt_pm2_approved = True
            self._mark_receipt_activity_done(current_user, feedback=_('✅ Approved: %s') % reason)
            self.message_post(
                body=_('✅ Receipt Approved\nApproved by: PM2 - %s\nReason: %s') % (
                    current_user.name, reason),
                message_type='notification', subtype_xmlid='mail.mt_note',
            )
            self._ks_complete_receipt_approval()
        else:
            raise UserError(_('You are not authorized to approve this request or have already approved.'))

    def _ks_complete_receipt_approval(self):
        """All required approvals received — restore state and complete the receipt."""
        self.ensure_one()
        config = self._get_receipt_approval_config()

        if self.ks_receipt_pm1_id:
            self._mark_receipt_activity_done(
                self.ks_receipt_pm1_id, feedback=_('Approval complete — receipt validated'))
        if self.ks_receipt_pm2_id:
            self._mark_receipt_activity_done(
                self.ks_receipt_pm2_id, feedback=_('Approval complete — receipt validated'))

        if config.is_dual_approval():
            approvers = '%s (PM1) and %s (PM2)' % (
                self.ks_receipt_pm1_id.name, self.ks_receipt_pm2_id.name)
        else:
            approvers = '%s (PM1)' % self.ks_receipt_pm1_id.name

        pre_state = self.ks_receipt_pre_approval_state or 'assigned'
        self.write({
            'state': pre_state,
            'ks_receipt_approved': True,
        })

        self.message_post(
            body=_('🎉 Receipt validated and approved by <strong>%(approvers)s</strong>.') % {
                'approvers': approvers},
            message_type='notification', subtype_xmlid='mail.mt_note',
        )

        # Notify requester
        if self.ks_receipt_request_user_id:
            self.env['bus.bus']._sendone(
                self.ks_receipt_request_user_id.partner_id,
                'simple_notification',
                {
                    'type': 'success',
                    'title': _('Receipt Approved & Done: %s') % self.name,
                    'message': _('Your receipt has been approved and marked as done.'),
                    'sticky': True,
                },
            )

        # ks_receipt_approved=True ensures _action_done skips our gate
        self._action_done()

    # -------------------------------------------------------------------------
    # Reject logic (called from reason wizard)
    # -------------------------------------------------------------------------
    def ks_do_reject_receipt(self, reason):
        self.ensure_one()
        current_user = self.env.user
        if not ((self.ks_receipt_pm1_id and current_user == self.ks_receipt_pm1_id) or
                (self.ks_receipt_pm2_id and current_user == self.ks_receipt_pm2_id)):
            raise UserError(_('You are not authorized to reject this request.'))
        if (self.ks_receipt_pm2_id and current_user == self.ks_receipt_pm2_id
                and not self.ks_receipt_pm1_approved):
            raise UserError(_('PM1 must approve first before PM2 can reject.'))

        pm_role = ('PM1 - %s' % current_user.name
                   if current_user == self.ks_receipt_pm1_id
                   else 'PM2 - %s' % current_user.name)

        self._mark_receipt_activity_done(current_user, feedback=_('❌ Rejected: %s') % reason)
        self._ks_cancel_receipt_activities()

        pre_state = self.ks_receipt_pre_approval_state or 'assigned'
        self.write({
            'state': pre_state,
            'ks_receipt_pm1_id': False,
            'ks_receipt_pm2_id': False,
            'ks_receipt_pm1_approved': False,
            'ks_receipt_pm2_approved': False,
            'ks_receipt_request_user_id': False,
            'ks_receipt_request_date': False,
            'ks_receipt_pre_approval_state': False,
        })
        self.message_post(
            body=_('❌ Receipt Rejected\nRejected by: %s\nReason: %s') % (pm_role, reason),
            message_type='notification', subtype_xmlid='mail.mt_note',
        )
        if self.ks_receipt_request_user_id:
            self.env['bus.bus']._sendone(
                self.ks_receipt_request_user_id.partner_id,
                'simple_notification',
                {
                    'type': 'danger',
                    'title': _('Receipt Rejected: %s') % self.name,
                    'message': _('Your receipt approval request was rejected.'),
                    'sticky': True,
                },
            )

    # -------------------------------------------------------------------------
    # Activity helpers
    # -------------------------------------------------------------------------
    def _create_receipt_approval_activity(self, user, keyword='Validate'):
        self.ensure_one()
        self.activity_schedule(
            act_type_xmlid='ks_purchase_receipt_approval.mail_activity_data_receipt_approval',
            summary=_('Receipt Approval (%s): %s') % (keyword, self.name),
            note=_('Please review this purchase receipt approval request.'),
            user_id=user.id,
            date_deadline=fields.Date.context_today(self),
        )

    def _mark_receipt_activity_done(self, user, feedback=''):
        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'stock.picking'),
            ('res_id', '=', self.id),
            ('user_id', '=', user.id),
            ('summary', 'ilike', 'Receipt Approval'),
        ])
        for act in activities:
            act.action_feedback(feedback=feedback)

    def _ks_cancel_receipt_activities(self):
        """Silently cancel all receipt-approval activities."""
        self.ensure_one()
        pm_ids = list(filter(None, [
            self.ks_receipt_pm1_id.id if self.ks_receipt_pm1_id else False,
            self.ks_receipt_pm2_id.id if self.ks_receipt_pm2_id else False,
        ]))
        domain = [
            ('res_model', '=', 'stock.picking'),
            ('res_id', '=', self.id),
            ('active', '=', True),
            ('summary', 'ilike', 'Receipt Approval'),
        ]
        if pm_ids:
            domain.append(('user_id', 'in', pm_ids))
        self.env['mail.activity'].search(domain).sudo().unlink()
