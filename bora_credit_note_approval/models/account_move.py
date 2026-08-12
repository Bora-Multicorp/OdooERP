# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ── New state value ───────────────────────────────────────────────────────
    state = fields.Selection(
        selection_add=[
            ('credit_note_approval_pending', 'Credit Note Approval Pending'),
        ],
        ondelete={'credit_note_approval_pending': lambda recs: recs.write({'state': 'draft'})},
    )

    # State before entering approval-pending (always 'draft' for credit notes)
    bora_cn_pre_approval_state = fields.Char(copy=False)

    # Set to True once all required PMs have approved — bypasses the approval gate
    bora_cn_approved = fields.Boolean(default=False, copy=False, tracking=True)

    # ── Approval tracking fields ──────────────────────────────────────────────
    bora_cn_pm1_id = fields.Many2one('res.users', string='CN Approver PM1', copy=False)
    bora_cn_pm2_id = fields.Many2one('res.users', string='CN Approver PM2', copy=False)
    bora_cn_pm1_approved = fields.Boolean(default=False, copy=False, tracking=True)
    bora_cn_pm2_approved = fields.Boolean(default=False, copy=False, tracking=True)
    bora_cn_request_reason = fields.Text(string='Request Reason', copy=False)
    bora_cn_request_user_id = fields.Many2one('res.users', string='Requested By', copy=False)
    bora_cn_request_date = fields.Datetime(string='Request Date', copy=False)

    # ── Computed UI fields ────────────────────────────────────────────────────
    bora_is_cn_pm_user = fields.Boolean(compute='_compute_bora_cn_pm_user')
    bora_is_cn_admin = fields.Boolean(compute='_compute_bora_cn_admin')
    bora_is_cn_dual_approval = fields.Boolean(compute='_compute_bora_cn_dual_approval')

    bora_show_cn_approve_button = fields.Boolean(compute='_compute_cn_button_visibility')
    bora_show_cn_reject_button = fields.Boolean(compute='_compute_cn_button_visibility')
    bora_show_cn_update_button = fields.Boolean(compute='_compute_cn_button_visibility')

    # ─────────────────────────────────────────────────────────────────────────
    # Helper: is this move a credit note?
    # Customer credit notes (out_refund) and Vendor credit notes (in_refund) qualify.
    # ─────────────────────────────────────────────────────────────────────────
    def _is_credit_note(self):
        return self.move_type in ('out_refund', 'in_refund')

    # ─────────────────────────────────────────────────────────────────────────
    # Config helpers
    # ─────────────────────────────────────────────────────────────────────────
    def _get_cn_approval_config(self):
        config = self.env['bora.credit.note.approval.config'].get_config(
            company=self.company_id
        )
        if not config:
            raise UserError(_(
                'No active credit note approval configuration found for company "%s". '
                'Please configure approvers in Accounting > Configuration > '
                'Credit Note Approvers.'
            ) % self.company_id.name)
        return config

    def _has_cn_approval_config(self):
        return bool(
            self.env['bora.credit.note.approval.config'].get_config(
                company=self.company_id
            )
        )

    def _is_cn_admin_user(self):
        """Returns True if the current user is a system administrator."""
        return self.env.user._is_admin()

    # ─────────────────────────────────────────────────────────────────────────
    # Computed fields
    # ─────────────────────────────────────────────────────────────────────────
    @api.depends_context('uid')
    def _compute_bora_cn_admin(self):
        is_admin = self._is_cn_admin_user()
        for rec in self:
            rec.bora_is_cn_admin = is_admin if rec._is_credit_note() else False

    @api.depends_context('uid')
    def _compute_bora_cn_pm_user(self):
        for rec in self:
            if rec._is_credit_note() and rec._has_cn_approval_config():
                config = rec._get_cn_approval_config()
                rec.bora_is_cn_pm_user = self.env.user in config.get_all_pm_users()
            else:
                rec.bora_is_cn_pm_user = False

    @api.depends('state')
    def _compute_bora_cn_dual_approval(self):
        for rec in self:
            if rec._is_credit_note() and rec._has_cn_approval_config():
                rec.bora_is_cn_dual_approval = rec._get_cn_approval_config().is_dual_approval()
            else:
                rec.bora_is_cn_dual_approval = False

    @api.depends(
        'state', 'move_type',
        'bora_is_cn_pm_user',
        'bora_cn_pm1_id', 'bora_cn_pm2_id',
        'bora_cn_pm1_approved', 'bora_cn_pm2_approved',
        'bora_cn_request_user_id',
    )
    @api.depends_context('uid')
    def _compute_cn_button_visibility(self):
        current_user = self.env.user
        for rec in self:
            rec.bora_show_cn_approve_button = False
            rec.bora_show_cn_reject_button = False
            rec.bora_show_cn_update_button = False

            if not rec._is_credit_note():
                continue

            is_admin = rec._is_cn_admin_user()
            is_pm = rec.bora_is_cn_pm_user

            if is_admin:
                if rec.state == 'credit_note_approval_pending':
                    rec.bora_show_cn_approve_button = True
                    rec.bora_show_cn_reject_button = True
                continue

            if not rec._has_cn_approval_config():
                continue

            if not is_pm:
                # Original requester can update approvers while pending
                if (rec.state == 'credit_note_approval_pending'
                        and rec.bora_cn_request_user_id == current_user):
                    rec.bora_show_cn_update_button = True

            if is_pm and rec.state == 'credit_note_approval_pending':
                # PM1 can approve if not yet done
                if (rec.bora_cn_pm1_id and current_user == rec.bora_cn_pm1_id
                        and not rec.bora_cn_pm1_approved):
                    rec.bora_show_cn_approve_button = True
                    rec.bora_show_cn_reject_button = True
                # PM2 can approve only after PM1 (sequential)
                elif (rec.bora_cn_pm2_id and current_user == rec.bora_cn_pm2_id
                      and rec.bora_cn_pm1_approved and not rec.bora_cn_pm2_approved):
                    rec.bora_show_cn_approve_button = True
                    rec.bora_show_cn_reject_button = True

    # ─────────────────────────────────────────────────────────────────────────
    # Override action_post (Confirm button)
    # ─────────────────────────────────────────────────────────────────────────
    def action_post(self):
        """Intercept Confirm for credit notes that require approval."""
        # Validate credit note date up-front so the user sees the error immediately
        # on clicking Confirm, before the approval flow begins.
        for move in self:
            if move._is_credit_note() and not move.invoice_date:
                raise UserError(_(
                    'The Credit Note date is required to validate this document. '
                    'Please set the date before confirming.'
                ))

        cn_needing_approval = self.env['account.move']
        cn_can_proceed = self.env['account.move']

        for move in self:
            if (move._is_credit_note()
                    and move.state == 'draft'
                    and not move._is_cn_admin_user()
                    and not move.bora_cn_approved):
                config = move._get_cn_approval_config()
                if self.env.user not in config.get_all_pm_users():
                    cn_needing_approval |= move
                    continue
            cn_can_proceed |= move

        for move in cn_needing_approval:
            move.write({
                'bora_cn_pre_approval_state': 'draft',
                'state': 'credit_note_approval_pending',
            })

        res = True
        if cn_can_proceed:
            res = super(AccountMove, cn_can_proceed).action_post()

        if cn_needing_approval:
            return cn_needing_approval[0]._bora_open_cn_approval_wizard()

        return res

    def _bora_open_cn_approval_wizard(self, is_update=False):
        view_id = self.env.ref(
            'bora_credit_note_approval.bora_credit_note_approval_request_wizard_form'
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Update CN Approvers') if is_update else _('Request for Approval'),
            'res_model': 'bora.credit.note.approval.request.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'context': {
                'default_bora_cn_move_id': self.id,
                'bora_cn_is_update': is_update,
                'default_bora_cn_is_update_mode': is_update,
                'default_bora_cn_approver1_user': self.bora_cn_pm1_id.id or False if is_update else False,
                'default_bora_cn_approver2_user': self.bora_cn_pm2_id.id or False if is_update else False,
            },
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Workflow: submit for approval
    # ─────────────────────────────────────────────────────────────────────────
    def bora_cn_do_request_approval(self, pm1_user, pm2_user=None, reason=None):
        """Normal user submits credit note for approval. Called from the request wizard."""
        self.ensure_one()
        if self.state not in ('draft', 'credit_note_approval_pending'):
            raise UserError(_('Approval can only be requested for credit notes in Draft state.'))
        if not pm1_user:
            raise UserError(_('Approver 1 must be selected.'))

        config = self._get_cn_approval_config()
        if config.is_dual_approval() and not pm2_user:
            raise UserError(_('Approver 2 is required for dual approval mode.'))

        vals = {
            'state': 'credit_note_approval_pending',
            'bora_cn_pm1_id': pm1_user.id,
        }
        if not self.bora_cn_pre_approval_state:
            vals['bora_cn_pre_approval_state'] = 'draft'

        self.write({
            **vals,
            'bora_cn_pm2_id': pm2_user.id if pm2_user else False,
            'bora_cn_pm1_approved': False,
            'bora_cn_pm2_approved': False,
            'bora_cn_request_reason': reason or '',
            'bora_cn_request_user_id': self.env.user.id,
            'bora_cn_request_date': fields.Datetime.now(),
        })

        # Subscribe PMs to chatter
        partner_ids = [pm1_user.partner_id.id]
        if pm2_user:
            partner_ids.append(pm2_user.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)

        if config.is_dual_approval():
            msg = _('Credit note approval request submitted by <strong>%s</strong>. '
                    'Waiting for approval from <strong>%s</strong> (PM1) and <strong>%s</strong> (PM2).') % (
                self.env.user.name, pm1_user.name, pm2_user.name if pm2_user else '')
        else:
            msg = _('Credit note approval request submitted by <strong>%s</strong>. '
                    'Waiting for approval from <strong>%s</strong> (PM1).') % (
                self.env.user.name, pm1_user.name)

        if reason:
            msg += _('<br/>Reason: %s') % reason

        self.message_post(body=msg, message_type='notification', subtype_xmlid='mail.mt_note')

        # Create activity for PM1 (PM2 activity created after PM1 approves — sequential)
        self._create_cn_approval_activity(pm1_user, 'Confirm')

    # ─────────────────────────────────────────────────────────────────────────
    # Update Approvers
    # ─────────────────────────────────────────────────────────────────────────
    def action_update_cn_approvers(self):
        """Requester updates approvers while credit note is pending."""
        self.ensure_one()
        if self.state != 'credit_note_approval_pending':
            raise UserError(_(
                "Update Approvers is only available while the credit note is in "
                "'Credit Note Approval Pending' state."
            ))
        if (self.bora_cn_request_user_id
                and self.bora_cn_request_user_id != self.env.user
                and not self._is_cn_admin_user()):
            raise UserError(_('Only the original requester can update the approval request.'))
        return self._bora_open_cn_approval_wizard(is_update=True)

    def bora_action_request_cn_approval(self):
        """Re-open approval wizard when stuck in credit_note_approval_pending with no PM1."""
        self.ensure_one()
        return self._bora_open_cn_approval_wizard()

    # ─────────────────────────────────────────────────────────────────────────
    # Approve / Reject buttons (open reason wizard)
    # ─────────────────────────────────────────────────────────────────────────
    def bora_action_approve_cn(self):
        self.ensure_one()
        if self.state != 'credit_note_approval_pending':
            raise UserError(_("Can only approve credit notes in 'Credit Note Approval Pending' state."))
        view_id = self.env.ref(
            'bora_credit_note_approval.bora_credit_note_approval_reason_wizard_form'
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Approve Credit Note'),
            'res_model': 'bora.credit.note.approval.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'context': {
                'default_bora_cn_move_id': self.id,
                'default_bora_cn_action_type': 'approve',
            },
        }

    def bora_action_reject_cn(self):
        self.ensure_one()
        if self.state != 'credit_note_approval_pending':
            raise UserError(_("Can only reject credit notes in 'Credit Note Approval Pending' state."))
        view_id = self.env.ref(
            'bora_credit_note_approval.bora_credit_note_approval_reason_wizard_form'
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Credit Note'),
            'res_model': 'bora.credit.note.approval.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'context': {
                'default_bora_cn_move_id': self.id,
                'default_bora_cn_action_type': 'reject',
            },
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Approve logic (called from reason wizard)
    # ─────────────────────────────────────────────────────────────────────────
    def _bora_do_approve_cn_with_reason(self, reason, current_user):
        self.ensure_one()
        config = self._get_cn_approval_config()

        if current_user == self.bora_cn_pm1_id and not self.bora_cn_pm1_approved:
            self.bora_cn_pm1_approved = True
            self._mark_cn_activity_done(current_user, feedback=_('✅ Approved: %s') % reason)
            self.message_post(
                body=_('✅ Credit Note Approved\nApproved by: PM1 - %s\nReason: %s') % (
                    current_user.name, reason),
                message_type='notification', subtype_xmlid='mail.mt_note',
            )
            if config.is_dual_approval() and self.bora_cn_pm2_id:
                # Sequential: create PM2 activity now
                self._create_cn_approval_activity(self.bora_cn_pm2_id, 'Confirm')
                return
            # Single mode — complete
            self._bora_complete_cn_approval()

        elif current_user == self.bora_cn_pm2_id and not self.bora_cn_pm2_approved:
            if not self.bora_cn_pm1_approved:
                raise UserError(_('PM1 must approve first before PM2 can approve.'))
            self.bora_cn_pm2_approved = True
            self._mark_cn_activity_done(current_user, feedback=_('✅ Approved: %s') % reason)
            self.message_post(
                body=_('✅ Credit Note Approved\nApproved by: PM2 - %s\nReason: %s') % (
                    current_user.name, reason),
                message_type='notification', subtype_xmlid='mail.mt_note',
            )
            self._bora_complete_cn_approval()
        else:
            raise UserError(_('You are not authorized to approve this request or have already approved.'))

    def _bora_complete_cn_approval(self):
        """All required approvals received — restore state and call action_post automatically."""
        self.ensure_one()
        config = self._get_cn_approval_config()

        if self.bora_cn_pm1_id:
            self._mark_cn_activity_done(
                self.bora_cn_pm1_id, feedback=_('Approval complete — credit note confirmed'))
        if self.bora_cn_pm2_id:
            self._mark_cn_activity_done(
                self.bora_cn_pm2_id, feedback=_('Approval complete — credit note confirmed'))

        if config.is_dual_approval():
            approvers = '%s (PM1) and %s (PM2)' % (
                self.bora_cn_pm1_id.name, self.bora_cn_pm2_id.name)
        else:
            approvers = '%s (PM1)' % self.bora_cn_pm1_id.name

        # Restore to draft so action_post can run properly
        self.write({
            'state': 'draft',
            'bora_cn_approved': True,
        })

        self.message_post(
            body=_('🎉 Credit note approved by <strong>%(approvers)s</strong> and is being confirmed.') % {
                'approvers': approvers},
            message_type='notification', subtype_xmlid='mail.mt_note',
        )

        # Notify requester
        if self.bora_cn_request_user_id:
            self.env['bus.bus']._sendone(
                self.bora_cn_request_user_id.partner_id,
                'simple_notification',
                {
                    'type': 'success',
                    'title': _('Credit Note Approved & Confirmed: %s') % self.name,
                    'message': _('Your credit note has been approved and confirmed automatically.'),
                    'sticky': True,
                },
            )

        # bora_cn_approved=True ensures action_post skips our gate
        super(AccountMove, self).action_post()

    # ─────────────────────────────────────────────────────────────────────────
    # Reject logic (called from reason wizard)
    # ─────────────────────────────────────────────────────────────────────────
    def bora_cn_do_reject(self, reason):
        self.ensure_one()
        current_user = self.env.user
        if not ((self.bora_cn_pm1_id and current_user == self.bora_cn_pm1_id) or
                (self.bora_cn_pm2_id and current_user == self.bora_cn_pm2_id)):
            raise UserError(_('You are not authorized to reject this request.'))
        if (self.bora_cn_pm2_id and current_user == self.bora_cn_pm2_id
                and not self.bora_cn_pm1_approved):
            raise UserError(_('PM1 must approve first before PM2 can reject.'))

        pm_role = ('PM1 - %s' % current_user.name
                   if current_user == self.bora_cn_pm1_id
                   else 'PM2 - %s' % current_user.name)

        self._mark_cn_activity_done(current_user, feedback=_('❌ Rejected: %s') % reason)
        self._bora_cancel_cn_activities()

        pre_state = self.bora_cn_pre_approval_state or 'draft'
        self.write({
            'state': pre_state,
            'bora_cn_pm1_id': False,
            'bora_cn_pm2_id': False,
            'bora_cn_pm1_approved': False,
            'bora_cn_pm2_approved': False,
            'bora_cn_request_user_id': False,
            'bora_cn_request_date': False,
            'bora_cn_pre_approval_state': False,
        })
        self.message_post(
            body=_('❌ Credit Note Rejected\nRejected by: %s\nReason: %s') % (pm_role, reason),
            message_type='notification', subtype_xmlid='mail.mt_note',
        )
        if self.bora_cn_request_user_id:
            self.env['bus.bus']._sendone(
                self.bora_cn_request_user_id.partner_id,
                'simple_notification',
                {
                    'type': 'danger',
                    'title': _('Credit Note Rejected: %s') % self.name,
                    'message': _('Your credit note approval request was rejected.'),
                    'sticky': True,
                },
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Activity helpers
    # ─────────────────────────────────────────────────────────────────────────
    def _create_cn_approval_activity(self, user, keyword='Confirm'):
        self.ensure_one()
        self.activity_schedule(
            act_type_xmlid='bora_credit_note_approval.mail_activity_data_cn_approval',
            summary=_('Credit Note Approval (%s): %s') % (keyword, self.name),
            note=_('Please review this credit note approval request.'),
            user_id=user.id,
            date_deadline=fields.Date.context_today(self),
        )

    def _mark_cn_activity_done(self, user, feedback=''):
        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', self.id),
            ('user_id', '=', user.id),
            ('summary', 'ilike', 'Credit Note Approval'),
        ])
        for act in activities:
            act.action_feedback(feedback=feedback)

    def _bora_cancel_cn_activities(self):
        """Silently cancel all credit-note-approval activities."""
        self.ensure_one()
        pm_ids = list(filter(None, [
            self.bora_cn_pm1_id.id if self.bora_cn_pm1_id else False,
            self.bora_cn_pm2_id.id if self.bora_cn_pm2_id else False,
        ]))
        domain = [
            ('res_model', '=', 'account.move'),
            ('res_id', '=', self.id),
            ('active', '=', True),
            ('summary', 'ilike', 'Credit Note Approval'),
        ]
        if pm_ids:
            domain.append(('user_id', 'in', pm_ids))
        self.env['mail.activity'].search(domain).sudo().unlink()
