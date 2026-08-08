# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ── New state value ───────────────────────────────────────────────────────
    state = fields.Selection(
        selection_add=[
            ('invoice_approval_pending', 'Invoice Approval Pending'),
        ],
        ondelete={'invoice_approval_pending': lambda recs: recs.write({'state': 'draft'})},
    )

    bora_inv_pre_approval_state = fields.Char(copy=False)
    bora_inv_approved = fields.Boolean(default=False, copy=False, tracking=True)

    # True = local sale (India customer), False = export sale
    bora_inv_is_local_sale = fields.Boolean(
        string='Is Local Sale', copy=False,
        help='Set at approval request time: True if customer is from India.')

    # ── Approval tracking fields ──────────────────────────────────────────────
    bora_inv_pm1_id = fields.Many2one('res.users', string='Invoice Approver PM1', copy=False)
    bora_inv_pm2_id = fields.Many2one('res.users', string='Invoice Approver PM2', copy=False)
    bora_inv_pm1_approved = fields.Boolean(default=False, copy=False, tracking=True)
    bora_inv_pm2_approved = fields.Boolean(default=False, copy=False, tracking=True)
    bora_inv_request_reason = fields.Text(string='Request Reason', copy=False)
    bora_inv_request_user_id = fields.Many2one('res.users', string='Requested By', copy=False)
    bora_inv_request_date = fields.Datetime(string='Request Date', copy=False)

    # ── Computed UI fields ────────────────────────────────────────────────────
    bora_is_inv_pm_user = fields.Boolean(compute='_compute_bora_inv_pm_user')
    bora_is_inv_admin = fields.Boolean(compute='_compute_bora_inv_admin')
    bora_show_inv_approve_button = fields.Boolean(compute='_compute_inv_button_visibility')
    bora_show_inv_reject_button = fields.Boolean(compute='_compute_inv_button_visibility')
    bora_show_inv_update_button = fields.Boolean(compute='_compute_inv_button_visibility')

    # ── Sale type label (for display) ─────────────────────────────────────────
    bora_inv_sale_type_label = fields.Char(
        compute='_compute_inv_sale_type_label', string='Sale Type')

    @api.depends('bora_inv_is_local_sale', 'state')
    def _compute_inv_sale_type_label(self):
        for rec in self:
            if rec.state == 'invoice_approval_pending' or rec.bora_inv_pm1_id:
                rec.bora_inv_sale_type_label = _('Local Sale') if rec.bora_inv_is_local_sale else _('Export Sale')
            else:
                rec.bora_inv_sale_type_label = False

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────
    def _is_customer_invoice(self):
        """True for customer invoices that are NOT debit notes."""
        return self.move_type == 'out_invoice' and not self.debit_origin_id

    def _is_local_sale(self):
        """True if the customer's country code is 'IN' (India)."""
        return self.partner_id.country_id.code == 'IN'

    def _get_inv_approval_config(self):
        config = self.env['bora.invoice.approval.config'].get_config(company=self.company_id)
        if not config:
            raise UserError(_(
                'No active invoice approval configuration found for company "%s". '
                'Please configure approvers in Accounting > Configuration > Invoice Approvers.'
            ) % self.company_id.name)
        return config

    def _has_inv_approval_config(self):
        return bool(self.env['bora.invoice.approval.config'].get_config(company=self.company_id))

    def _is_inv_admin_user(self):
        return self.env.user._is_admin()

    # ─────────────────────────────────────────────────────────────────────────
    # Computed fields
    # ─────────────────────────────────────────────────────────────────────────
    @api.depends_context('uid')
    def _compute_bora_inv_admin(self):
        is_admin = self._is_inv_admin_user()
        for rec in self:
            rec.bora_is_inv_admin = is_admin

    @api.depends_context('uid')
    def _compute_bora_inv_pm_user(self):
        for rec in self:
            if rec._has_inv_approval_config():
                config = rec._get_inv_approval_config()
                rec.bora_is_inv_pm_user = self.env.user in config.get_all_pm_users()
            else:
                rec.bora_is_inv_pm_user = False

    @api.depends(
        'state',
        'bora_is_inv_pm_user',
        'bora_inv_pm1_id', 'bora_inv_pm2_id',
        'bora_inv_pm1_approved', 'bora_inv_pm2_approved',
        'bora_inv_request_user_id',
    )
    @api.depends_context('uid')
    def _compute_inv_button_visibility(self):
        current_user = self.env.user
        for rec in self:
            rec.bora_show_inv_approve_button = False
            rec.bora_show_inv_reject_button = False
            rec.bora_show_inv_update_button = False

            is_admin = rec._is_inv_admin_user()
            is_pm = rec.bora_is_inv_pm_user

            if is_admin:
                if rec.state == 'invoice_approval_pending':
                    rec.bora_show_inv_approve_button = True
                    rec.bora_show_inv_reject_button = True
                continue

            if not rec._has_inv_approval_config():
                continue

            if not is_pm:
                if (rec.state == 'invoice_approval_pending'
                        and rec.bora_inv_request_user_id == current_user):
                    rec.bora_show_inv_update_button = True

            if is_pm and rec.state == 'invoice_approval_pending':
                if (rec.bora_inv_pm1_id and current_user == rec.bora_inv_pm1_id
                        and not rec.bora_inv_pm1_approved):
                    rec.bora_show_inv_approve_button = True
                    rec.bora_show_inv_reject_button = True
                elif (rec.bora_inv_pm2_id and current_user == rec.bora_inv_pm2_id
                      and rec.bora_inv_pm1_approved and not rec.bora_inv_pm2_approved):
                    rec.bora_show_inv_approve_button = True
                    rec.bora_show_inv_reject_button = True

    # ─────────────────────────────────────────────────────────────────────────
    # Override action_post (Confirm button for customer invoices)
    # ─────────────────────────────────────────────────────────────────────────
    def action_post(self):
        """Intercept Confirm for customer invoices (out_invoice, no debit_origin_id)."""
        # Validate invoice date up-front
        for move in self:
            if move._is_customer_invoice() and not move.invoice_date:
                raise UserError(_(
                    'The Invoice date is required to validate this document. '
                    'Please set the Invoice Date before confirming.'
                ))

        inv_needing_approval = self.env['account.move']
        inv_can_proceed = self.env['account.move']

        for move in self:
            if (move._is_customer_invoice()
                    and move.state == 'draft'
                    and move._has_inv_approval_config()
                    and not move._is_inv_admin_user()
                    and not move.bora_inv_approved):
                config = move._get_inv_approval_config()
                if self.env.user not in config.get_all_pm_users():
                    inv_needing_approval |= move
                    continue
            inv_can_proceed |= move

        for move in inv_needing_approval:
            move.write({
                'bora_inv_pre_approval_state': 'draft',
                'state': 'invoice_approval_pending',
                'bora_inv_is_local_sale': move._is_local_sale(),
            })

        if inv_can_proceed:
            super(AccountMove, inv_can_proceed).action_post()

        if inv_needing_approval:
            return inv_needing_approval[0]._bora_open_inv_approval_wizard()

        return True

    def _bora_open_inv_approval_wizard(self, is_update=False):
        view_id = self.env.ref(
            'bora_invoice_approval.bora_invoice_approval_request_wizard_form'
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Update Invoice Approvers') if is_update else _('Request for Approval'),
            'res_model': 'bora.invoice.approval.request.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'context': {
                'default_bora_inv_move_id': self.id,
                'bora_inv_is_update': is_update,
                'default_bora_inv_is_update_mode': is_update,
            },
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Workflow: submit for approval
    # ─────────────────────────────────────────────────────────────────────────
    def bora_inv_do_request_approval(self, pm1_user, pm2_user=None, reason=None):
        """Called from request wizard after approvers are selected."""
        self.ensure_one()
        if self.state not in ('draft', 'invoice_approval_pending'):
            raise UserError(_('Approval can only be requested for invoices in Draft state.'))
        if not pm1_user:
            raise UserError(_('Approver 1 must be selected.'))

        config = self._get_inv_approval_config()
        is_local = self.bora_inv_is_local_sale
        if config.is_dual_approval(is_local) and not pm2_user:
            raise UserError(_('Approver 2 is required for dual approval mode.'))

        vals = {
            'state': 'invoice_approval_pending',
            'bora_inv_pm1_id': pm1_user.id,
            'bora_inv_pm2_id': pm2_user.id if pm2_user else False,
            'bora_inv_pm1_approved': False,
            'bora_inv_pm2_approved': False,
            'bora_inv_request_reason': reason or '',
            'bora_inv_request_user_id': self.env.user.id,
            'bora_inv_request_date': fields.Datetime.now(),
        }
        if not self.bora_inv_pre_approval_state:
            vals['bora_inv_pre_approval_state'] = 'draft'
        self.write(vals)

        partner_ids = [pm1_user.partner_id.id]
        if pm2_user:
            partner_ids.append(pm2_user.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)

        sale_type = _('Local') if is_local else _('Export')
        if config.is_dual_approval(is_local):
            msg = _('[%s] Invoice approval request submitted by <strong>%s</strong>. '
                    'Waiting for <strong>%s</strong> (PM1) and <strong>%s</strong> (PM2).') % (
                sale_type, self.env.user.name, pm1_user.name, pm2_user.name if pm2_user else '')
        else:
            msg = _('[%s] Invoice approval request submitted by <strong>%s</strong>. '
                    'Waiting for <strong>%s</strong> (PM1).') % (
                sale_type, self.env.user.name, pm1_user.name)

        if reason:
            msg += _('<br/>Reason: %s') % reason
        self.message_post(body=msg, message_type='notification', subtype_xmlid='mail.mt_note')
        self._create_inv_approval_activity(pm1_user, 'Confirm')

    # ─────────────────────────────────────────────────────────────────────────
    # Update Approvers
    # ─────────────────────────────────────────────────────────────────────────
    def action_update_inv_approvers(self):
        self.ensure_one()
        if self.state != 'invoice_approval_pending':
            raise UserError(_(
                "Update Approvers is only available while the invoice is in "
                "'Invoice Approval Pending' state."
            ))
        if (self.bora_inv_request_user_id
                and self.bora_inv_request_user_id != self.env.user
                and not self._is_inv_admin_user()):
            raise UserError(_('Only the original requester can update the approval request.'))
        return self._bora_open_inv_approval_wizard(is_update=True)

    def bora_action_request_inv_approval(self):
        """Re-open wizard when stuck in invoice_approval_pending with no PM1."""
        self.ensure_one()
        return self._bora_open_inv_approval_wizard()

    # ─────────────────────────────────────────────────────────────────────────
    # Approve / Reject (open reason wizard)
    # ─────────────────────────────────────────────────────────────────────────
    def bora_action_approve_inv(self):
        self.ensure_one()
        if self.state != 'invoice_approval_pending':
            raise UserError(_("Can only approve invoices in 'Invoice Approval Pending' state."))
        view_id = self.env.ref('bora_invoice_approval.bora_invoice_approval_reason_wizard_form')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Approve Invoice'),
            'res_model': 'bora.invoice.approval.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'context': {
                'default_bora_inv_move_id': self.id,
                'default_bora_inv_action_type': 'approve',
            },
        }

    def bora_action_reject_inv(self):
        self.ensure_one()
        if self.state != 'invoice_approval_pending':
            raise UserError(_("Can only reject invoices in 'Invoice Approval Pending' state."))
        view_id = self.env.ref('bora_invoice_approval.bora_invoice_approval_reason_wizard_form')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Invoice'),
            'res_model': 'bora.invoice.approval.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'context': {
                'default_bora_inv_move_id': self.id,
                'default_bora_inv_action_type': 'reject',
            },
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Approve logic
    # ─────────────────────────────────────────────────────────────────────────
    def _bora_do_approve_inv_with_reason(self, reason, current_user):
        self.ensure_one()
        config = self._get_inv_approval_config()
        is_local = self.bora_inv_is_local_sale

        if current_user == self.bora_inv_pm1_id and not self.bora_inv_pm1_approved:
            self.bora_inv_pm1_approved = True
            self._mark_inv_activity_done(current_user, feedback=_('✅ Approved: %s') % reason)
            self.message_post(
                body=_('✅ Invoice Approved\nApproved by: PM1 - %s\nReason: %s') % (
                    current_user.name, reason),
                message_type='notification', subtype_xmlid='mail.mt_note',
            )
            if config.is_dual_approval(is_local) and self.bora_inv_pm2_id:
                self._create_inv_approval_activity(self.bora_inv_pm2_id, 'Confirm')
                return
            self._bora_complete_inv_approval()

        elif current_user == self.bora_inv_pm2_id and not self.bora_inv_pm2_approved:
            if not self.bora_inv_pm1_approved:
                raise UserError(_('PM1 must approve first before PM2 can approve.'))
            self.bora_inv_pm2_approved = True
            self._mark_inv_activity_done(current_user, feedback=_('✅ Approved: %s') % reason)
            self.message_post(
                body=_('✅ Invoice Approved\nApproved by: PM2 - %s\nReason: %s') % (
                    current_user.name, reason),
                message_type='notification', subtype_xmlid='mail.mt_note',
            )
            self._bora_complete_inv_approval()
        else:
            raise UserError(_('You are not authorized to approve this request or have already approved.'))

    def _bora_complete_inv_approval(self):
        """All required approvals received — restore to draft and auto-confirm."""
        self.ensure_one()
        config = self._get_inv_approval_config()
        is_local = self.bora_inv_is_local_sale

        if self.bora_inv_pm1_id:
            self._mark_inv_activity_done(
                self.bora_inv_pm1_id, feedback=_('Approval complete — invoice confirmed'))
        if self.bora_inv_pm2_id:
            self._mark_inv_activity_done(
                self.bora_inv_pm2_id, feedback=_('Approval complete — invoice confirmed'))

        if config.is_dual_approval(is_local):
            approvers = '%s (PM1) and %s (PM2)' % (
                self.bora_inv_pm1_id.name, self.bora_inv_pm2_id.name)
        else:
            approvers = '%s (PM1)' % self.bora_inv_pm1_id.name

        sale_type = _('Local') if is_local else _('Export')
        self.write({'state': 'draft', 'bora_inv_approved': True})
        self.message_post(
            body=_('🎉 [%(sale_type)s] Invoice approved by <strong>%(approvers)s</strong> and is being confirmed automatically.') % {
                'sale_type': sale_type, 'approvers': approvers},
            message_type='notification', subtype_xmlid='mail.mt_note',
        )

        if self.bora_inv_request_user_id:
            self.env['bus.bus']._sendone(
                self.bora_inv_request_user_id.partner_id,
                'simple_notification',
                {
                    'type': 'success',
                    'title': _('Invoice Approved & Confirmed: %s') % self.name,
                    'message': _('Your invoice has been approved and confirmed automatically.'),
                    'sticky': True,
                },
            )

        # bora_inv_approved=True skips our gate on the next call
        super(AccountMove, self).action_post()

    # ─────────────────────────────────────────────────────────────────────────
    # Reject logic
    # ─────────────────────────────────────────────────────────────────────────
    def bora_inv_do_reject(self, reason):
        self.ensure_one()
        current_user = self.env.user
        if not ((self.bora_inv_pm1_id and current_user == self.bora_inv_pm1_id) or
                (self.bora_inv_pm2_id and current_user == self.bora_inv_pm2_id)):
            raise UserError(_('You are not authorized to reject this request.'))
        if (self.bora_inv_pm2_id and current_user == self.bora_inv_pm2_id
                and not self.bora_inv_pm1_approved):
            raise UserError(_('PM1 must approve first before PM2 can reject.'))

        pm_role = ('PM1 - %s' % current_user.name
                   if current_user == self.bora_inv_pm1_id
                   else 'PM2 - %s' % current_user.name)

        self._mark_inv_activity_done(current_user, feedback=_('❌ Rejected: %s') % reason)
        self._bora_cancel_inv_activities()

        pre_state = self.bora_inv_pre_approval_state or 'draft'
        self.write({
            'state': pre_state,
            'bora_inv_pm1_id': False,
            'bora_inv_pm2_id': False,
            'bora_inv_pm1_approved': False,
            'bora_inv_pm2_approved': False,
            'bora_inv_request_user_id': False,
            'bora_inv_request_date': False,
            'bora_inv_pre_approval_state': False,
        })
        self.message_post(
            body=_('❌ Invoice Rejected\nRejected by: %s\nReason: %s') % (pm_role, reason),
            message_type='notification', subtype_xmlid='mail.mt_note',
        )
        if self.bora_inv_request_user_id:
            self.env['bus.bus']._sendone(
                self.bora_inv_request_user_id.partner_id,
                'simple_notification',
                {
                    'type': 'danger',
                    'title': _('Invoice Rejected: %s') % self.name,
                    'message': _('Your invoice approval request was rejected.'),
                    'sticky': True,
                },
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Activity helpers
    # ─────────────────────────────────────────────────────────────────────────
    def _create_inv_approval_activity(self, user, keyword='Confirm'):
        self.ensure_one()
        self.activity_schedule(
            act_type_xmlid='bora_invoice_approval.mail_activity_data_inv_approval',
            summary=_('Invoice Approval (%s): %s') % (keyword, self.name),
            note=_('Please review this invoice approval request.'),
            user_id=user.id,
            date_deadline=fields.Date.context_today(self),
        )

    def _mark_inv_activity_done(self, user, feedback=''):
        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', self.id),
            ('user_id', '=', user.id),
            ('summary', 'ilike', 'Invoice Approval'),
        ])
        for act in activities:
            act.action_feedback(feedback=feedback)

    def _bora_cancel_inv_activities(self):
        self.ensure_one()
        pm_ids = list(filter(None, [
            self.bora_inv_pm1_id.id if self.bora_inv_pm1_id else False,
            self.bora_inv_pm2_id.id if self.bora_inv_pm2_id else False,
        ]))
        domain = [
            ('res_model', '=', 'account.move'),
            ('res_id', '=', self.id),
            ('active', '=', True),
            ('summary', 'ilike', 'Invoice Approval'),
        ]
        if pm_ids:
            domain.append(('user_id', 'in', pm_ids))
        self.env['mail.activity'].search(domain).sudo().unlink()
