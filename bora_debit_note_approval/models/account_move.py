# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ── New state value ───────────────────────────────────────────────────────
    state = fields.Selection(
        selection_add=[
            ('debit_note_approval_pending', 'Debit Note Approval Pending'),
        ],
        ondelete={'debit_note_approval_pending': lambda recs: recs.write({'state': 'draft'})},
    )

    # State before entering approval-pending (always 'draft' for debit notes)
    bora_dn_pre_approval_state = fields.Char(copy=False)

    # Set to True once all required PMs have approved — bypasses the approval gate
    bora_dn_approved = fields.Boolean(default=False, copy=False, tracking=True)

    # ── Approval tracking fields ──────────────────────────────────────────────
    bora_dn_pm1_id = fields.Many2one('res.users', string='DN Approver PM1', copy=False)
    bora_dn_pm2_id = fields.Many2one('res.users', string='DN Approver PM2', copy=False)
    bora_dn_pm1_approved = fields.Boolean(default=False, copy=False, tracking=True)
    bora_dn_pm2_approved = fields.Boolean(default=False, copy=False, tracking=True)
    bora_dn_request_reason = fields.Text(string='Request Reason', copy=False)
    bora_dn_request_user_id = fields.Many2one('res.users', string='Requested By', copy=False)
    bora_dn_request_date = fields.Datetime(string='Request Date', copy=False)

    # ── Computed UI fields ────────────────────────────────────────────────────
    bora_is_dn_pm_user = fields.Boolean(compute='_compute_bora_dn_pm_user')
    bora_is_dn_admin = fields.Boolean(compute='_compute_bora_dn_admin')
    bora_is_dn_dual_approval = fields.Boolean(compute='_compute_bora_dn_dual_approval')

    bora_show_dn_approve_button = fields.Boolean(compute='_compute_dn_button_visibility')
    bora_show_dn_reject_button = fields.Boolean(compute='_compute_dn_button_visibility')
    bora_show_dn_update_button = fields.Boolean(compute='_compute_dn_button_visibility')

    # ─────────────────────────────────────────────────────────────────────────
    # Helper: is this move a debit note?
    # Both vendor debit notes (in_invoice + debit_origin_id) and
    # customer debit notes (out_invoice + debit_origin_id) qualify.
    # ─────────────────────────────────────────────────────────────────────────
    def _is_debit_note(self):
        return bool(self.debit_origin_id)

    # ─────────────────────────────────────────────────────────────────────────
    # Config helpers
    # ─────────────────────────────────────────────────────────────────────────
    def _get_dn_approval_config(self):
        config = self.env['bora.debit.note.approval.config'].get_config(
            company=self.company_id
        )
        if not config:
            raise UserError(_(
                'No active debit note approval configuration found for company "%s". '
                'Please configure approvers in Accounting > Configuration > '
                'Debit Note Approvers.'
            ) % self.company_id.name)
        return config

    def _has_dn_approval_config(self):
        return bool(
            self.env['bora.debit.note.approval.config'].get_config(
                company=self.company_id
            )
        )

    def _is_dn_admin_user(self):
        """Returns True if the current user is a system administrator."""
        return self.env.user._is_admin()

    # ─────────────────────────────────────────────────────────────────────────
    # Computed fields
    # ─────────────────────────────────────────────────────────────────────────
    @api.depends_context('uid')
    def _compute_bora_dn_admin(self):
        is_admin = self._is_dn_admin_user()
        for rec in self:
            rec.bora_is_dn_admin = is_admin

    @api.depends_context('uid')
    def _compute_bora_dn_pm_user(self):
        for rec in self:
            if rec._has_dn_approval_config():
                config = rec._get_dn_approval_config()
                rec.bora_is_dn_pm_user = self.env.user in config.get_all_pm_users()
            else:
                rec.bora_is_dn_pm_user = False

    @api.depends('state')
    def _compute_bora_dn_dual_approval(self):
        for rec in self:
            if rec._has_dn_approval_config():
                rec.bora_is_dn_dual_approval = rec._get_dn_approval_config().is_dual_approval()
            else:
                rec.bora_is_dn_dual_approval = False

    @api.depends(
        'state',
        'bora_is_dn_pm_user',
        'bora_dn_pm1_id', 'bora_dn_pm2_id',
        'bora_dn_pm1_approved', 'bora_dn_pm2_approved',
        'bora_dn_request_user_id',
    )
    @api.depends_context('uid')
    def _compute_dn_button_visibility(self):
        current_user = self.env.user
        for rec in self:
            rec.bora_show_dn_approve_button = False
            rec.bora_show_dn_reject_button = False
            rec.bora_show_dn_update_button = False

            is_admin = rec._is_dn_admin_user()
            is_pm = rec.bora_is_dn_pm_user

            if is_admin:
                if rec.state == 'debit_note_approval_pending':
                    rec.bora_show_dn_approve_button = True
                    rec.bora_show_dn_reject_button = True
                continue

            if not rec._has_dn_approval_config():
                continue

            if not is_pm:
                # Original requester can update approvers while pending
                if (rec.state == 'debit_note_approval_pending'
                        and rec.bora_dn_request_user_id == current_user):
                    rec.bora_show_dn_update_button = True

            if is_pm and rec.state == 'debit_note_approval_pending':
                # PM1 can approve if not yet done
                if (rec.bora_dn_pm1_id and current_user == rec.bora_dn_pm1_id
                        and not rec.bora_dn_pm1_approved):
                    rec.bora_show_dn_approve_button = True
                    rec.bora_show_dn_reject_button = True
                # PM2 can approve only after PM1 (sequential)
                elif (rec.bora_dn_pm2_id and current_user == rec.bora_dn_pm2_id
                      and rec.bora_dn_pm1_approved and not rec.bora_dn_pm2_approved):
                    rec.bora_show_dn_approve_button = True
                    rec.bora_show_dn_reject_button = True

    # ─────────────────────────────────────────────────────────────────────────
    # Override action_post (Confirm button)
    # ─────────────────────────────────────────────────────────────────────────
    def action_post(self):
        """Intercept Confirm for debit notes that require approval."""
        # Validate debit note date up-front so the user sees the error immediately
        # on clicking Confirm, before the approval flow begins.
        for move in self:
            if move._is_debit_note() and not move.invoice_date:
                raise UserError(_(
                    'The Debit Note date is required to validate this document. '
                    'Please set the date before confirming.'
                ))

        dn_needing_approval = self.env['account.move']
        dn_can_proceed = self.env['account.move']

        for move in self:
            if (move._is_debit_note()
                    and move.state == 'draft'
                    and move._has_dn_approval_config()
                    and not move._is_dn_admin_user()
                    and not move.bora_dn_approved):
                config = move._get_dn_approval_config()
                if self.env.user not in config.get_all_pm_users():
                    dn_needing_approval |= move
                    continue
            dn_can_proceed |= move

        for move in dn_needing_approval:
            move.write({
                'bora_dn_pre_approval_state': 'draft',
                'state': 'debit_note_approval_pending',
            })

        if dn_can_proceed:
            super(AccountMove, dn_can_proceed).action_post()

        if dn_needing_approval:
            return dn_needing_approval[0]._bora_open_dn_approval_wizard()

        return True

    def _bora_open_dn_approval_wizard(self, is_update=False):
        view_id = self.env.ref(
            'bora_debit_note_approval.bora_debit_note_approval_request_wizard_form'
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Update DN Approvers') if is_update else _('Request for Approval'),
            'res_model': 'bora.debit.note.approval.request.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'context': {
                'default_bora_dn_move_id': self.id,
                'bora_dn_is_update': is_update,
                'default_bora_dn_is_update_mode': is_update,
                'default_bora_dn_approver1_user': self.bora_dn_pm1_id.id or False if is_update else False,
                'default_bora_dn_approver2_user': self.bora_dn_pm2_id.id or False if is_update else False,
            },
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Workflow: submit for approval
    # ─────────────────────────────────────────────────────────────────────────
    def bora_dn_do_request_approval(self, pm1_user, pm2_user=None, reason=None):
        """Normal user submits debit note for approval. Called from the request wizard."""
        self.ensure_one()
        if self.state not in ('draft', 'debit_note_approval_pending'):
            raise UserError(_('Approval can only be requested for debit notes in Draft state.'))
        if not pm1_user:
            raise UserError(_('Approver 1 must be selected.'))

        config = self._get_dn_approval_config()
        if config.is_dual_approval() and not pm2_user:
            raise UserError(_('Approver 2 is required for dual approval mode.'))

        vals = {
            'state': 'debit_note_approval_pending',
            'bora_dn_pm1_id': pm1_user.id,
        }
        if not self.bora_dn_pre_approval_state:
            vals['bora_dn_pre_approval_state'] = 'draft'

        self.write({
            **vals,
            'bora_dn_pm2_id': pm2_user.id if pm2_user else False,
            'bora_dn_pm1_approved': False,
            'bora_dn_pm2_approved': False,
            'bora_dn_request_reason': reason or '',
            'bora_dn_request_user_id': self.env.user.id,
            'bora_dn_request_date': fields.Datetime.now(),
        })

        # Subscribe PMs to chatter
        partner_ids = [pm1_user.partner_id.id]
        if pm2_user:
            partner_ids.append(pm2_user.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)

        if config.is_dual_approval():
            msg = _('Debit note approval request submitted by <strong>%s</strong>. '
                    'Waiting for approval from <strong>%s</strong> (PM1) and <strong>%s</strong> (PM2).') % (
                self.env.user.name, pm1_user.name, pm2_user.name if pm2_user else '')
        else:
            msg = _('Debit note approval request submitted by <strong>%s</strong>. '
                    'Waiting for approval from <strong>%s</strong> (PM1).') % (
                self.env.user.name, pm1_user.name)

        if reason:
            msg += _('<br/>Reason: %s') % reason

        self.message_post(body=msg, message_type='notification', subtype_xmlid='mail.mt_note')

        # Create activity for PM1 (PM2 activity created after PM1 approves — sequential)
        self._create_dn_approval_activity(pm1_user, 'Confirm')

    # ─────────────────────────────────────────────────────────────────────────
    # Update Approvers
    # ─────────────────────────────────────────────────────────────────────────
    def action_update_dn_approvers(self):
        """Requester updates approvers while debit note is pending."""
        self.ensure_one()
        if self.state != 'debit_note_approval_pending':
            raise UserError(_(
                "Update Approvers is only available while the debit note is in "
                "'Debit Note Approval Pending' state."
            ))
        if (self.bora_dn_request_user_id
                and self.bora_dn_request_user_id != self.env.user
                and not self._is_dn_admin_user()):
            raise UserError(_('Only the original requester can update the approval request.'))
        return self._bora_open_dn_approval_wizard(is_update=True)

    def bora_action_request_dn_approval(self):
        """Re-open approval wizard when stuck in debit_note_approval_pending with no PM1."""
        self.ensure_one()
        return self._bora_open_dn_approval_wizard()

    # ─────────────────────────────────────────────────────────────────────────
    # Approve / Reject buttons (open reason wizard)
    # ─────────────────────────────────────────────────────────────────────────
    def bora_action_approve_dn(self):
        self.ensure_one()
        if self.state != 'debit_note_approval_pending':
            raise UserError(_("Can only approve debit notes in 'Debit Note Approval Pending' state."))
        view_id = self.env.ref(
            'bora_debit_note_approval.bora_debit_note_approval_reason_wizard_form'
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Approve Debit Note'),
            'res_model': 'bora.debit.note.approval.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'context': {
                'default_bora_dn_move_id': self.id,
                'default_bora_dn_action_type': 'approve',
            },
        }

    def bora_action_reject_dn(self):
        self.ensure_one()
        if self.state != 'debit_note_approval_pending':
            raise UserError(_("Can only reject debit notes in 'Debit Note Approval Pending' state."))
        view_id = self.env.ref(
            'bora_debit_note_approval.bora_debit_note_approval_reason_wizard_form'
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Debit Note'),
            'res_model': 'bora.debit.note.approval.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'context': {
                'default_bora_dn_move_id': self.id,
                'default_bora_dn_action_type': 'reject',
            },
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Approve logic (called from reason wizard)
    # ─────────────────────────────────────────────────────────────────────────
    def _bora_do_approve_dn_with_reason(self, reason, current_user):
        self.ensure_one()
        config = self._get_dn_approval_config()

        if current_user == self.bora_dn_pm1_id and not self.bora_dn_pm1_approved:
            self.bora_dn_pm1_approved = True
            self._mark_dn_activity_done(current_user, feedback=_('✅ Approved: %s') % reason)
            self.message_post(
                body=_('✅ Debit Note Approved\nApproved by: PM1 - %s\nReason: %s') % (
                    current_user.name, reason),
                message_type='notification', subtype_xmlid='mail.mt_note',
            )
            if config.is_dual_approval() and self.bora_dn_pm2_id:
                # Sequential: create PM2 activity now
                self._create_dn_approval_activity(self.bora_dn_pm2_id, 'Confirm')
                return
            # Single mode — complete
            self._bora_complete_dn_approval()

        elif current_user == self.bora_dn_pm2_id and not self.bora_dn_pm2_approved:
            if not self.bora_dn_pm1_approved:
                raise UserError(_('PM1 must approve first before PM2 can approve.'))
            self.bora_dn_pm2_approved = True
            self._mark_dn_activity_done(current_user, feedback=_('✅ Approved: %s') % reason)
            self.message_post(
                body=_('✅ Debit Note Approved\nApproved by: PM2 - %s\nReason: %s') % (
                    current_user.name, reason),
                message_type='notification', subtype_xmlid='mail.mt_note',
            )
            self._bora_complete_dn_approval()
        else:
            raise UserError(_('You are not authorized to approve this request or have already approved.'))

    def _bora_complete_dn_approval(self):
        """All required approvals received — restore state and call action_post automatically."""
        self.ensure_one()
        config = self._get_dn_approval_config()

        if self.bora_dn_pm1_id:
            self._mark_dn_activity_done(
                self.bora_dn_pm1_id, feedback=_('Approval complete — debit note confirmed'))
        if self.bora_dn_pm2_id:
            self._mark_dn_activity_done(
                self.bora_dn_pm2_id, feedback=_('Approval complete — debit note confirmed'))

        if config.is_dual_approval():
            approvers = '%s (PM1) and %s (PM2)' % (
                self.bora_dn_pm1_id.name, self.bora_dn_pm2_id.name)
        else:
            approvers = '%s (PM1)' % self.bora_dn_pm1_id.name

        # Restore to draft so action_post can run properly
        self.write({
            'state': 'draft',
            'bora_dn_approved': True,
        })

        self.message_post(
            body=_('🎉 Debit note approved by <strong>%(approvers)s</strong> and is being confirmed.') % {
                'approvers': approvers},
            message_type='notification', subtype_xmlid='mail.mt_note',
        )

        # Notify requester
        if self.bora_dn_request_user_id:
            self.env['bus.bus']._sendone(
                self.bora_dn_request_user_id.partner_id,
                'simple_notification',
                {
                    'type': 'success',
                    'title': _('Debit Note Approved & Confirmed: %s') % self.name,
                    'message': _('Your debit note has been approved and confirmed automatically.'),
                    'sticky': True,
                },
            )

        # bora_dn_approved=True ensures action_post skips our gate
        super(AccountMove, self).action_post()

    # ─────────────────────────────────────────────────────────────────────────
    # Reject logic (called from reason wizard)
    # ─────────────────────────────────────────────────────────────────────────
    def bora_dn_do_reject(self, reason):
        self.ensure_one()
        current_user = self.env.user
        if not ((self.bora_dn_pm1_id and current_user == self.bora_dn_pm1_id) or
                (self.bora_dn_pm2_id and current_user == self.bora_dn_pm2_id)):
            raise UserError(_('You are not authorized to reject this request.'))
        if (self.bora_dn_pm2_id and current_user == self.bora_dn_pm2_id
                and not self.bora_dn_pm1_approved):
            raise UserError(_('PM1 must approve first before PM2 can reject.'))

        pm_role = ('PM1 - %s' % current_user.name
                   if current_user == self.bora_dn_pm1_id
                   else 'PM2 - %s' % current_user.name)

        self._mark_dn_activity_done(current_user, feedback=_('❌ Rejected: %s') % reason)
        self._bora_cancel_dn_activities()

        pre_state = self.bora_dn_pre_approval_state or 'draft'
        self.write({
            'state': pre_state,
            'bora_dn_pm1_id': False,
            'bora_dn_pm2_id': False,
            'bora_dn_pm1_approved': False,
            'bora_dn_pm2_approved': False,
            'bora_dn_request_user_id': False,
            'bora_dn_request_date': False,
            'bora_dn_pre_approval_state': False,
        })
        self.message_post(
            body=_('❌ Debit Note Rejected\nRejected by: %s\nReason: %s') % (pm_role, reason),
            message_type='notification', subtype_xmlid='mail.mt_note',
        )
        if self.bora_dn_request_user_id:
            self.env['bus.bus']._sendone(
                self.bora_dn_request_user_id.partner_id,
                'simple_notification',
                {
                    'type': 'danger',
                    'title': _('Debit Note Rejected: %s') % self.name,
                    'message': _('Your debit note approval request was rejected.'),
                    'sticky': True,
                },
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Activity helpers
    # ─────────────────────────────────────────────────────────────────────────
    def _create_dn_approval_activity(self, user, keyword='Confirm'):
        self.ensure_one()
        self.activity_schedule(
            act_type_xmlid='bora_debit_note_approval.mail_activity_data_dn_approval',
            summary=_('Debit Note Approval (%s): %s') % (keyword, self.name),
            note=_('Please review this debit note approval request.'),
            user_id=user.id,
            date_deadline=fields.Date.context_today(self),
        )

    def _mark_dn_activity_done(self, user, feedback=''):
        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', self.id),
            ('user_id', '=', user.id),
            ('summary', 'ilike', 'Debit Note Approval'),
        ])
        for act in activities:
            act.action_feedback(feedback=feedback)

    def _bora_cancel_dn_activities(self):
        """Silently cancel all debit-note-approval activities."""
        self.ensure_one()
        pm_ids = list(filter(None, [
            self.bora_dn_pm1_id.id if self.bora_dn_pm1_id else False,
            self.bora_dn_pm2_id.id if self.bora_dn_pm2_id else False,
        ]))
        domain = [
            ('res_model', '=', 'account.move'),
            ('res_id', '=', self.id),
            ('active', '=', True),
            ('summary', 'ilike', 'Debit Note Approval'),
        ]
        if pm_ids:
            domain.append(('user_id', 'in', pm_ids))
        self.env['mail.activity'].search(domain).sudo().unlink()
