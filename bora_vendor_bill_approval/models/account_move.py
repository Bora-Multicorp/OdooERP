# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ── New state value ───────────────────────────────────────────────────────
    state = fields.Selection(
        selection_add=[
            ('bill_approval_pending', 'Bill Approval Pending'),
        ],
        ondelete={'bill_approval_pending': lambda recs: recs.write({'state': 'draft'})},
    )

    # State before entering approval-pending (always 'draft' for vendor bills)
    bora_bill_pre_approval_state = fields.Char(copy=False)

    # Set to True once all required PMs have approved — bypasses the approval gate
    bora_bill_approved = fields.Boolean(default=False, copy=False, tracking=True)

    # ── Approval tracking fields ──────────────────────────────────────────────
    bora_bill_pm1_id = fields.Many2one('res.users', string='Bill Approver PM1', copy=False)
    bora_bill_pm2_id = fields.Many2one('res.users', string='Bill Approver PM2', copy=False)
    bora_bill_pm1_approved = fields.Boolean(default=False, copy=False, tracking=True)
    bora_bill_pm2_approved = fields.Boolean(default=False, copy=False, tracking=True)
    bora_bill_request_reason = fields.Text(string='Request Reason', copy=False)
    bora_bill_request_user_id = fields.Many2one('res.users', string='Requested By', copy=False)
    bora_bill_request_date = fields.Datetime(string='Request Date', copy=False)

    # ── Computed UI fields ────────────────────────────────────────────────────
    # True when this move is a debit note (debit_origin_id is set).
    # Used in views to gate vendor-bill-only UI elements without declaring
    # debit_origin_id again (the debit note module already exposes it).
    bora_is_debit_note = fields.Boolean(
        compute='_compute_bora_is_debit_note',
        help='True if this journal entry is a debit note (has a debit origin).'
    )

    bora_is_bill_pm_user = fields.Boolean(compute='_compute_bora_bill_pm_user')
    bora_is_bill_admin = fields.Boolean(compute='_compute_bora_bill_admin')
    bora_is_bill_dual_approval = fields.Boolean(compute='_compute_bora_bill_dual_approval')

    bora_show_bill_approve_button = fields.Boolean(compute='_compute_bill_button_visibility')
    bora_show_bill_reject_button = fields.Boolean(compute='_compute_bill_button_visibility')
    bora_show_bill_update_button = fields.Boolean(compute='_compute_bill_button_visibility')

    # ─────────────────────────────────────────────────────────────────────────
    # Config helpers
    # ─────────────────────────────────────────────────────────────────────────
    def _get_bill_approval_config(self):
        config = self.env['bora.vendor.bill.approval.config'].get_config(
            company=self.company_id
        )
        if not config:
            raise UserError(_(
                'No active vendor bill approval configuration found for company "%s". '
                'Please configure approvers in Purchase > Configuration > '
                'Vendor Bill Approvers.'
            ) % self.company_id.name)
        return config

    def _has_bill_approval_config(self):
        return bool(
            self.env['bora.vendor.bill.approval.config'].get_config(
                company=self.company_id
            )
        )

    def _is_bill_admin_user(self):
        """Returns True if the current user is a system administrator."""
        return self.env.user._is_admin()

    # ─────────────────────────────────────────────────────────────────────────
    # Computed fields
    # ─────────────────────────────────────────────────────────────────────────
    @api.depends('debit_origin_id')
    def _compute_bora_is_debit_note(self):
        for rec in self:
            rec.bora_is_debit_note = bool(rec.debit_origin_id)

    @api.depends_context('uid')
    def _compute_bora_bill_admin(self):
        is_admin = self._is_bill_admin_user()
        for rec in self:
            rec.bora_is_bill_admin = is_admin

    @api.depends_context('uid')
    def _compute_bora_bill_pm_user(self):
        for rec in self:
            if rec._has_bill_approval_config():
                config = rec._get_bill_approval_config()
                rec.bora_is_bill_pm_user = self.env.user in config.get_all_pm_users()
            else:
                rec.bora_is_bill_pm_user = False

    @api.depends('state')
    def _compute_bora_bill_dual_approval(self):
        for rec in self:
            if rec._has_bill_approval_config():
                rec.bora_is_bill_dual_approval = rec._get_bill_approval_config().is_dual_approval()
            else:
                rec.bora_is_bill_dual_approval = False

    @api.depends(
        'state',
        'bora_is_bill_pm_user',
        'bora_bill_pm1_id', 'bora_bill_pm2_id',
        'bora_bill_pm1_approved', 'bora_bill_pm2_approved',
        'bora_bill_request_user_id',
    )
    @api.depends_context('uid')
    def _compute_bill_button_visibility(self):
        current_user = self.env.user
        for rec in self:
            rec.bora_show_bill_approve_button = False
            rec.bora_show_bill_reject_button = False
            rec.bora_show_bill_update_button = False

            is_admin = rec._is_bill_admin_user()
            is_pm = rec.bora_is_bill_pm_user

            if is_admin:
                if rec.state == 'bill_approval_pending':
                    rec.bora_show_bill_approve_button = True
                    rec.bora_show_bill_reject_button = True
                continue

            if not rec._has_bill_approval_config():
                continue

            if not is_pm:
                # Original requester can update approvers while pending
                if (rec.state == 'bill_approval_pending'
                        and rec.bora_bill_request_user_id == current_user):
                    rec.bora_show_bill_update_button = True

            if is_pm and rec.state == 'bill_approval_pending':
                # PM1 can approve if not yet done
                if (rec.bora_bill_pm1_id and current_user == rec.bora_bill_pm1_id
                        and not rec.bora_bill_pm1_approved):
                    rec.bora_show_bill_approve_button = True
                    rec.bora_show_bill_reject_button = True
                # PM2 can approve only after PM1 (sequential)
                elif (rec.bora_bill_pm2_id and current_user == rec.bora_bill_pm2_id
                      and rec.bora_bill_pm1_approved and not rec.bora_bill_pm2_approved):
                    rec.bora_show_bill_approve_button = True
                    rec.bora_show_bill_reject_button = True

    # ─────────────────────────────────────────────────────────────────────────
    # Override action_post (Confirm button)
    # ─────────────────────────────────────────────────────────────────────────
    def action_post(self):
        """Intercept Confirm for vendor bills that require approval."""
        # Validate bill date up-front so the user sees the error immediately
        # on clicking Confirm, before the approval flow begins.
        # Debit notes are excluded — they are handled by bora_debit_note_approval.
        for move in self:
            if (move.move_type == 'in_invoice'
                    and not move.debit_origin_id
                    and not move.invoice_date):
                raise UserError(_(
                    'The Bill/Refund date is required to validate this document. '
                    'Please set the Bill Date before confirming.'
                ))

        bills_needing_approval = self.env['account.move']
        bills_can_proceed = self.env['account.move']

        for move in self:
            if (move.move_type == 'in_invoice'
                    and not move.debit_origin_id  # exclude debit notes — handled by bora_debit_note_approval
                    and move.state == 'draft'
                    and move._has_bill_approval_config()
                    and not move._is_bill_admin_user()
                    and not move.bora_bill_approved):
                config = move._get_bill_approval_config()
                if self.env.user not in config.get_all_pm_users():
                    bills_needing_approval |= move
                    continue
            bills_can_proceed |= move

        for move in bills_needing_approval:
            move.write({
                'bora_bill_pre_approval_state': 'draft',
                'state': 'bill_approval_pending',
            })

        if bills_can_proceed:
            super(AccountMove, bills_can_proceed).action_post()

        if bills_needing_approval:
            return bills_needing_approval[0]._bora_open_bill_approval_wizard()

        return True

    def _bora_open_bill_approval_wizard(self, is_update=False):
        view_id = self.env.ref(
            'bora_vendor_bill_approval.bora_vendor_bill_approval_request_wizard_form'
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Update Bill Approvers') if is_update else _('Request for Approval'),
            'res_model': 'bora.vendor.bill.approval.request.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'context': {
                'default_bora_move_id': self.id,
                'bora_is_update': is_update,
                'default_bora_is_update_mode': is_update,
                'default_bora_approver1_user': self.bora_bill_pm1_id.id or False if is_update else False,
                'default_bora_approver2_user': self.bora_bill_pm2_id.id or False if is_update else False,
            },
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Workflow: submit for approval
    # ─────────────────────────────────────────────────────────────────────────
    def bora_do_request_bill_approval(self, pm1_user, pm2_user=None, reason=None):
        """Normal user submits vendor bill for approval. Called from the request wizard."""
        self.ensure_one()
        if self.state not in ('draft', 'bill_approval_pending'):
            raise UserError(_('Approval can only be requested for bills in Draft state.'))
        if not pm1_user:
            raise UserError(_('Approver 1 must be selected.'))

        config = self._get_bill_approval_config()
        if config.is_dual_approval() and not pm2_user:
            raise UserError(_('Approver 2 is required for dual approval mode.'))

        vals = {
            'state': 'bill_approval_pending',
            'bora_bill_pm1_id': pm1_user.id,
        }
        if not self.bora_bill_pre_approval_state:
            vals['bora_bill_pre_approval_state'] = 'draft'

        self.write({
            **vals,
            'bora_bill_pm2_id': pm2_user.id if pm2_user else False,
            'bora_bill_pm1_approved': False,
            'bora_bill_pm2_approved': False,
            'bora_bill_request_reason': reason or '',
            'bora_bill_request_user_id': self.env.user.id,
            'bora_bill_request_date': fields.Datetime.now(),
        })

        # Subscribe PMs to chatter
        partner_ids = [pm1_user.partner_id.id]
        if pm2_user:
            partner_ids.append(pm2_user.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)

        if config.is_dual_approval():
            msg = _('Vendor bill approval request submitted by <strong>%s</strong>. '
                    'Waiting for approval from <strong>%s</strong> (PM1) and <strong>%s</strong> (PM2).') % (
                self.env.user.name, pm1_user.name, pm2_user.name if pm2_user else '')
        else:
            msg = _('Vendor bill approval request submitted by <strong>%s</strong>. '
                    'Waiting for approval from <strong>%s</strong> (PM1).') % (
                self.env.user.name, pm1_user.name)

        if reason:
            msg += _('<br/>Reason: %s') % reason

        self.message_post(body=msg, message_type='notification', subtype_xmlid='mail.mt_note')

        # Create activity for PM1 (PM2 activity created after PM1 approves — sequential)
        self._create_bill_approval_activity(pm1_user, 'Confirm')

    # ─────────────────────────────────────────────────────────────────────────
    # Update Approvers
    # ─────────────────────────────────────────────────────────────────────────
    def action_update_bill_approvers(self):
        """Requester updates approvers while bill is pending."""
        self.ensure_one()
        if self.state != 'bill_approval_pending':
            raise UserError(_(
                "Update Approvers is only available while the bill is in 'Bill Approval Pending' state."
            ))
        if (self.bora_bill_request_user_id
                and self.bora_bill_request_user_id != self.env.user
                and not self._is_bill_admin_user()):
            raise UserError(_('Only the original requester can update the approval request.'))
        return self._bora_open_bill_approval_wizard(is_update=True)

    def bora_action_request_bill_approval(self):
        """Re-open approval wizard when stuck in bill_approval_pending with no PM1."""
        self.ensure_one()
        return self._bora_open_bill_approval_wizard()

    # ─────────────────────────────────────────────────────────────────────────
    # Approve / Reject buttons (open reason wizard)
    # ─────────────────────────────────────────────────────────────────────────
    def bora_action_approve_bill(self):
        self.ensure_one()
        if self.state != 'bill_approval_pending':
            raise UserError(_("Can only approve bills in 'Bill Approval Pending' state."))
        view_id = self.env.ref(
            'bora_vendor_bill_approval.bora_vendor_bill_approval_reason_wizard_form'
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Approve Vendor Bill'),
            'res_model': 'bora.vendor.bill.approval.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'context': {
                'default_bora_move_id': self.id,
                'default_bora_action_type': 'approve',
            },
        }

    def bora_action_reject_bill(self):
        self.ensure_one()
        if self.state != 'bill_approval_pending':
            raise UserError(_("Can only reject bills in 'Bill Approval Pending' state."))
        view_id = self.env.ref(
            'bora_vendor_bill_approval.bora_vendor_bill_approval_reason_wizard_form'
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Vendor Bill'),
            'res_model': 'bora.vendor.bill.approval.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'context': {
                'default_bora_move_id': self.id,
                'default_bora_action_type': 'reject',
            },
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Approve logic (called from reason wizard)
    # ─────────────────────────────────────────────────────────────────────────
    def _bora_do_approve_bill_with_reason(self, reason, current_user):
        self.ensure_one()
        config = self._get_bill_approval_config()

        if current_user == self.bora_bill_pm1_id and not self.bora_bill_pm1_approved:
            self.bora_bill_pm1_approved = True
            self._mark_bill_activity_done(current_user, feedback=_('✅ Approved: %s') % reason)
            self.message_post(
                body=_('✅ Bill Approved\nApproved by: PM1 - %s\nReason: %s') % (
                    current_user.name, reason),
                message_type='notification', subtype_xmlid='mail.mt_note',
            )
            if config.is_dual_approval() and self.bora_bill_pm2_id:
                # Sequential: create PM2 activity now
                self._create_bill_approval_activity(self.bora_bill_pm2_id, 'Confirm')
                return
            # Single mode — complete
            self._bora_complete_bill_approval()

        elif current_user == self.bora_bill_pm2_id and not self.bora_bill_pm2_approved:
            if not self.bora_bill_pm1_approved:
                raise UserError(_('PM1 must approve first before PM2 can approve.'))
            self.bora_bill_pm2_approved = True
            self._mark_bill_activity_done(current_user, feedback=_('✅ Approved: %s') % reason)
            self.message_post(
                body=_('✅ Bill Approved\nApproved by: PM2 - %s\nReason: %s') % (
                    current_user.name, reason),
                message_type='notification', subtype_xmlid='mail.mt_note',
            )
            self._bora_complete_bill_approval()
        else:
            raise UserError(_('You are not authorized to approve this request or have already approved.'))

    def _bora_complete_bill_approval(self):
        """All required approvals received — restore state and call action_post automatically."""
        self.ensure_one()
        config = self._get_bill_approval_config()

        if self.bora_bill_pm1_id:
            self._mark_bill_activity_done(
                self.bora_bill_pm1_id, feedback=_('Approval complete — bill confirmed'))
        if self.bora_bill_pm2_id:
            self._mark_bill_activity_done(
                self.bora_bill_pm2_id, feedback=_('Approval complete — bill confirmed'))

        if config.is_dual_approval():
            approvers = '%s (PM1) and %s (PM2)' % (
                self.bora_bill_pm1_id.name, self.bora_bill_pm2_id.name)
        else:
            approvers = '%s (PM1)' % self.bora_bill_pm1_id.name

        # Restore to draft so action_post can run properly
        self.write({
            'state': 'draft',
            'bora_bill_approved': True,
        })

        self.message_post(
            body=_('🎉 Vendor bill approved by <strong>%(approvers)s</strong> and is being confirmed.') % {
                'approvers': approvers},
            message_type='notification', subtype_xmlid='mail.mt_note',
        )

        # Notify requester
        if self.bora_bill_request_user_id:
            self.env['bus.bus']._sendone(
                self.bora_bill_request_user_id.partner_id,
                'simple_notification',
                {
                    'type': 'success',
                    'title': _('Bill Approved & Confirmed: %s') % self.name,
                    'message': _('Your vendor bill has been approved and confirmed automatically.'),
                    'sticky': True,
                },
            )

        # bora_bill_approved=True ensures action_post skips our gate
        super(AccountMove, self).action_post()

    # ─────────────────────────────────────────────────────────────────────────
    # Reject logic (called from reason wizard)
    # ─────────────────────────────────────────────────────────────────────────
    def bora_do_reject_bill(self, reason):
        self.ensure_one()
        current_user = self.env.user
        if not ((self.bora_bill_pm1_id and current_user == self.bora_bill_pm1_id) or
                (self.bora_bill_pm2_id and current_user == self.bora_bill_pm2_id)):
            raise UserError(_('You are not authorized to reject this request.'))
        if (self.bora_bill_pm2_id and current_user == self.bora_bill_pm2_id
                and not self.bora_bill_pm1_approved):
            raise UserError(_('PM1 must approve first before PM2 can reject.'))

        pm_role = ('PM1 - %s' % current_user.name
                   if current_user == self.bora_bill_pm1_id
                   else 'PM2 - %s' % current_user.name)

        self._mark_bill_activity_done(current_user, feedback=_('❌ Rejected: %s') % reason)
        self._bora_cancel_bill_activities()

        pre_state = self.bora_bill_pre_approval_state or 'draft'
        self.write({
            'state': pre_state,
            'bora_bill_pm1_id': False,
            'bora_bill_pm2_id': False,
            'bora_bill_pm1_approved': False,
            'bora_bill_pm2_approved': False,
            'bora_bill_request_user_id': False,
            'bora_bill_request_date': False,
            'bora_bill_pre_approval_state': False,
        })
        self.message_post(
            body=_('❌ Bill Rejected\nRejected by: %s\nReason: %s') % (pm_role, reason),
            message_type='notification', subtype_xmlid='mail.mt_note',
        )
        if self.bora_bill_request_user_id:
            self.env['bus.bus']._sendone(
                self.bora_bill_request_user_id.partner_id,
                'simple_notification',
                {
                    'type': 'danger',
                    'title': _('Bill Rejected: %s') % self.name,
                    'message': _('Your vendor bill approval request was rejected.'),
                    'sticky': True,
                },
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Activity helpers
    # ─────────────────────────────────────────────────────────────────────────
    def _create_bill_approval_activity(self, user, keyword='Confirm'):
        self.ensure_one()
        self.activity_schedule(
            act_type_xmlid='bora_vendor_bill_approval.mail_activity_data_bill_approval',
            summary=_('Bill Approval (%s): %s') % (keyword, self.name),
            note=_('Please review this vendor bill approval request.'),
            user_id=user.id,
            date_deadline=fields.Date.context_today(self),
        )

    def _mark_bill_activity_done(self, user, feedback=''):
        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', self.id),
            ('user_id', '=', user.id),
            ('summary', 'ilike', 'Bill Approval'),
        ])
        for act in activities:
            act.action_feedback(feedback=feedback)

    def _bora_cancel_bill_activities(self):
        """Silently cancel all bill-approval activities."""
        self.ensure_one()
        pm_ids = list(filter(None, [
            self.bora_bill_pm1_id.id if self.bora_bill_pm1_id else False,
            self.bora_bill_pm2_id.id if self.bora_bill_pm2_id else False,
        ]))
        domain = [
            ('res_model', '=', 'account.move'),
            ('res_id', '=', self.id),
            ('active', '=', True),
            ('summary', 'ilike', 'Bill Approval'),
        ]
        if pm_ids:
            domain.append(('user_id', 'in', pm_ids))
        self.env['mail.activity'].search(domain).sudo().unlink()
