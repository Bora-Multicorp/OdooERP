# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Override state field to add new states
    state = fields.Selection(
        selection_add=[
            ('approval_pending', 'Approval Pending'),
            ('cancel_pending', 'Cancel Pending'),
            ('edit_pending', 'Edit Approval Pending'),
            ('sale',),  # Ensure proper ordering
        ],
        ondelete={
            'approval_pending': 'set default',
            'cancel_pending': 'set default',
            'edit_pending': 'set default',
        }
    )

    # ===== Confirmation Approval Fields =====
    ks_confirm_pm1_id = fields.Many2one(
        'res.users',
        string='Selected Confirmation Approver PM1',
        copy=False,
        help='Selected approver from PM1 list for this approval request',
    )
    ks_confirm_pm2_id = fields.Many2one(
        'res.users',
        string='Selected Confirmation Approver PM2',
        copy=False,
        help='Selected approver from PM2 list for this approval request',
    )
    ks_confirm_pm1_approved = fields.Boolean(
        string='PM1 Confirmation Approved',
        default=False,
        copy=False,
        tracking=True,
    )
    ks_confirm_pm2_approved = fields.Boolean(
        string='PM2 Confirmation Approved',
        default=False,
        copy=False,
        tracking=True,
    )
    ks_confirm_request_user_id = fields.Many2one(
        'res.users',
        string='Confirmation Requested By',
        copy=False,
    )
    ks_confirm_request_date = fields.Datetime(
        string='Confirmation Request Date',
        copy=False,
    )

    # ===== Cancel Approval Fields =====
    ks_cancel_pm1_id = fields.Many2one(
        'res.users',
        string='Selected Cancel Approver PM1',
        copy=False,
        help='Selected approver from PM1 list for this cancel request',
    )
    ks_cancel_pm2_id = fields.Many2one(
        'res.users',
        string='Selected Cancel Approver PM2',
        copy=False,
        help='Selected approver from PM2 list for this cancel request',
    )
    ks_cancel_pm1_approved = fields.Boolean(
        string='PM1 Cancel Approved',
        default=False,
        copy=False,
        tracking=True,
    )
    ks_cancel_pm2_approved = fields.Boolean(
        string='PM2 Cancel Approved',
        default=False,
        copy=False,
        tracking=True,
    )
    ks_cancel_request_reason = fields.Text(
        string='Cancel Request Reason',
        copy=False,
    )
    ks_cancel_request_user_id = fields.Many2one(
        'res.users',
        string='Cancel Requested By',
        copy=False,
    )
    ks_cancel_request_date = fields.Datetime(
        string='Cancel Request Date',
        copy=False,
    )

    # ===== Edit Approval Fields =====
    ks_edit_pm1_id = fields.Many2one(
        'res.users',
        string='Selected Edit Approver PM1',
        copy=False,
        help='Selected approver from PM1 list for this edit request',
    )
    ks_edit_pm2_id = fields.Many2one(
        'res.users',
        string='Selected Edit Approver PM2',
        copy=False,
        help='Selected approver from PM2 list for this edit request',
    )
    ks_edit_pm1_approved = fields.Boolean(
        string='PM1 Edit Approved',
        default=False,
        copy=False,
        tracking=True,
    )
    ks_edit_pm2_approved = fields.Boolean(
        string='PM2 Edit Approved',
        default=False,
        copy=False,
        tracking=True,
    )
    ks_edit_request_reason = fields.Text(
        string='Edit Request Reason',
        copy=False,
    )
    ks_edit_request_user_id = fields.Many2one(
        'res.users',
        string='Edit Requested By',
        copy=False,
    )
    ks_edit_request_date = fields.Datetime(
        string='Edit Request Date',
        copy=False,
    )
    ks_edit_approved = fields.Boolean(
        string='Edit Approved (Editable)',
        default=False,
        copy=False,
        help='When True, the original requester can edit the SO',
    )

    # ===== Computed Fields for UI =====
    ks_is_pm_user = fields.Boolean(
        string='Is PM User',
        compute='_compute_ks_is_pm_user',
    )
    ks_is_normal_user = fields.Boolean(
        string='Is Normal User',
        compute='_compute_ks_is_pm_user',
    )
    ks_can_edit = fields.Boolean(
        string='Can Edit SO',
        compute='_compute_ks_can_edit',
    )
    ks_is_admin_user = fields.Boolean(
        string='Is Admin User',
        compute='_compute_ks_is_admin_user',
    )

    # Button visibility fields
    ks_show_approve_confirm_button = fields.Boolean(
        string='Show Approve Confirmation Button',
        compute='_compute_ks_button_visibility',
    )
    ks_show_reject_confirm_button = fields.Boolean(
        string='Show Reject Confirmation Button',
        compute='_compute_ks_button_visibility',
    )
    ks_show_approve_cancel_button = fields.Boolean(
        string='Show Approve Cancel Button',
        compute='_compute_ks_button_visibility',
    )
    ks_show_reject_cancel_button = fields.Boolean(
        string='Show Reject Cancel Button',
        compute='_compute_ks_button_visibility',
    )
    ks_show_approve_edit_button = fields.Boolean(
        string='Show Approve Edit Button',
        compute='_compute_ks_button_visibility',
    )
    ks_show_reject_edit_button = fields.Boolean(
        string='Show Reject Edit Button',
        compute='_compute_ks_button_visibility',
    )
    ks_show_request_edit_button = fields.Boolean(
        string='Show Request Edit Button',
        compute='_compute_ks_button_visibility',
    )
    ks_show_complete_edit_button = fields.Boolean(
        string='Show Complete Edit Button',
        compute='_compute_ks_button_visibility',
    )
    ks_is_dual_approval = fields.Boolean(
        string='Is Dual Approval Mode',
        compute='_compute_ks_is_dual_approval',
        help='True if dual approval mode is enabled in config',
    )
    ks_show_update_approval_button = fields.Boolean(
        string='Show Update Approvals Button',
        compute='_compute_ks_button_visibility',
    )
    ks_show_update_cancel_approval_button = fields.Boolean(
        string='Show Update Cancel Approvals Button',
        compute='_compute_ks_button_visibility',
    )
    ks_show_update_edit_approval_button = fields.Boolean(
        string='Show Update Edit Approvals Button',
        compute='_compute_ks_button_visibility',
    )

    @api.depends('company_id')
    def _compute_ks_is_dual_approval(self):
        """Compute if dual approval mode is enabled"""
        for order in self:
            if order._has_approval_config():
                config = order._get_approval_config()
                order.ks_is_dual_approval = config.is_dual_approval()
            else:
                order.ks_is_dual_approval = False

    # ===== Helper Methods =====
    def _get_approval_config(self):
        """Get global approval configuration (applies to all companies)"""
        config = self.env['ks.sale.approval.config'].get_config()
        if not config:
            raise UserError(_(
                "No active approval configuration found. "
                "Please configure PM approvers in Sales > Configuration > Sale Approval Configuration."
            ))
        return config

    def _has_approval_config(self):
        """Check if approval config exists without raising error"""
        config = self.env['ks.sale.approval.config'].get_config()
        return bool(config)

    @api.depends_context('uid')
    def _compute_ks_is_pm_user(self):
        """Check if current user is any of the PM users"""
        for order in self:
            if order._has_approval_config():
                config = order._get_approval_config()
                all_pms = config.get_all_pm_users()
                order.ks_is_pm_user = self.env.user in all_pms
                order.ks_is_normal_user = self.env.user not in all_pms
            else:
                order.ks_is_pm_user = False
                order.ks_is_normal_user = True

    @api.depends('state', 'ks_is_pm_user', 'ks_edit_approved', 'ks_edit_request_user_id')
    @api.depends_context('uid')
    def _compute_ks_can_edit(self):
        """
        Determine if current user can edit the SO

        Rules:
        - Admin users: Can edit ANY state (bypass all restrictions)
        - Draft/Sent: Everyone can edit
        - Approval Pending: No one can edit (locked) - except admin
        - Cancel Pending: No one can edit (locked) - except admin
        - Edit Pending: No one can edit (locked) - except admin
        - Sale (Confirmed):
            - Normal users: CANNOT edit (locked) UNLESS edit was approved for them
            - PM users: Can edit (they have full control)
            - Admin users: Can edit (bypass restrictions)
        - Locked: No one can edit - except admin
        """
        for order in self:
            current_user = self.env.user

            # Admin users can edit ANY state - bypass all restrictions
            if order._is_admin_user():
                order.ks_can_edit = True
                continue

            if order.state in ['draft', 'sent']:
                # Draft and Sent - everyone can edit
                order.ks_can_edit = True
            elif order.state in ['approval_pending', 'cancel_pending', 'edit_pending']:
                # All approval states - locked for everyone (except admin, handled above)
                order.ks_can_edit = False
            elif order.state == 'sale':
                # Confirmed state
                if order.ks_is_pm_user:
                    # PM users can always edit confirmed SOs
                    order.ks_can_edit = True
                elif order.ks_edit_approved and order.ks_edit_request_user_id == current_user:
                    # Normal user who requested edit AND it was approved
                    order.ks_can_edit = True
                else:
                    # Normal users cannot edit confirmed SOs
                    order.ks_can_edit = False
            elif order.locked:
                # Locked state - no one can edit (except admin, handled above)
                order.ks_can_edit = False
            else:
                order.ks_can_edit = False

    @api.depends('state', 'ks_is_pm_user', 'ks_is_normal_user',
                 'ks_confirm_pm1_approved', 'ks_confirm_pm2_approved',
                 'ks_cancel_pm1_approved', 'ks_cancel_pm2_approved',
                 'ks_edit_pm1_approved', 'ks_edit_pm2_approved',
                 'ks_edit_approved', 'ks_edit_request_user_id')
    @api.depends_context('uid')
    def _compute_ks_button_visibility(self):
        """Compute visibility of all action buttons

        Admin users can see all buttons and bypass approval restrictions.
        """
        for order in self:
            # Reset all
            order.ks_show_approve_confirm_button = False
            order.ks_show_reject_confirm_button = False
            order.ks_show_approve_cancel_button = False
            order.ks_show_reject_cancel_button = False
            order.ks_show_approve_edit_button = False
            order.ks_show_reject_edit_button = False
            order.ks_show_request_edit_button = False
            order.ks_show_complete_edit_button = False
            order.ks_show_update_approval_button = False
            order.ks_show_update_cancel_approval_button = False
            order.ks_show_update_edit_approval_button = False

            # Admin users bypass all restrictions
            # Admin users should NOT see "Request Cancel" and "Request Edit" buttons
            # They should use the standard Cancel button and can edit directly
            is_admin = order._is_admin_user()
            if is_admin:
                # Admin can approve/reject pending requests if needed
                if order.state == 'approval_pending':
                    order.ks_show_approve_confirm_button = True
                    order.ks_show_reject_confirm_button = True
                elif order.state == 'cancel_pending':
                    order.ks_show_approve_cancel_button = True
                    order.ks_show_reject_cancel_button = True
                elif order.state == 'edit_pending':
                    order.ks_show_approve_edit_button = True
                    order.ks_show_reject_edit_button = True
                # Do NOT show Request Cancel or Request Edit buttons for admin
                # Admin can use standard Cancel button and edit directly
                continue  # Skip normal user logic for admins

            if not order._has_approval_config():
                continue

            config = order._get_approval_config()
            current_user = self.env.user
            is_pm = order.ks_is_pm_user
            is_normal = order.ks_is_normal_user

            # === NORMAL USER BUTTONS ===
            if is_normal:
                # Request Edit button - only when SO is confirmed and no pending edit
                if order.state == 'sale' and not order.ks_edit_approved:
                    order.ks_show_request_edit_button = True

                # Complete Edit button - when edit is approved for this user
                if (order.state == 'sale' and
                        order.ks_edit_approved and
                        order.ks_edit_request_user_id == current_user):
                    order.ks_show_complete_edit_button = True

                # Update Approvals button - only the requester can update while pending
                if (order.state == 'approval_pending' and
                        order.ks_confirm_request_user_id == current_user):
                    order.ks_show_update_approval_button = True

                # Update Cancel Approvals - requester can update while cancel_pending
                if (order.state == 'cancel_pending' and
                        order.ks_cancel_request_user_id == current_user):
                    order.ks_show_update_cancel_approval_button = True

                # Update Edit Approvals - requester can update while edit_pending
                if (order.state == 'edit_pending' and
                        order.ks_edit_request_user_id == current_user):
                    order.ks_show_update_edit_approval_button = True

            # === PM USER BUTTONS ===
            if is_pm:
                # Confirmation approval buttons
                if order.state == 'approval_pending':
                    # Check if this PM can still approve (hasn't approved yet)
                    can_approve = False
                    # PM1 can always approve if not already approved
                    if order.ks_confirm_pm1_id and current_user == order.ks_confirm_pm1_id and not order.ks_confirm_pm1_approved:
                        can_approve = True
                    # PM2 can only approve if PM1 has already approved
                    elif order.ks_confirm_pm2_id and current_user == order.ks_confirm_pm2_id:
                        if order.ks_confirm_pm1_approved and not order.ks_confirm_pm2_approved:
                            can_approve = True

                    if can_approve:
                        order.ks_show_approve_confirm_button = True
                        order.ks_show_reject_confirm_button = True

                # Cancel approval buttons
                if order.state == 'cancel_pending':
                    can_approve = False
                    # PM1 can always approve if not already approved
                    if order.ks_cancel_pm1_id and current_user == order.ks_cancel_pm1_id and not order.ks_cancel_pm1_approved:
                        can_approve = True
                    # PM2 can only approve if PM1 has already approved
                    elif order.ks_cancel_pm2_id and current_user == order.ks_cancel_pm2_id:
                        if order.ks_cancel_pm1_approved and not order.ks_cancel_pm2_approved:
                            can_approve = True

                    if can_approve:
                        order.ks_show_approve_cancel_button = True
                        order.ks_show_reject_cancel_button = True

                # Edit approval buttons
                if order.state == 'edit_pending':
                    can_approve = False
                    # PM1 can always approve if not already approved
                    if order.ks_edit_pm1_id and current_user == order.ks_edit_pm1_id and not order.ks_edit_pm1_approved:
                        can_approve = True
                    # PM2 can only approve if PM1 has already approved
                    elif order.ks_edit_pm2_id and current_user == order.ks_edit_pm2_id:
                        if order.ks_edit_pm1_approved and not order.ks_edit_pm2_approved:
                            can_approve = True

                    if can_approve:
                        order.ks_show_approve_edit_button = True
                        order.ks_show_reject_edit_button = True

    # ===== Helper Methods =====

    @api.depends_context('uid')
    def _compute_ks_is_admin_user(self):
        """Compute if current user is a custom admin (is_custom_admin on res.users)"""
        for order in self:
            order.ks_is_admin_user = order._is_admin_user()

    def _is_admin_user(self):
        """Check if current user has admin privileges (is_custom_admin on res.users).
        Custom admins bypass all approval stages and can confirm/cancel/edit directly.
        """
        return bool(self.env.user.is_custom_admin)

    # ===== Override Confirm Action =====

    def _confirmation_error_message(self):
        """Include check: sales price must not be below latest purchase price (in order currency)."""
        msg = super()._confirmation_error_message()
        if msg:
            return msg
        self.ensure_one()
        for line in self.order_line:
            if line.display_type or not line.product_id:
                continue
            min_purchase = line._ks_get_latest_purchase_price_in_order_currency()
            if min_purchase is None:
                continue
            sale_price = line._ks_get_sale_price_in_order_currency()
            if sale_price is None:
                continue
            if float_compare(sale_price, min_purchase, precision_digits=2) < 0:
                order_cur = self.currency_id
                return _(
                    "Sales price cannot be below latest purchase price. "
                    "Product '%s': unit price in order currency (%s) is below latest purchase price (min %s %s)."
                ) % (line.product_id.display_name, order_cur.name, order_cur.round(min_purchase), order_cur.name)
        return False

    def action_confirm(self):
        """
        Override:
        - Custom admin (is_custom_admin): Confirm immediately (bypass all approval)
        - PM users (from config): Confirm immediately (standard flow)
        - Normal users: Open approval request wizard to show recipients
        """
        for order in self:
            if order.state not in ['draft', 'sent']:
                continue

            # Check confirmation errors
            error_msg = order._confirmation_error_message()
            if error_msg:
                raise UserError(error_msg)

            # Custom admin bypasses all approval restrictions (no group check)
            if order._is_admin_user():
                return super().action_confirm()

            # Check if approval config exists
            if not order._has_approval_config():
                # No config, use standard behavior
                return super().action_confirm()

            config = order._get_approval_config()
            is_pm = self.env.user in config.get_all_pm_users()

            if is_pm:
                # PM users can directly confirm - call original method
                return super().action_confirm()
            else:
                # Normal user - open approval request wizard
                return order._action_open_approval_request_wizard()

        return True

    def _action_open_approval_request_wizard(self):
        """Open wizard to show approval recipients before sending request"""
        self.ensure_one()
        config = self._get_approval_config() if self._has_approval_config() else False
        return {
            'name': _('Request for Approval'),
            'type': 'ir.actions.act_window',
            'res_model': 'ks.sale.approval.request.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_ks_sale_order_id': self.id,
                'ks_approval_mode': config.ks_approval_mode if config else 'single',
            },
        }

    def action_update_approvals(self):
        """Let the requester update approvers while the SO is still approval_pending.

        Steps:
        1. Cancel all pending approval activities on this SO.
        2. Reset approval flags / approver fields so the order is effectively
           back to 'draft-ready-to-resubmit' state (state stays approval_pending
           until the wizard re-runs _ks_send_to_approval_pending which moves it
           to approval_pending again — we briefly set it to 'sent' to satisfy
           the state guard in that method).
        3. Open the same approval-request wizard as the first-time flow.
        """
        self.ensure_one()
        if self.state != 'approval_pending':
            raise UserError(_("Update Approvals is only available while the order is in 'Approval Pending' state."))
        if self.ks_confirm_request_user_id and self.ks_confirm_request_user_id != self.env.user:
            if not self._is_admin_user():
                raise UserError(_("Only the original requester can update the approval request."))

        # Open the wizard with is_update=True flag.
        # ALL cleanup (cancel activities, reset fields) happens inside the wizard's
        # action_confirm_request ONLY when the user clicks OK — not here.
        # This means clicking "Cancel" in the wizard leaves everything untouched.
        config = self._get_approval_config() if self._has_approval_config() else False
        return {
            'name': _('Update Approval Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'ks.sale.approval.request.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_ks_sale_order_id': self.id,
                'ks_approval_mode': config.ks_approval_mode if config else 'single',
                'ks_is_update': True,
                'default_ks_is_update_mode': True,
                'default_ks_approver1_user': self.ks_confirm_pm1_id.id or False,
                'default_ks_approver2_user': self.ks_confirm_pm2_id.id or False,
            },
        }

    def action_update_cancel_approvals(self):
        """Let the requester update cancel approvers while the SO is in cancel_pending."""
        self.ensure_one()
        if self.state != 'cancel_pending':
            raise UserError(_("Update Cancel Approvals is only available while the order is in 'Cancel Pending' state."))
        if self.ks_cancel_request_user_id and self.ks_cancel_request_user_id != self.env.user:
            if not self._is_admin_user():
                raise UserError(_("Only the original requester can update the cancel approval request."))

        config = self._get_approval_config() if self._has_approval_config() else False
        return {
            'name': _('Update Cancel Approval Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'ks.sale.cancel.approval.request.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_ks_sale_order_id': self.id,
                'ks_approval_mode': config.ks_approval_mode if config else 'single',
                'ks_is_update': True,
                'default_ks_is_update_mode': True,
                'default_ks_approver1_user': self.ks_cancel_pm1_id.id or False,
                'default_ks_approver2_user': self.ks_cancel_pm2_id.id or False,
            },
        }

    def action_update_edit_approvals(self):
        """Let the requester update edit approvers while the SO is in edit_pending."""
        self.ensure_one()
        if self.state != 'edit_pending':
            raise UserError(_("Update Edit Approvals is only available while the order is in 'Edit Approval Pending' state."))
        if self.ks_edit_request_user_id and self.ks_edit_request_user_id != self.env.user:
            if not self._is_admin_user():
                raise UserError(_("Only the original requester can update the edit approval request."))

        config = self._get_approval_config() if self._has_approval_config() else False
        return {
            'name': _('Update Edit Approval Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'ks.sale.edit.approval.request.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_ks_sale_order_id': self.id,
                'ks_approval_mode': config.ks_approval_mode if config else 'single',
                'ks_is_update': True,
                'default_ks_is_update_mode': True,
                'default_ks_approver1_user': self.ks_edit_pm1_id.id or False,
                'default_ks_approver2_user': self.ks_edit_pm2_id.id or False,
            },
        }

    def _ks_send_to_approval_pending(self):
        """Normal user sends SO to approval pending - locks the order"""
        self.ensure_one()
        if self.state not in ['draft', 'sent']:
            raise UserError(_("Can only request confirmation for Draft or Sent orders."))

        # Validate that approvers are selected
        if not self.ks_confirm_pm1_id:
            raise UserError(_("Approver 1 must be selected before sending approval request."))

        # Validate analytic distribution
        self.order_line._validate_analytic_distribution()

        config = self._get_approval_config()
        if config.is_dual_approval() and not self.ks_confirm_pm2_id:
            raise UserError(_("Approver 2 must be selected for dual approval mode."))

        self.write({
            'state': 'approval_pending',
            'ks_confirm_request_user_id': self.env.user.id,
            'ks_confirm_request_date': fields.Datetime.now(),
            'ks_confirm_pm1_approved': False,
            'ks_confirm_pm2_approved': False,
        })
        # Lock the SO immediately so it cannot be edited while awaiting approval
        self.action_lock()

        # Determine approval message based on mode
        if config.is_dual_approval():
            pm1_name = self.ks_confirm_pm1_id.name if self.ks_confirm_pm1_id else ''
            pm2_name = self.ks_confirm_pm2_id.name if self.ks_confirm_pm2_id else ''
            approval_msg = _(
                "Confirmation request submitted by %s. Waiting for approval from %s (PM1) and %s (PM2).") % (
                               self.env.user.name, pm1_name, pm2_name
                           )
        else:
            pm1_name = self.ks_confirm_pm1_id.name if self.ks_confirm_pm1_id else ''
            approval_msg = _("Confirmation request submitted by %s. Waiting for approval from %s (PM1).") % (
                self.env.user.name, pm1_name
            )

        # Log in chatter
        self.message_post(
            body=approval_msg,
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

        # Subscribe selected PM users
        partner_ids = [self.ks_confirm_pm1_id.partner_id.id]
        if self.ks_confirm_pm2_id:
            partner_ids.append(self.ks_confirm_pm2_id.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)

        # Create activities for approvers
        # Create activity for PM1
        summary = self._get_approval_activity_summary('confirm', 'PM1')
        note = self._get_approval_activity_note('confirm', self.name, self.env.user.name)
        self._create_approval_activity(self.ks_confirm_pm1_id, summary, note)

        # In dual approval mode, create activity for PM2 only after PM1 approves
        # (PM2 activity will be created when PM1 approves)

        return True

    def ks_action_approve_confirmation(self):
        """PM approves confirmation request - open wizard for reason"""
        self.ensure_one()
        if self.state != 'approval_pending':
            raise UserError(_("Can only approve orders in 'Approval Pending' state."))
        return self._action_open_approval_reason_wizard('approve_confirm')

    def _ks_do_approve_confirmation_with_reason(self, reason, current_user):
        """Execute confirmation approval with reason"""
        self.ensure_one()
        if not reason:
            raise UserError(_("Approval reason is required."))

        config = self._get_approval_config()

        # Check which PM is approving
        pm_role = None
        is_pm1_approving = False
        is_pm2_approving = False

        if self.ks_confirm_pm1_id and current_user == self.ks_confirm_pm1_id:
            if self.ks_confirm_pm1_approved:
                raise UserError(_("You have already approved this confirmation request."))
            self.ks_confirm_pm1_approved = True
            pm_role = 'PM1 - %s' % self.ks_confirm_pm1_id.name
            is_pm1_approving = True
        elif self.ks_confirm_pm2_id and current_user == self.ks_confirm_pm2_id:
            # Sequential approval: PM2 can only approve if PM1 has already approved
            if not self.ks_confirm_pm1_approved:
                raise UserError(_("PM1 must approve first before PM2 can approve this confirmation request."))
            if self.ks_confirm_pm2_approved:
                raise UserError(_("You have already approved this confirmation request."))
            self.ks_confirm_pm2_approved = True
            pm_role = 'PM2 - %s' % self.ks_confirm_pm2_id.name
            is_pm2_approving = True
        else:
            raise UserError(_("You are not authorized to approve this confirmation request."))

        # Mark current user's activity as done
        self._mark_activity_done(current_user, feedback=_("Approved: %s") % reason)

        # If PM1 approved and dual mode, create activity for PM2
        if is_pm1_approving and config.is_dual_approval() and self.ks_confirm_pm2_id:
            summary = self._get_approval_activity_summary('confirm', 'PM2')
            note = self._get_approval_activity_note('confirm', self.name,
                                                    self.ks_confirm_request_user_id.name if self.ks_confirm_request_user_id else _(
                                                        'Unknown'))
            self._create_approval_activity(self.ks_confirm_pm2_id, summary, note)

        # Post message in chatter with reason
        self.message_post(
            body=_(
                "✅ Confirmation Approved\n"
                "Approved by: %s\n"
                "Action: Approved\n"
                "Reason: %s"
            ) % (pm_role, reason),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

        # Check if approval is complete based on mode
        approval_complete = False
        if config.is_dual_approval():
            # Both PMs must approve
            if self.ks_confirm_pm1_approved and self.ks_confirm_pm2_approved:
                approval_complete = True
        else:
            # Single PM approval - PM1 approval is enough
            if self.ks_confirm_pm1_approved:
                approval_complete = True

        if approval_complete:
            # Mark all remaining activities as done (approval complete)
            if self.ks_confirm_pm1_id:
                self._mark_activity_done(self.ks_confirm_pm1_id,
                                         feedback=_("Approval completed - Sale Order confirmed"))
            if self.ks_confirm_pm2_id:
                self._mark_activity_done(self.ks_confirm_pm2_id,
                                         feedback=_("Approval completed - Sale Order confirmed"))
            # Approval complete - confirm the SO using standard flow
            self._ks_complete_confirmation()

        return True

    def _ks_complete_confirmation(self):
        """Complete the confirmation after all required approvals"""
        self.ensure_one()

        # Subscribe partner if not already
        if self.partner_id not in self.message_partner_ids:
            self.message_subscribe([self.partner_id.id])

        # Prepare confirmation values
        confirmation_values = self._prepare_confirmation_values()
        self.write(confirmation_values)

        # Context key 'default_name' is sometimes propagated up to here.
        context = self._context.copy()
        context.pop('default_name', None)
        context.pop('default_user_id', None)

        self.with_context(context)._action_confirm()

        # Check stock availability and send notifications after confirmation
        # This ensures stock shortage alerts are triggered even when order is confirmed via approval process
        # Note: State is already set to 'sale' by _prepare_confirmation_values() and write() above
        if hasattr(self, '_ks_check_and_notify_stock_shortage_on_confirm'):
            # Refresh to ensure state is loaded from database
            self.invalidate_recordset(['state'])
            # Call the stock shortage check - it will verify state == 'sale' internally
            self._ks_check_and_notify_stock_shortage_on_confirm()

        # Lock if needed
        if self._should_be_locked():
            self.action_lock()

        config = self._get_approval_config()
        if config.is_dual_approval():
            pm1_name = self.ks_confirm_pm1_id.name if self.ks_confirm_pm1_id else ''
            pm2_name = self.ks_confirm_pm2_id.name if self.ks_confirm_pm2_id else ''
            self.message_post(
                body=_("Sale Order confirmed after both %s (PM1) and %s (PM2) approval.") % (pm1_name, pm2_name),
                message_type='notification',
                subtype_xmlid='mail.mt_comment',
            )
        else:
            pm1_name = self.ks_confirm_pm1_id.name if self.ks_confirm_pm1_id else ''
            self.message_post(
                body=_("Sale Order confirmed after %s (PM1) approval.") % pm1_name,
                message_type='notification',
                subtype_xmlid='mail.mt_comment',
            )

    def ks_action_reject_confirmation(self):
        """PM rejects confirmation request - open wizard for reason"""
        self.ensure_one()
        if self.state != 'approval_pending':
            raise UserError(_("Can only reject orders in 'Approval Pending' state."))
        return self._action_open_approval_reason_wizard('reject_confirm')

    def ks_do_reject_confirmation(self, reason):
        """Execute confirmation rejection with reason"""
        self.ensure_one()
        if not reason:
            raise UserError(_("Rejection reason is required."))

        config = self._get_approval_config()
        current_user = self.env.user

        # Check if user is one of the selected approvers
        if not ((self.ks_confirm_pm1_id and current_user == self.ks_confirm_pm1_id) or
                (self.ks_confirm_pm2_id and current_user == self.ks_confirm_pm2_id)):
            raise UserError(_("You are not authorized to reject this confirmation request."))

        # Sequential approval: PM2 can only reject if PM1 has already approved
        if self.ks_confirm_pm2_id and current_user == self.ks_confirm_pm2_id:
            if not self.ks_confirm_pm1_approved:
                raise UserError(_("PM1 must approve first before PM2 can reject this confirmation request."))

        # Determine PM role
        pm_role = None
        if self.ks_confirm_pm1_id and current_user == self.ks_confirm_pm1_id:
            pm_role = 'PM1 - %s' % self.ks_confirm_pm1_id.name
        elif self.ks_confirm_pm2_id and current_user == self.ks_confirm_pm2_id:
            pm_role = 'PM2 - %s' % self.ks_confirm_pm2_id.name

        # Mark current user's activity as done
        self._mark_activity_done(current_user, feedback=_("Rejected: %s") % reason)

        # Also mark other approver's activity as done if exists (rejection ends the process)
        if self.ks_confirm_pm1_id and current_user != self.ks_confirm_pm1_id:
            self._mark_activity_done(self.ks_confirm_pm1_id, feedback=_("Request rejected by %s") % current_user.name)
        if self.ks_confirm_pm2_id and current_user != self.ks_confirm_pm2_id:
            self._mark_activity_done(self.ks_confirm_pm2_id, feedback=_("Request rejected by %s") % current_user.name)

        # Reset to draft state and unlock so it can be edited again
        self.action_unlock()
        self.write({
            'state': 'draft',
            'ks_confirm_pm1_id': False,
            'ks_confirm_pm2_id': False,
            'ks_confirm_pm1_approved': False,
            'ks_confirm_pm2_approved': False,
            'ks_confirm_request_user_id': False,
            'ks_confirm_request_date': False,
        })

        # Post message in chatter with reason
        self.message_post(
            body=_(
                "❌ Confirmation Rejected\n"
                "Rejected by: %s\n"
                "Action: Rejected\n"
                "Reason: %s"
            ) % (pm_role or current_user.name, reason),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

        return True

    # ===== Cancel Request Methods =====

    def write(self, values):
        """Override write to trigger recomputation of ks_can_edit_price on lines when ks_edit_approved changes.
        Also blocks normal users from changing payment_term_id or user_id on confirmed/locked SOs.
        """
        _protected_fields = ['payment_term_id', 'user_id', 'ks_no_tax_allowed', 'stock_decifient']
        changing_protected = any(f in values for f in _protected_fields)

        if changing_protected:
            for order in self:
                if not order.locked:
                    continue
                if order._is_admin_user():
                    continue
                if not order._has_approval_config():
                    continue
                config = order._get_approval_config()
                if self.env.user in config.get_all_pm_users():
                    continue
                # Normal user on a locked order
                edit_approved = (
                    order.ks_edit_approved and
                    order.ks_edit_request_user_id == self.env.user
                )
                if not edit_approved:
                    changed = [f for f in _protected_fields if f in values]
                    raise UserError(_(
                        "You cannot modify %s on a confirmed Sale Order. "
                        "Please use 'Request Edit' to get edit approval first."
                    ) % ', '.join(changed))

        result = super().write(values)

        # If ks_edit_approved changed, recompute ks_can_edit_price on order lines
        if 'ks_edit_approved' in values or 'ks_edit_request_user_id' in values:
            for order in self:
                if order.order_line:
                    order.order_line._compute_ks_can_edit_price()

        return result

    def action_cancel(self):
        """Override: Normal users must request cancellation for confirmed SOs, PMs can directly cancel"""
        for order in self:
            # Admin users bypass all approval restrictions
            if order._is_admin_user():
                if order.locked:
                    order.action_unlock()
                return super().action_cancel()

            # Check if approval config exists
            if not order._has_approval_config():
                # No config, use standard behavior
                return super().action_cancel()

            config = order._get_approval_config()
            is_pm = self.env.user in config.get_all_pm_users()

            if is_pm:
                # PM users can directly cancel; unlock first if locked
                if order.locked:
                    order.action_unlock()
                return super().action_cancel()
            else:
                # Normal user
                if order.state in ['draft', 'sent']:
                    # For draft/sent, allow direct cancellation
                    return super().action_cancel()
                elif order.state == 'sale':
                    # For confirmed SO, need approval - open wizard
                    return order._action_open_cancel_request_wizard()
                elif order.state == 'approval_pending':
                    # Requester withdrawing their own confirmation request → back to draft
                    return order._ks_cancel_approval_request()
                elif order.state == 'cancel_pending':
                    # A cancel-approval is in flight.  The requester can withdraw it
                    # (returns to sale); other users are blocked to protect history.
                    if order.ks_cancel_request_user_id == self.env.user:
                        self._ks_cancel_workflow_activities(
                            'cancel', mark_done=True,
                            feedback=_("Cancel request withdrawn by %s") % self.env.user.name,
                        )
                        order.write({
                            'state': 'sale',
                            'ks_cancel_pm1_id': False,
                            'ks_cancel_pm2_id': False,
                            'ks_cancel_pm1_approved': False,
                            'ks_cancel_pm2_approved': False,
                            'ks_cancel_request_user_id': False,
                            'ks_cancel_request_date': False,
                            'ks_cancel_request_reason': False,
                        })
                        order.message_post(
                            body=_("Cancel request withdrawn by %s.") % self.env.user.name,
                            message_type='notification',
                            subtype_xmlid='mail.mt_note',
                        )
                        return True
                    else:
                        raise UserError(_(
                            "A cancellation approval is in progress. "
                            "Only the original requester (%s) can withdraw it."
                        ) % (order.ks_cancel_request_user_id.name or ''))
                elif order.state == 'edit_pending':
                    # An edit-approval is in flight — block standard cancel entirely.
                    # The requester should use 'Update Edit Approvals' to change approvers
                    # or wait for the PM to decide.
                    raise UserError(_(
                        "An edit approval request is pending. "
                        "Please wait for the PM to approve or reject it before cancelling."
                    ))
                else:
                    raise UserError(_("Cannot cancel order in current state."))
        return True

    def _ks_cancel_approval_request(self):
        """Cancel the approval request and return to draft"""
        self.ensure_one()
        # Mark confirm-workflow activities as done (leaves chatter entry, type+keyword scoped)
        self._ks_cancel_workflow_activities(
            'confirm', mark_done=True,
            feedback=_("Approval request cancelled by %s") % self.env.user.name,
        )

        # Unlock so the SO can be edited again after withdrawal
        self.action_unlock()
        self.write({
            'state': 'draft',
            'ks_confirm_pm1_id': False,
            'ks_confirm_pm2_id': False,
            'ks_confirm_pm1_approved': False,
            'ks_confirm_pm2_approved': False,
            'ks_confirm_request_user_id': False,
            'ks_confirm_request_date': False,
        })
        self.message_post(
            body=_("Approval request cancelled by %s.") % self.env.user.name,
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        return True

    def _action_open_cancel_request_wizard(self):
        """Open wizard to select approvers for cancel request"""
        self.ensure_one()
        config = self._get_approval_config() if self._has_approval_config() else False
        return {
            'name': _('Product Approval Picker'),
            'type': 'ir.actions.act_window',
            'res_model': 'ks.sale.cancel.approval.request.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_ks_sale_order_id': self.id,
                'ks_approval_mode': config.ks_approval_mode if config else 'single',
            },
        }

    def ks_do_request_cancel(self, reason):
        """Execute cancel request (approvers already selected via wizard)"""
        self.ensure_one()
        if not reason:
            raise UserError(_("Cancel request reason is required."))

        # Validate that approvers are selected
        if not self.ks_cancel_pm1_id:
            raise UserError(_("Approver 1 must be selected before sending cancel request."))

        config = self._get_approval_config()
        if config.is_dual_approval() and not self.ks_cancel_pm2_id:
            raise UserError(_("Approver 2 must be selected for dual approval mode."))

        self.write({
            'state': 'cancel_pending',
            'ks_cancel_request_reason': reason,
            'ks_cancel_request_user_id': self.env.user.id,
            'ks_cancel_request_date': fields.Datetime.now(),
            'ks_cancel_pm1_approved': False,
            'ks_cancel_pm2_approved': False,
        })

        # Determine approval message based on mode
        if config.is_dual_approval():
            pm1_name = self.ks_cancel_pm1_id.name if self.ks_cancel_pm1_id else ''
            pm2_name = self.ks_cancel_pm2_id.name if self.ks_cancel_pm2_id else ''
            approval_msg = _(
                "Cancellation request submitted by %s. Waiting for approval from %s (PM1) and %s (PM2).\nReason: %s") % (
                               self.env.user.name, pm1_name, pm2_name, reason
                           )
        else:
            pm1_name = self.ks_cancel_pm1_id.name if self.ks_cancel_pm1_id else ''
            approval_msg = _(
                "Cancellation request submitted by %s. Waiting for approval from %s (PM1).\nReason: %s") % (
                               self.env.user.name, pm1_name, reason
                           )

        self.message_post(
            body=approval_msg,
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

        # Subscribe selected PM users
        partner_ids = []
        if self.ks_cancel_pm1_id:
            partner_ids.append(self.ks_cancel_pm1_id.partner_id.id)
        if self.ks_cancel_pm2_id:
            partner_ids.append(self.ks_cancel_pm2_id.partner_id.id)
        if partner_ids:
            self.message_subscribe(partner_ids=partner_ids)

        # Create activities for approvers
        # Create activity for PM1
        if self.ks_cancel_pm1_id:
            summary = self._get_approval_activity_summary('cancel', 'PM1')
            note = self._get_approval_activity_note('cancel', self.name, self.env.user.name, reason)
            self._create_approval_activity(self.ks_cancel_pm1_id, summary, note)

        # In dual approval mode, create activity for PM2 only after PM1 approves

        return True

    def ks_action_approve_cancel(self):
        """PM approves cancel request - open wizard for reason"""
        self.ensure_one()
        if self.state != 'cancel_pending':
            raise UserError(_("Can only approve cancel requests in 'Cancel Pending' state."))
        return self._action_open_approval_reason_wizard('approve_cancel')

    def _ks_do_approve_cancel_with_reason(self, reason, current_user):
        """Execute cancel approval with reason"""
        self.ensure_one()
        if not reason:
            raise UserError(_("Approval reason is required."))

        config = self._get_approval_config()

        # Check which PM is approving
        pm_role = None
        is_pm1_approving = False
        is_pm2_approving = False

        if self.ks_cancel_pm1_id and current_user == self.ks_cancel_pm1_id:
            if self.ks_cancel_pm1_approved:
                raise UserError(_("You have already approved this cancel request."))
            self.ks_cancel_pm1_approved = True
            pm_role = 'PM1 - %s' % self.ks_cancel_pm1_id.name
            is_pm1_approving = True
        elif self.ks_cancel_pm2_id and current_user == self.ks_cancel_pm2_id:
            # Sequential approval: PM2 can only approve if PM1 has already approved
            if not self.ks_cancel_pm1_approved:
                raise UserError(_("PM1 must approve first before PM2 can approve this cancel request."))
            if self.ks_cancel_pm2_approved:
                raise UserError(_("You have already approved this cancel request."))
            self.ks_cancel_pm2_approved = True
            pm_role = 'PM2 - %s' % self.ks_cancel_pm2_id.name
            is_pm2_approving = True
        else:
            raise UserError(_("You are not authorized to approve this cancel request."))

        # Mark current user's activity as done
        self._mark_activity_done(current_user, feedback=_("Approved: %s") % reason)

        # If PM1 approved and dual mode, create activity for PM2
        if is_pm1_approving and config.is_dual_approval() and self.ks_cancel_pm2_id:
            summary = self._get_approval_activity_summary('cancel', 'PM2')
            note = self._get_approval_activity_note('cancel', self.name,
                                                    self.ks_cancel_request_user_id.name if self.ks_cancel_request_user_id else _(
                                                        'Unknown'), self.ks_cancel_request_reason)
            self._create_approval_activity(self.ks_cancel_pm2_id, summary, note)

        # Post message in chatter with reason
        self.message_post(
            body=_(
                "✅ Cancellation Approved\n"
                "Approved by: %s\n"
                "Action: Approved\n"
                "Reason: %s"
            ) % (pm_role, reason),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

        # Check if approval is complete based on mode
        approval_complete = False
        if config.is_dual_approval():
            # Both PMs must approve
            if self.ks_cancel_pm1_approved and self.ks_cancel_pm2_approved:
                approval_complete = True
        else:
            # Single PM approval - PM1 approval is enough
            if self.ks_cancel_pm1_approved:
                approval_complete = True

        if approval_complete:
            # Mark all remaining activities as done (approval complete)
            if self.ks_cancel_pm1_id:
                self._mark_activity_done(self.ks_cancel_pm1_id, feedback=_("Approval completed - Sale Order cancelled"))
            if self.ks_cancel_pm2_id:
                self._mark_activity_done(self.ks_cancel_pm2_id, feedback=_("Approval completed - Sale Order cancelled"))
            # Cancel any draft invoices
            inv = self.invoice_ids.filtered(lambda inv: inv.state == 'draft')
            inv.button_cancel()

            # Cancel the SO
            self.write({'state': 'cancel'})

            if config.is_dual_approval():
                pm1_name = self.ks_cancel_pm1_id.name if self.ks_cancel_pm1_id else ''
                pm2_name = self.ks_cancel_pm2_id.name if self.ks_cancel_pm2_id else ''
                self.message_post(
                    body=_("Sale Order cancelled after both %s (PM1) and %s (PM2) approval.") % (pm1_name, pm2_name),
                    message_type='notification',
                    subtype_xmlid='mail.mt_comment',
                )
            else:
                pm1_name = self.ks_cancel_pm1_id.name if self.ks_cancel_pm1_id else ''
                self.message_post(
                    body=_("Sale Order cancelled after %s (PM1) approval.") % pm1_name,
                    message_type='notification',
                    subtype_xmlid='mail.mt_comment',
                )

            # Send "Sales Order Cancellation Approved" email to user who requested cancellation
            if self.ks_cancel_request_user_id and self.ks_cancel_request_user_id.email:
                template = self.env.ref(
                    'ks_sale_approval.mail_template_sale_order_cancellation_approved',
                    raise_if_not_found=False,
                )
                if template:
                    template.send_mail(self.id, force_send=True)

        return True

    def ks_action_reject_cancel(self):
        """PM rejects cancel request - open wizard for reason"""
        self.ensure_one()
        if self.state != 'cancel_pending':
            raise UserError(_("Can only reject cancel requests in 'Cancel Pending' state."))
        return self._action_open_approval_reason_wizard('reject_cancel')

    def ks_do_reject_cancel(self, reason):
        """Execute cancel rejection with reason"""
        self.ensure_one()
        if not reason:
            raise UserError(_("Rejection reason is required."))

        config = self._get_approval_config()
        current_user = self.env.user

        # Check if user is one of the selected approvers
        if not ((self.ks_cancel_pm1_id and current_user == self.ks_cancel_pm1_id) or
                (self.ks_cancel_pm2_id and current_user == self.ks_cancel_pm2_id)):
            raise UserError(_("You are not authorized to reject this cancel request."))

        # Sequential approval: PM2 can only reject if PM1 has already approved
        if self.ks_cancel_pm2_id and current_user == self.ks_cancel_pm2_id:
            if not self.ks_cancel_pm1_approved:
                raise UserError(_("PM1 must approve first before PM2 can reject this cancel request."))

        # Determine PM role
        pm_role = None
        if self.ks_cancel_pm1_id and current_user == self.ks_cancel_pm1_id:
            pm_role = 'PM1 - %s' % self.ks_cancel_pm1_id.name
        elif self.ks_cancel_pm2_id and current_user == self.ks_cancel_pm2_id:
            pm_role = 'PM2 - %s' % self.ks_cancel_pm2_id.name

        # Mark current user's activity as done
        self._mark_activity_done(current_user, feedback=_("Rejected: %s") % reason)

        # Also mark other approver's activity as done if exists (rejection ends the process)
        if self.ks_cancel_pm1_id and current_user != self.ks_cancel_pm1_id:
            self._mark_activity_done(self.ks_cancel_pm1_id, feedback=_("Request rejected by %s") % current_user.name)
        if self.ks_cancel_pm2_id and current_user != self.ks_cancel_pm2_id:
            self._mark_activity_done(self.ks_cancel_pm2_id, feedback=_("Request rejected by %s") % current_user.name)

        # Return to sale state
        self.write({
            'state': 'sale',
            'ks_cancel_pm1_id': False,
            'ks_cancel_pm2_id': False,
            'ks_cancel_pm1_approved': False,
            'ks_cancel_pm2_approved': False,
            'ks_cancel_request_reason': False,
            'ks_cancel_request_user_id': False,
            'ks_cancel_request_date': False,
        })

        # Post message in chatter with reason
        self.message_post(
            body=_(
                "❌ Cancellation Request Rejected\n"
                "Rejected by: %s\n"
                "Action: Rejected\n"
                "Reason: %s"
            ) % (pm_role or current_user.name, reason),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

        return True

    # ===== Edit Request Methods =====

    def ks_action_request_edit(self):
        """Normal user requests edit permission - opens wizard for reason

        Admin users can edit directly without approval.
        """
        self.ensure_one()

        # Admin users bypass approval - allow direct edit
        if self._is_admin_user():
            self.write({
                'ks_edit_approved': True,
                'ks_edit_request_user_id': self.env.user.id,
                'ks_edit_request_date': fields.Datetime.now(),
            })
            self.message_post(
                body=_("Edit permission granted directly by admin user %s.") % self.env.user.name,
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
            return True

        if self.state != 'sale':
            raise UserError(_("Can only request edit for confirmed Sale Orders."))
        if self.ks_edit_approved:
            raise UserError(_("Edit is already approved. Please complete your edits first."))
        return self._action_open_edit_request_wizard()

    def _action_open_edit_request_wizard(self):
        """Open wizard to select approvers for edit request"""
        self.ensure_one()
        config = self._get_approval_config() if self._has_approval_config() else False
        return {
            'name': _('Product Approval Picker'),
            'type': 'ir.actions.act_window',
            'res_model': 'ks.sale.edit.approval.request.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_ks_sale_order_id': self.id,
                'ks_approval_mode': config.ks_approval_mode if config else 'single',
            },
        }

    def ks_do_request_edit(self, reason):
        """Execute edit request (approvers already selected via wizard)"""
        self.ensure_one()
        if not reason:
            raise UserError(_("Edit request reason is required."))

        # Validate that approvers are selected
        if not self.ks_edit_pm1_id:
            raise UserError(_("Approver 1 must be selected before sending edit request."))

        config = self._get_approval_config()
        if config.is_dual_approval() and not self.ks_edit_pm2_id:
            raise UserError(_("Approver 2 must be selected for dual approval mode."))

        self.write({
            'state': 'edit_pending',
            'ks_edit_request_reason': reason,
            'ks_edit_request_user_id': self.env.user.id,
            'ks_edit_request_date': fields.Datetime.now(),
            'ks_edit_pm1_approved': False,
            'ks_edit_pm2_approved': False,
            'ks_edit_approved': False,
        })

        # Determine approval message based on mode
        if config.is_dual_approval():
            pm1_name = self.ks_edit_pm1_id.name if self.ks_edit_pm1_id else ''
            pm2_name = self.ks_edit_pm2_id.name if self.ks_edit_pm2_id else ''
            approval_msg = _(
                "Edit request submitted by %s. Waiting for approval from %s (PM1) and %s (PM2).\nReason: %s") % (
                               self.env.user.name, pm1_name, pm2_name, reason
                           )
        else:
            pm1_name = self.ks_edit_pm1_id.name if self.ks_edit_pm1_id else ''
            approval_msg = _("Edit request submitted by %s. Waiting for approval from %s (PM1).\nReason: %s") % (
                self.env.user.name, pm1_name, reason
            )

        self.message_post(
            body=approval_msg,
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

        # Subscribe selected PM users
        partner_ids = []
        if self.ks_edit_pm1_id:
            partner_ids.append(self.ks_edit_pm1_id.partner_id.id)
        if self.ks_edit_pm2_id:
            partner_ids.append(self.ks_edit_pm2_id.partner_id.id)
        if partner_ids:
            self.message_subscribe(partner_ids=partner_ids)

        # Create activities for approvers
        # Create activity for PM1
        if self.ks_edit_pm1_id:
            summary = self._get_approval_activity_summary('edit', 'PM1')
            note = self._get_approval_activity_note('edit', self.name, self.env.user.name, reason)
            self._create_approval_activity(self.ks_edit_pm1_id, summary, note)

        # In dual approval mode, create activity for PM2 only after PM1 approves

        return True

    def ks_action_approve_edit(self):
        """PM approves edit request - open wizard for reason"""
        self.ensure_one()
        if self.state != 'edit_pending':
            raise UserError(_("Can only approve edit requests in 'Edit Approval Pending' state."))
        return self._action_open_approval_reason_wizard('approve_edit')

    def _ks_do_approve_edit_with_reason(self, reason, current_user):
        """Execute edit approval with reason"""
        self.ensure_one()
        if not reason:
            raise UserError(_("Approval reason is required."))

        config = self._get_approval_config()

        # Check which PM is approving
        pm_role = None
        is_pm1_approving = False
        is_pm2_approving = False

        if self.ks_edit_pm1_id and current_user == self.ks_edit_pm1_id:
            if self.ks_edit_pm1_approved:
                raise UserError(_("You have already approved this edit request."))
            self.ks_edit_pm1_approved = True
            pm_role = 'PM1 - %s' % self.ks_edit_pm1_id.name
            is_pm1_approving = True
        elif self.ks_edit_pm2_id and current_user == self.ks_edit_pm2_id:
            # Sequential approval: PM2 can only approve if PM1 has already approved
            if not self.ks_edit_pm1_approved:
                raise UserError(_("PM1 must approve first before PM2 can approve this edit request."))
            if self.ks_edit_pm2_approved:
                raise UserError(_("You have already approved this edit request."))
            self.ks_edit_pm2_approved = True
            pm_role = 'PM2 - %s' % self.ks_edit_pm2_id.name
            is_pm2_approving = True
        else:
            raise UserError(_("You are not authorized to approve this edit request."))

        # Mark current user's activity as done
        self._mark_activity_done(current_user, feedback=_("Approved: %s") % reason)

        # If PM1 approved and dual mode, create activity for PM2
        if is_pm1_approving and config.is_dual_approval() and self.ks_edit_pm2_id:
            summary = self._get_approval_activity_summary('edit', 'PM2')
            note = self._get_approval_activity_note('edit', self.name,
                                                    self.ks_edit_request_user_id.name if self.ks_edit_request_user_id else _(
                                                        'Unknown'), self.ks_edit_request_reason)
            self._create_approval_activity(self.ks_edit_pm2_id, summary, note)

        # Post message in chatter with reason
        self.message_post(
            body=_(
                "✅ Edit Approved\n"
                "Approved by: %s\n"
                "Action: Approved\n"
                "Reason: %s"
            ) % (pm_role, reason),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

        # Check if approval is complete based on mode
        approval_complete = False
        if config.is_dual_approval():
            # Both PMs must approve
            if self.ks_edit_pm1_approved and self.ks_edit_pm2_approved:
                approval_complete = True
        else:
            # Single PM approval - PM1 approval is enough
            if self.ks_edit_pm1_approved:
                approval_complete = True

        if approval_complete:
            # Mark all remaining activities as done (approval complete)
            if self.ks_edit_pm1_id:
                self._mark_activity_done(self.ks_edit_pm1_id,
                                         feedback=_("Approval completed - Edit permission granted"))
            if self.ks_edit_pm2_id:
                self._mark_activity_done(self.ks_edit_pm2_id,
                                         feedback=_("Approval completed - Edit permission granted"))
            # Both approved - unlock the SO so the requester can edit
            self.action_unlock()
            self.write({
                'state': 'sale',
                'ks_edit_approved': True,
            })

            # Trigger recomputation of ks_can_edit_price on order lines
            if self.order_line:
                self.order_line._compute_ks_can_edit_price()

            if config.is_dual_approval():
                pm1_name = self.ks_edit_pm1_id.name if self.ks_edit_pm1_id else ''
                pm2_name = self.ks_edit_pm2_id.name if self.ks_edit_pm2_id else ''
                self.message_post(
                    body=_("Edit approved by both %s (PM1) and %s (PM2). %s can now edit this Sale Order.") % (
                        pm1_name, pm2_name, self.ks_edit_request_user_id.name
                    ),
                    message_type='notification',
                    subtype_xmlid='mail.mt_comment',
                )
            else:
                pm1_name = self.ks_edit_pm1_id.name if self.ks_edit_pm1_id else ''
                self.message_post(
                    body=_("Edit approved by %s (PM1). %s can now edit this Sale Order.") % (
                        pm1_name, self.ks_edit_request_user_id.name
                    ),
                    message_type='notification',
                    subtype_xmlid='mail.mt_comment',
                )

            # Send "Sales Order Update Request Approved" email to user who requested the update
            if self.ks_edit_request_user_id and self.ks_edit_request_user_id.email:
                template = self.env.ref(
                    'ks_sale_approval.mail_template_sale_order_update_approved',
                    raise_if_not_found=False,
                )
                if template:
                    template.send_mail(self.id, force_send=True)

        return True

    def ks_action_reject_edit(self):
        """PM rejects edit request - open wizard for reason"""
        self.ensure_one()
        if self.state != 'edit_pending':
            raise UserError(_("Can only reject edit requests in 'Edit Approval Pending' state."))
        return self._action_open_approval_reason_wizard('reject_edit')

    def ks_do_reject_edit(self, reason):
        """Execute edit rejection with reason"""
        self.ensure_one()
        if not reason:
            raise UserError(_("Rejection reason is required."))

        config = self._get_approval_config()
        current_user = self.env.user

        # Check if user is one of the selected approvers
        if not ((self.ks_edit_pm1_id and current_user == self.ks_edit_pm1_id) or
                (self.ks_edit_pm2_id and current_user == self.ks_edit_pm2_id)):
            raise UserError(_("You are not authorized to reject this edit request."))

        # Sequential approval: PM2 can only reject if PM1 has already approved
        if self.ks_edit_pm2_id and current_user == self.ks_edit_pm2_id:
            if not self.ks_edit_pm1_approved:
                raise UserError(_("PM1 must approve first before PM2 can reject this edit request."))

        # Determine PM role
        pm_role = None
        if self.ks_edit_pm1_id and current_user == self.ks_edit_pm1_id:
            pm_role = 'PM1 - %s' % self.ks_edit_pm1_id.name
        elif self.ks_edit_pm2_id and current_user == self.ks_edit_pm2_id:
            pm_role = 'PM2 - %s' % self.ks_edit_pm2_id.name

        # Mark current user's activity as done
        self._mark_activity_done(current_user, feedback=_("Rejected: %s") % reason)

        # Also mark other approver's activity as done if exists (rejection ends the process)
        if self.ks_edit_pm1_id and current_user != self.ks_edit_pm1_id:
            self._mark_activity_done(self.ks_edit_pm1_id, feedback=_("Request rejected by %s") % current_user.name)
        if self.ks_edit_pm2_id and current_user != self.ks_edit_pm2_id:
            self._mark_activity_done(self.ks_edit_pm2_id, feedback=_("Request rejected by %s") % current_user.name)

        # Return to sale state
        self.write({
            'state': 'sale',
            'ks_edit_pm1_id': False,
            'ks_edit_pm2_id': False,
            'ks_edit_pm1_approved': False,
            'ks_edit_pm2_approved': False,
            'ks_edit_request_reason': False,
            'ks_edit_request_user_id': False,
            'ks_edit_request_date': False,
            'ks_edit_approved': False,
        })

        # Post message in chatter with reason
        self.message_post(
            body=_(
                "❌ Edit Request Rejected\n"
                "Rejected by: %s\n"
                "Action: Rejected\n"
                "Reason: %s"
            ) % (pm_role or current_user.name, reason),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

        return True

    def ks_action_complete_edit(self):
        """User completes editing after edit approval - lock SO again"""
        self.ensure_one()
        if not self.ks_edit_approved:
            raise UserError(_("No pending edit to complete."))
        if self.ks_edit_request_user_id != self.env.user:
            raise UserError(_("Only the user who requested the edit can complete it."))

        self.write({
            'ks_edit_pm1_id': False,
            'ks_edit_pm2_id': False,
            'ks_edit_approved': False,
            'ks_edit_request_reason': False,
            'ks_edit_request_user_id': False,
            'ks_edit_request_date': False,
            'ks_edit_pm1_approved': False,
            'ks_edit_pm2_approved': False,
        })

        # Re-lock the SO after edit is complete
        self.action_lock()

        # Trigger recomputation of ks_can_edit_price on order lines
        if self.order_line:
            self.order_line._compute_ks_can_edit_price()

        self.message_post(
            body=_("Edit completed by %s. Sale Order is now locked.") % self.env.user.name,
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

        return True

    # ===== Activity Management Methods =====

    # Keyword used in activity summaries for each workflow type.
    # Changing a summary in _get_approval_activity_summary must be reflected here.
    _APPROVAL_TYPE_KEYWORD = {
        'confirm': 'Confirm',
        'cancel': 'Cancel',
        'edit': 'Edit',
    }

    def _ks_cancel_workflow_activities(self, approval_type, mark_done=False, feedback=None):
        """Cancel pending activities that belong to one specific approval workflow.

        This is the ONLY method that should be called to remove/complete approval
        activities.  It uses both the activity-type record AND a summary keyword
        so that — even when the same PM user appears in multiple workflows — only
        the activities created for *this* workflow are touched.

        :param approval_type: 'confirm' | 'cancel' | 'edit'
        :param mark_done: True  → action_feedback (leaves a chatter entry, used for
                                  full cancellations / rejections)
                          False → unlink (silent removal, used for 'Update' resets)
        :param feedback: feedback string passed to action_feedback when mark_done=True
        """
        self.ensure_one()
        keyword = self._APPROVAL_TYPE_KEYWORD.get(approval_type, '')

        # Determine which PM IDs were assigned to this workflow
        pm_map = {
            'confirm': (self.ks_confirm_pm1_id, self.ks_confirm_pm2_id),
            'cancel':  (self.ks_cancel_pm1_id,  self.ks_cancel_pm2_id),
            'edit':    (self.ks_edit_pm1_id,     self.ks_edit_pm2_id),
        }
        pm1, pm2 = pm_map.get(approval_type, (False, False))
        user_ids = [u.id for u in (pm1, pm2) if u]

        # Base domain: this SO, approval activity type, matching summary keyword
        activity_type_rec = self.env.ref(
            'ks_sale_approval.mail_activity_data_sale_approval', raise_if_not_found=False
        )
        domain = [
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('active', '=', True),
        ]
        if activity_type_rec:
            domain.append(('activity_type_id', '=', activity_type_rec.id))
        if keyword:
            domain.append(('summary', 'ilike', keyword))
        if user_ids:
            domain.append(('user_id', 'in', user_ids))

        activities = self.env['mail.activity'].search(domain)
        if not activities:
            return True

        if mark_done:
            activities.action_feedback(feedback=feedback or '')
        else:
            activities.sudo().unlink()
        return True

    def _create_approval_activity(self, user_id, summary, note=None, activity_type='mail.mail_activity_data_todo'):
        """Create an activity for approval request

        :param user_id: res.users record - user to assign activity to
        :param summary: string - activity summary/title
        :param note: string - optional note/description
        :param activity_type: string - activity type xmlid (default: todo)
        :return: mail.activity record
        """
        self.ensure_one()
        if not user_id:
            return False

        activity_type_id = self.env.ref(activity_type, raise_if_not_found=False)
        if not activity_type_id:
            # Fallback to default todo activity type
            activity_type_id = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)

        if not activity_type_id:
            return False

        activity_vals = {
            'res_id': self.id,
            'res_model_id': self.env['ir.model']._get_id('sale.order'),
            'activity_type_id': activity_type_id.id,
            'user_id': user_id.id,
            'summary': summary,
            'date_deadline': fields.Date.today(),
        }
        if note:
            activity_vals['note'] = note

        activity = self.env['mail.activity'].create(activity_vals)
        return activity

    def _mark_activity_done(self, user_id, feedback=None, summary_keyword=None):
        """Mark pending activities for this user as done.

        :param user_id: res.users record
        :param feedback: optional feedback message shown in chatter
        :param summary_keyword: optional string — when supplied only activities
               whose summary contains this keyword are matched.  Use the
               approval_type keyword ('Confirm', 'Cancel', 'Edit') to make the
               operation type-specific and avoid touching unrelated activities.
        """
        self.ensure_one()
        if not user_id:
            return True

        domain = [
            ('res_id', '=', self.id),
            ('res_model', '=', 'sale.order'),
            ('user_id', '=', user_id.id),
            ('active', '=', True),
        ]
        if summary_keyword:
            domain.append(('summary', 'ilike', summary_keyword))

        activities = self.env['mail.activity'].search(domain)
        if activities:
            activities.action_feedback(feedback=feedback or '')
        return True

    def _get_approval_activity_summary(self, approval_type, pm_role=None):
        """Get activity summary text based on approval type

        :param approval_type: string - 'confirm', 'cancel', or 'edit'
        :param pm_role: string - optional PM role (PM1/PM2)
        :return: string - activity summary
        """
        summaries = {
            'confirm': _('Sale Order Approval Required'),
            'cancel': _('Sale Order Cancellation Approval Required'),
            'edit': _('Sale Order Edit Approval Required'),
        }
        base_summary = summaries.get(approval_type, _('Sale Order Approval Required'))
        if pm_role:
            return f"{base_summary} ({pm_role})"
        return base_summary

    def _get_approval_activity_note(self, approval_type, order_ref, requester_name, reason=None):
        """Get activity note/description

        :param approval_type: string - 'confirm', 'cancel', or 'edit'
        :param order_ref: string - sale order reference/name
        :param requester_name: string - name of user who requested
        :param reason: string - optional reason
        :return: string - activity note
        """
        notes = {
            'confirm': _('Sale Order %s requires your approval for confirmation.\nRequested by: %s') % (order_ref,
                                                                                                        requester_name),
            'cancel': _('Sale Order %s requires your approval for cancellation.\nRequested by: %s') % (order_ref,
                                                                                                       requester_name),
            'edit': _('Sale Order %s requires your approval for editing.\nRequested by: %s') % (order_ref,
                                                                                                requester_name),
        }
        base_note = notes.get(approval_type, _('Sale Order %s requires your approval.\nRequested by: %s') % (order_ref,
                                                                                                             requester_name))
        if reason:
            base_note += f"\n\nReason: {reason}"
        return base_note

    # ===== Wizard Helpers =====

    def _action_open_approval_reason_wizard(self, action_type):
        """Open wizard to enter reason for approval/rejection"""
        self.ensure_one()
        return {
            'name': _('Enter Reason'),
            'type': 'ir.actions.act_window',
            'res_model': 'ks.sale.approval.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_ks_sale_order_id': self.id,
                'default_ks_action_type': action_type,
            },
        }

    def _action_open_reject_reason_wizard(self, rejection_type):
        """Open wizard to enter reason for rejection (legacy - kept for backward compatibility)"""
        self.ensure_one()
        return {
            'name': _('Enter Rejection Reason'),
            'type': 'ir.actions.act_window',
            'res_model': 'ks.sale.reject.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_ks_sale_order_id': self.id,
                'default_ks_action_type': 'reject_' + rejection_type,
            },
        }

