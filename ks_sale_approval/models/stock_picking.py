# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # -------------------------------------------------------------------------
    # Extend state field — same pattern as sale.order
    # -------------------------------------------------------------------------
    state = fields.Selection(
        selection_add=[
            ('approval_pending', 'Approval Pending'),
        ],
        ondelete={'approval_pending': lambda recs: recs.write({'state': 'draft'})},
    )

    # Stores the picking state before entering approval_pending so we can restore it
    ks_pre_approval_state = fields.Char(copy=False)

    # True after all required PMs have approved — lets the requester bypass the approval gate
    ks_delivery_approved = fields.Boolean(default=False, copy=False, tracking=True)

    # ---- Approval tracking fields (mirror sale.order confirm fields) ----
    ks_validate_pm1_id = fields.Many2one('res.users', string='Approver PM1', copy=False)
    ks_validate_pm2_id = fields.Many2one('res.users', string='Approver PM2', copy=False)
    ks_validate_pm1_approved = fields.Boolean(default=False, copy=False, tracking=True)
    ks_validate_pm2_approved = fields.Boolean(default=False, copy=False, tracking=True)
    ks_validate_request_reason = fields.Text(string='Request Reason', copy=False)
    ks_validate_request_user_id = fields.Many2one('res.users', string='Requested By', copy=False)
    ks_validate_request_date = fields.Datetime(string='Request Date', copy=False)

    # ---- Computed UI fields ----
    ks_is_delivery_pm_user = fields.Boolean(compute='_compute_ks_delivery_pm_user')
    ks_is_delivery_admin = fields.Boolean(compute='_compute_ks_delivery_admin')
    ks_is_delivery_dual_approval = fields.Boolean(compute='_compute_ks_delivery_dual_approval')

    ks_show_delivery_approve_button = fields.Boolean(compute='_compute_delivery_button_visibility')
    ks_show_delivery_reject_button = fields.Boolean(compute='_compute_delivery_button_visibility')
    ks_show_delivery_update_button = fields.Boolean(compute='_compute_delivery_button_visibility')

    # -------------------------------------------------------------------------
    # Config helpers
    # -------------------------------------------------------------------------
    def _get_delivery_approval_config(self):
        config = self.env['ks.delivery.approval.config'].get_config()
        if not config:
            raise UserError(_(
                'No active delivery approval configuration found. '
                'Please configure approvers in Inventory > Configuration > Delivery Approval Configuration.'
            ))
        return config

    def _has_delivery_approval_config(self):
        return bool(self.env['ks.delivery.approval.config'].get_config())

    def _is_delivery_admin_user(self):
        return bool(self.env.user.sudo().is_custom_admin)

    # -------------------------------------------------------------------------
    # Computed fields
    # -------------------------------------------------------------------------
    @api.depends_context('uid')
    def _compute_ks_delivery_admin(self):
        is_admin = self._is_delivery_admin_user()
        for rec in self:
            rec.ks_is_delivery_admin = is_admin

    @api.depends_context('uid')
    def _compute_ks_delivery_pm_user(self):
        for rec in self:
            if rec._has_delivery_approval_config():
                config = rec._get_delivery_approval_config()
                rec.ks_is_delivery_pm_user = self.env.user in config.get_all_pm_users()
            else:
                rec.ks_is_delivery_pm_user = False

    @api.depends('state')
    def _compute_ks_delivery_dual_approval(self):
        for rec in self:
            if rec._has_delivery_approval_config():
                rec.ks_is_delivery_dual_approval = rec._get_delivery_approval_config().is_dual_approval()
            else:
                rec.ks_is_delivery_dual_approval = False

    @api.depends(
        'state',
        'ks_is_delivery_pm_user',
        'ks_validate_pm1_id', 'ks_validate_pm2_id',
        'ks_validate_pm1_approved', 'ks_validate_pm2_approved',
        'ks_validate_request_user_id',
    )
    @api.depends_context('uid')
    def _compute_delivery_button_visibility(self):
        current_user = self.env.user
        for rec in self:
            rec.ks_show_delivery_approve_button = False
            rec.ks_show_delivery_reject_button = False
            rec.ks_show_delivery_update_button = False

            is_admin = rec._is_delivery_admin_user()
            is_pm = rec.ks_is_delivery_pm_user

            if is_admin:
                if rec.state == 'approval_pending':
                    rec.ks_show_delivery_approve_button = True
                    rec.ks_show_delivery_reject_button = True
                continue

            if not rec._has_delivery_approval_config():
                continue

            if not is_pm:
                # Original requester can update while approval is pending
                if rec.state == 'approval_pending' and rec.ks_validate_request_user_id == current_user:
                    rec.ks_show_delivery_update_button = True

            if is_pm and rec.state == 'approval_pending':
                # PM1 can approve if not already approved
                if (rec.ks_validate_pm1_id and current_user == rec.ks_validate_pm1_id
                        and not rec.ks_validate_pm1_approved):
                    rec.ks_show_delivery_approve_button = True
                    rec.ks_show_delivery_reject_button = True
                # PM2 can approve only after PM1 (sequential)
                elif (rec.ks_validate_pm2_id and current_user == rec.ks_validate_pm2_id
                      and rec.ks_validate_pm1_approved and not rec.ks_validate_pm2_approved):
                    rec.ks_show_delivery_approve_button = True
                    rec.ks_show_delivery_reject_button = True

    # -------------------------------------------------------------------------
    # Override button_validate + _action_done
    # Flow:
    #   1. button_validate() calls super() — Odoo runs all its own dialogs
    #      (immediate-transfer wizard, serial/lot assignment, backorder) first.
    #   2. When all dialogs are resolved, Odoo calls _action_done().
    #      _action_done() intercepts and sets approval_pending, then returns
    #      the approval wizard action so it opens right after every dialog.
    #   3. button_validate() also checks for approval_pending as a fallback
    #      (covers any path where _action_done's return value is not propagated).
    #   4. After PM approval, ks_delivery_approved=True. User clicks Validate
    #      again — _action_done() skips our gate → super()._action_done() runs
    #      → delivery is done.
    # -------------------------------------------------------------------------
    def button_validate(self):
        result = super().button_validate()

        # result is a dict in two cases:
        #   a) Odoo dialog (immediate-transfer / backorder) — pass through
        #   b) Our approval wizard returned from _action_done — pass through
        if isinstance(result, dict):
            return result

        # Fallback: _action_done set approval_pending but its return value was
        # lost somewhere in the call chain.
        pending = self.filtered(
            lambda p: p.state == 'approval_pending' and not p.ks_validate_pm1_id
        )
        if pending:
            return pending[0]._ks_open_delivery_approval_wizard()

        return result

    def _action_done(self, **kwargs):
        """Intercept AFTER all Odoo quantity/backorder dialogs for deliveries needing approval."""
        needs_approval = self.env['stock.picking']
        can_proceed = self.env['stock.picking']

        for picking in self:
            if (picking.picking_type_code == 'outgoing'
                    and picking.state == 'assigned'
                    and picking._has_delivery_approval_config()
                    and not picking._is_delivery_admin_user()
                    and not picking.ks_delivery_approved):
                config = picking._get_delivery_approval_config()
                if self.env.user not in config.get_all_pm_users():
                    needs_approval |= picking
                    continue
            can_proceed |= picking

        # Before showing the approval wizard, validate that all tracked moves
        # have lot/serial numbers assigned — same checks Odoo runs inside
        # super()._action_done(). Raising here gives the error BEFORE approval
        # so the user can fix it in one go.
        for picking in needs_approval:
            picking._ks_check_lots_before_approval()

        # Set approval_pending for pickings that need it (wizard will fill pm1/pm2)
        for picking in needs_approval:
            picking.write({
                'ks_pre_approval_state': 'assigned',
                'state': 'approval_pending',
            })

        if can_proceed:
            super(StockPicking, can_proceed)._action_done(**kwargs)

        # Return the approval wizard action so it opens after every dialog path
        # (immediate-transfer, backorder, or direct validate).
        if needs_approval:
            return needs_approval[0]._ks_open_delivery_approval_wizard()

        return True

    def _ks_check_lots_before_approval(self):
        """Raise UserError if any tracked move is missing lot/serial numbers.
        Mirrors the check inside stock.move._action_done so errors surface
        before the approval wizard instead of after.
        """
        self.ensure_one()
        for move in self.move_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
            if move.product_id.tracking == 'none':
                continue
            missing = False
            if not move.move_line_ids:
                missing = True
            else:
                for ml in move.move_line_ids:
                    if not ml.lot_id and not ml.lot_name:
                        missing = True
                        break
            if missing:
                raise UserError(
                    _('You need to supply a Lot/Serial number for products %s.')
                    % move.product_id.display_name
                )

    def _ks_open_delivery_approval_wizard(self, is_update=False):
        view_id = self.env.ref('ks_sale_approval.ks_delivery_approval_request_wizard_form')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Update Delivery Approvals') if is_update else _('Request for Approval'),
            'res_model': 'ks.delivery.approval.request.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'context': {
                'default_ks_picking_id': self.id,
                'ks_is_update': is_update,
                'default_ks_is_update_mode': is_update,
                'default_ks_approver1_user': self.ks_validate_pm1_id.id or False if is_update else False,
                'default_ks_approver2_user': self.ks_validate_pm2_id.id or False if is_update else False,
            },
        }

    # -------------------------------------------------------------------------
    # Workflow: send to approval_pending
    # -------------------------------------------------------------------------
    def ks_do_request_delivery_approval(self, pm1_user, pm2_user=None, reason=None):
        """Normal user submits delivery for approval. Called from wizard OK."""
        self.ensure_one()
        if self.state not in ('assigned', 'approval_pending'):
            raise UserError(_('Approval can only be requested for deliveries in Ready state.'))
        if not pm1_user:
            raise UserError(_('Approver 1 must be selected.'))

        config = self._get_delivery_approval_config()
        if config.is_dual_approval() and not pm2_user:
            raise UserError(_('Approver 2 is required for dual approval mode.'))

        # State is already approval_pending (set by _action_done intercept).
        # Only set ks_pre_approval_state if not already set.
        vals = {
            'state': 'approval_pending',
            'ks_validate_pm1_id': pm1_user.id,
        }
        if not self.ks_pre_approval_state:
            vals['ks_pre_approval_state'] = 'assigned'
        self.write({
            **vals,
            'ks_validate_pm2_id': pm2_user.id if pm2_user else False,
            'ks_validate_pm1_approved': False,
            'ks_validate_pm2_approved': False,
            'ks_validate_request_reason': reason or '',
            'ks_validate_request_user_id': self.env.user.id,
            'ks_validate_request_date': fields.Datetime.now(),
        })

        # Subscribe PMs to chatter
        partner_ids = [pm1_user.partner_id.id]
        if pm2_user:
            partner_ids.append(pm2_user.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)

        if config.is_dual_approval():
            msg = _('Validation approval request submitted by <strong>%s</strong>. '
                    'Waiting for approval from <strong>%s</strong> (PM1) and <strong>%s</strong> (PM2).') % (
                self.env.user.name, pm1_user.name, pm2_user.name if pm2_user else '')
        else:
            msg = _('Validation approval request submitted by <strong>%s</strong>. '
                    'Waiting for approval from <strong>%s</strong> (PM1).') % (
                self.env.user.name, pm1_user.name)

        if reason:
            msg += _('<br/>Reason: %s') % reason

        self.message_post(body=msg, message_type='notification', subtype_xmlid='mail.mt_note')

        # Create activity for PM1 (PM2 activity created after PM1 approves — sequential)
        self._create_delivery_approval_activity(pm1_user, 'Validate')

    # -------------------------------------------------------------------------
    # Update Approvals
    # -------------------------------------------------------------------------
    def action_update_delivery_approvals(self):
        """Requester updates approvers while pending. Cleanup only on wizard OK."""
        self.ensure_one()
        if self.state != 'approval_pending':
            raise UserError(_("Update Approvals is only available while the delivery is in 'Approval Pending' state."))
        if self.ks_validate_request_user_id and self.ks_validate_request_user_id != self.env.user:
            if not self._is_delivery_admin_user():
                raise UserError(_('Only the original requester can update the approval request.'))
        return self._ks_open_delivery_approval_wizard(is_update=True)

    def ks_action_request_delivery_approval(self):
        """Re-open approval wizard when stuck in approval_pending with no PM1 (e.g. user closed modal with X)."""
        self.ensure_one()
        return self._ks_open_delivery_approval_wizard()

    # -------------------------------------------------------------------------
    # Approve / Reject buttons (open reason wizard)
    # -------------------------------------------------------------------------
    def ks_action_approve_delivery(self):
        self.ensure_one()
        if self.state != 'approval_pending':
            raise UserError(_("Can only approve deliveries in 'Approval Pending' state."))
        view_id = self.env.ref('ks_sale_approval.ks_delivery_approval_reason_wizard_form')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Approve Delivery Validation'),
            'res_model': 'ks.delivery.approval.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'context': {'default_ks_picking_id': self.id, 'default_ks_action_type': 'approve'},
        }

    def ks_action_reject_delivery(self):
        self.ensure_one()
        if self.state != 'approval_pending':
            raise UserError(_("Can only reject deliveries in 'Approval Pending' state."))
        view_id = self.env.ref('ks_sale_approval.ks_delivery_approval_reason_wizard_form')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Delivery Validation'),
            'res_model': 'ks.delivery.approval.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'context': {'default_ks_picking_id': self.id, 'default_ks_action_type': 'reject'},
        }

    # -------------------------------------------------------------------------
    # Approve logic (called from reason wizard)
    # -------------------------------------------------------------------------
    def _ks_do_approve_delivery_with_reason(self, reason, current_user):
        self.ensure_one()
        config = self._get_delivery_approval_config()

        if current_user == self.ks_validate_pm1_id and not self.ks_validate_pm1_approved:
            self.ks_validate_pm1_approved = True
            self._mark_delivery_activity_done(current_user, feedback=_('✅ Approved: %s') % reason)
            self.message_post(
                body=_('✅ Validation Approved\nApproved by: PM1 - %s\nReason: %s') % (current_user.name, reason),
                message_type='notification', subtype_xmlid='mail.mt_note',
            )
            if config.is_dual_approval() and self.ks_validate_pm2_id:
                # Sequential: now create PM2 activity
                self._create_delivery_approval_activity(self.ks_validate_pm2_id, 'Validate')
                return
            # Single mode — complete
            self._ks_complete_delivery_approval()

        elif current_user == self.ks_validate_pm2_id and not self.ks_validate_pm2_approved:
            if not self.ks_validate_pm1_approved:
                raise UserError(_('PM1 must approve first before PM2 can approve.'))
            self.ks_validate_pm2_approved = True
            self._mark_delivery_activity_done(current_user, feedback=_('✅ Approved: %s') % reason)
            self.message_post(
                body=_('✅ Validation Approved\nApproved by: PM2 - %s\nReason: %s') % (current_user.name, reason),
                message_type='notification', subtype_xmlid='mail.mt_note',
            )
            self._ks_complete_delivery_approval()
        else:
            raise UserError(_('You are not authorized to approve this request or have already approved.'))

    def _ks_complete_delivery_approval(self):
        """All required approvals received — directly complete the delivery.

        Sets ks_delivery_approved = True, restores state to 'assigned', then
        calls _action_done() so the delivery goes to Done automatically without
        requiring a second Validate click from the user.
        """
        self.ensure_one()
        config = self._get_delivery_approval_config()

        # Mark all remaining activities done
        if self.ks_validate_pm1_id:
            self._mark_delivery_activity_done(self.ks_validate_pm1_id,
                                               feedback=_('Approval complete — delivery validated'))
        if self.ks_validate_pm2_id:
            self._mark_delivery_activity_done(self.ks_validate_pm2_id,
                                               feedback=_('Approval complete — delivery validated'))

        if config.is_dual_approval():
            approvers = '%s (PM1) and %s (PM2)' % (self.ks_validate_pm1_id.name, self.ks_validate_pm2_id.name)
        else:
            approvers = '%s (PM1)' % self.ks_validate_pm1_id.name

        # Restore state to 'assigned' and set approved flag so _action_done
        # skips our approval gate and calls super()._action_done() directly.
        pre_state = self.ks_pre_approval_state or 'assigned'
        self.write({
            'state': pre_state,
            'ks_delivery_approved': True,
        })

        self.message_post(
            body=_('🎉 Delivery validated and approved by <strong>%(approvers)s</strong>.') % {
                'approvers': approvers},
            message_type='notification', subtype_xmlid='mail.mt_note',
        )

        # Notify requester
        if self.ks_validate_request_user_id:
            self.env['bus.bus']._sendone(
                self.ks_validate_request_user_id.partner_id,
                'simple_notification',
                {
                    'type': 'success',
                    'title': _('Delivery Approved & Done: %s') % self.name,
                    'message': _('Your delivery has been approved and marked as done.'),
                    'sticky': True,
                },
            )

        # Directly complete the delivery — ks_delivery_approved=True ensures
        # _action_done() skips our gate and calls super()._action_done().
        self._action_done()

    # -------------------------------------------------------------------------
    # Reject logic (called from reason wizard)
    # -------------------------------------------------------------------------
    def ks_do_reject_delivery(self, reason):
        self.ensure_one()
        current_user = self.env.user
        if not ((self.ks_validate_pm1_id and current_user == self.ks_validate_pm1_id) or
                (self.ks_validate_pm2_id and current_user == self.ks_validate_pm2_id)):
            raise UserError(_('You are not authorized to reject this request.'))
        if (self.ks_validate_pm2_id and current_user == self.ks_validate_pm2_id
                and not self.ks_validate_pm1_approved):
            raise UserError(_('PM1 must approve first before PM2 can reject.'))

        pm_role = ('PM1 - %s' % current_user.name if current_user == self.ks_validate_pm1_id
                   else 'PM2 - %s' % current_user.name)

        self._mark_delivery_activity_done(current_user, feedback=_('❌ Rejected: %s') % reason)
        self._ks_cancel_delivery_activities()

        # Restore pre-approval state
        pre_state = self.ks_pre_approval_state or 'assigned'
        self.write({
            'state': pre_state,
            'ks_validate_pm1_id': False,
            'ks_validate_pm2_id': False,
            'ks_validate_pm1_approved': False,
            'ks_validate_pm2_approved': False,
            'ks_validate_request_user_id': False,
            'ks_validate_request_date': False,
            'ks_pre_approval_state': False,
        })
        self.message_post(
            body=_('❌ Validation Rejected\nRejected by: %s\nReason: %s') % (pm_role, reason),
            message_type='notification', subtype_xmlid='mail.mt_note',
        )
        if self.ks_validate_request_user_id:
            self.env['bus.bus']._sendone(
                self.ks_validate_request_user_id.partner_id,
                'simple_notification',
                {
                    'type': 'danger',
                    'title': _('Delivery Rejected: %s') % self.name,
                    'message': _('Your delivery approval request was rejected.'),
                    'sticky': True,
                },
            )

    # -------------------------------------------------------------------------
    # POD (Proof of Delivery)
    # -------------------------------------------------------------------------
    ks_pod_sent = fields.Boolean(string='POD Sent', default=False, copy=False, tracking=True)
    ks_pod_attachment_id = fields.Many2one('ir.attachment', string='POD Attachment', copy=False)

    def action_upload_pod(self):
        self.ensure_one()
        view_id = self.env.ref('ks_sale_approval.ks_pod_upload_wizard_form')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Upload Proof of Delivery'),
            'res_model': 'ks.pod.upload.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'context': {'default_ks_picking_id': self.id},
        }

    # -------------------------------------------------------------------------
    # Activity helpers
    # -------------------------------------------------------------------------
    def _create_delivery_approval_activity(self, user, keyword='Validate'):
        self.ensure_one()
        self.activity_schedule(
            act_type_xmlid='ks_sale_approval.mail_activity_data_sale_approval',
            summary=_('Delivery Approval (%s): %s') % (keyword, self.name),
            note=_('Please review this delivery validation approval request.'),
            user_id=user.id,
            date_deadline=fields.Date.context_today(self),
        )

    def _mark_delivery_activity_done(self, user, feedback=''):
        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'stock.picking'),
            ('res_id', '=', self.id),
            ('user_id', '=', user.id),
            ('summary', 'ilike', 'Delivery Approval'),
        ])
        for act in activities:
            act.action_feedback(feedback=feedback)

    def _ks_cancel_delivery_activities(self):
        """Silently cancel all delivery-approval activities (used on rejection/reset)."""
        self.ensure_one()
        pm_ids = list(filter(None, [
            self.ks_validate_pm1_id.id if self.ks_validate_pm1_id else False,
            self.ks_validate_pm2_id.id if self.ks_validate_pm2_id else False,
        ]))
        domain = [
            ('res_model', '=', 'stock.picking'),
            ('res_id', '=', self.id),
            ('active', '=', True),
            ('summary', 'ilike', 'Delivery Approval'),
        ]
        if pm_ids:
            domain.append(('user_id', 'in', pm_ids))
        self.env['mail.activity'].search(domain).sudo().unlink()
