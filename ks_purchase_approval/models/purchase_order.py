# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Override state field to add new states
    state = fields.Selection(
        selection_add=[
            ('pending_approval', 'Pending Approval'),
            ('update_requested', 'Update Requested'),
            ('cancel_requested', 'Cancel Requested'),
            ('purchase',),  # This ensures proper ordering
        ],
        ondelete={
            'pending_approval': 'set default',
            'update_requested': 'set default',
            'cancel_requested': 'set default',
        }
    )

    # ===== Confirmation Approval Fields =====
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
    ks_confirm_pm1_reason = fields.Text(
        string='PM1 Confirmation Reason',
        copy=False,
    )
    ks_confirm_pm2_reason = fields.Text(
        string='PM2 Confirmation Reason',
        copy=False,
    )

    # ===== Update Approval Fields =====
    ks_update_pm1_approved = fields.Boolean(
        string='PM1 Update Approved',
        default=False,
        copy=False,
        tracking=True,
    )
    ks_update_pm2_approved = fields.Boolean(
        string='PM2 Update Approved',
        default=False,
        copy=False,
        tracking=True,
    )
    ks_update_request_reason = fields.Text(
        string='Update Request Reason',
        copy=False,
    )
    ks_update_request_user_id = fields.Many2one(
        'res.users',
        string='Update Requested By',
        copy=False,
    )
    ks_update_request_date = fields.Datetime(
        string='Update Request Date',
        copy=False,
    )
    ks_update_approved = fields.Boolean(
        string='Update Approved (Editable)',
        default=False,
        copy=False,
        help='When True, the original requester can edit the PO',
    )

    # ===== Cancel Approval Fields =====
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
        string='Can Edit PO',
        compute='_compute_ks_can_edit',
    )
    
    # Button visibility fields
    ks_show_request_update_button = fields.Boolean(
        string='Show Request Update Button',
        compute='_compute_ks_button_visibility',
    )
    ks_show_request_cancel_button = fields.Boolean(
        string='Show Request Cancel Button',
        compute='_compute_ks_button_visibility',
    )
    ks_show_approve_confirm_button = fields.Boolean(
        string='Show Approve Confirmation Button',
        compute='_compute_ks_button_visibility',
    )
    ks_show_reject_confirm_button = fields.Boolean(
        string='Show Reject Confirmation Button',
        compute='_compute_ks_button_visibility',
    )
    ks_show_approve_update_button = fields.Boolean(
        string='Show Approve Update Button',
        compute='_compute_ks_button_visibility',
    )
    ks_show_reject_update_button = fields.Boolean(
        string='Show Reject Update Button',
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
    ks_show_unlock_button = fields.Boolean(
        string='Show Unlock Button',
        compute='_compute_ks_button_visibility',
    )
    ks_show_complete_update_button = fields.Boolean(
        string='Show Complete Update Button',
        compute='_compute_ks_button_visibility',
    )

    # ===== Helper Methods =====
    def _get_approval_config(self):
        """Get approval configuration for current company"""
        config = self.env['ks.purchase.approval.config'].get_config(self.company_id.id)
        if not config:
            raise UserError(_(
                "No approval configuration found for company '%s'. "
                "Please configure PM approvers in Purchase > Configuration > Approval Configuration."
            ) % self.company_id.name)
        return config

    def _has_approval_config(self):
        """Check if approval config exists without raising error"""
        config = self.env['ks.purchase.approval.config'].get_config(self.company_id.id)
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

    @api.depends('state', 'ks_is_pm_user', 'ks_update_approved', 'ks_update_request_user_id')
    @api.depends_context('uid')
    def _compute_ks_can_edit(self):
        """
        Determine if current user can edit the PO
        
        Rules:
        - Draft/Sent: Everyone can edit
        - Pending Approval: No one can edit (locked)
        - Update Requested: No one can edit (locked)
        - Cancel Requested: No one can edit (locked)
        - Purchase (Confirmed): 
            - Normal users: CANNOT edit (locked) UNLESS update was approved for them
            - PM users: Can edit (they have full control)
        - Done (Locked): No one can edit
        """
        for order in self:
            current_user = self.env.user
            
            if order.state in ['draft', 'sent']:
                # Draft and Sent - everyone can edit
                order.ks_can_edit = True
            elif order.state in ['pending_approval', 'update_requested', 'cancel_requested']:
                # All approval states - locked for everyone
                order.ks_can_edit = False
            elif order.state == 'purchase':
                # Confirmed state
                if order.ks_is_pm_user:
                    # PM users can always edit confirmed POs
                    order.ks_can_edit = True
                elif order.ks_update_approved and order.ks_update_request_user_id == current_user:
                    # Normal user who requested update AND it was approved
                    order.ks_can_edit = True
                else:
                    # Normal users cannot edit confirmed POs
                    order.ks_can_edit = False
            elif order.state == 'done':
                # Locked state - only PM can unlock first
                order.ks_can_edit = False
            else:
                order.ks_can_edit = False

    @api.depends('state', 'ks_is_pm_user', 'ks_is_normal_user',
                 'ks_confirm_pm1_approved', 'ks_confirm_pm2_approved',
                 'ks_update_pm1_approved', 'ks_update_pm2_approved', 'ks_update_approved',
                 'ks_cancel_pm1_approved', 'ks_cancel_pm2_approved',
                 'ks_update_request_user_id')
    @api.depends_context('uid')
    def _compute_ks_button_visibility(self):
        """Compute visibility of all action buttons"""
        for order in self:
            # Reset all
            order.ks_show_request_update_button = False
            order.ks_show_request_cancel_button = False
            order.ks_show_approve_confirm_button = False
            order.ks_show_reject_confirm_button = False
            order.ks_show_approve_update_button = False
            order.ks_show_reject_update_button = False
            order.ks_show_approve_cancel_button = False
            order.ks_show_reject_cancel_button = False
            order.ks_show_unlock_button = False
            order.ks_show_complete_update_button = False

            if not order._has_approval_config():
                continue

            config = order._get_approval_config()
            current_user = self.env.user
            is_pm = order.ks_is_pm_user
            is_normal = order.ks_is_normal_user

            # === NORMAL USER BUTTONS ===
            if is_normal:
                # Request Update button - only when PO is confirmed and no pending update
                if order.state == 'purchase' and not order.ks_update_approved:
                    order.ks_show_request_update_button = True
                
                # Request Cancel button - only when PO is confirmed
                if order.state == 'purchase':
                    order.ks_show_request_cancel_button = True

                # Complete Update button - when update is approved for this user
                if (order.state == 'purchase' and 
                    order.ks_update_approved and 
                    order.ks_update_request_user_id == current_user):
                    order.ks_show_complete_update_button = True

            # === PM USER BUTTONS ===
            if is_pm:
                # Confirmation approval buttons
                if order.state == 'pending_approval':
                    # Check if this PM can still approve (hasn't approved yet)
                    can_approve = False
                    if current_user == config.ks_confirm_pm1_id and not order.ks_confirm_pm1_approved:
                        can_approve = True
                    elif current_user == config.ks_confirm_pm2_id and not order.ks_confirm_pm2_approved:
                        can_approve = True
                    
                    if can_approve:
                        order.ks_show_approve_confirm_button = True
                        order.ks_show_reject_confirm_button = True

                # Update approval buttons
                if order.state == 'update_requested':
                    can_approve = False
                    if current_user == config.ks_update_pm1_id and not order.ks_update_pm1_approved:
                        can_approve = True
                    elif current_user == config.ks_update_pm2_id and not order.ks_update_pm2_approved:
                        can_approve = True
                    
                    if can_approve:
                        order.ks_show_approve_update_button = True
                        order.ks_show_reject_update_button = True

                # Cancel approval buttons
                if order.state == 'cancel_requested':
                    can_approve = False
                    if current_user == config.ks_cancel_pm1_id and not order.ks_cancel_pm1_approved:
                        can_approve = True
                    elif current_user == config.ks_cancel_pm2_id and not order.ks_cancel_pm2_approved:
                        can_approve = True
                    
                    if can_approve:
                        order.ks_show_approve_cancel_button = True
                        order.ks_show_reject_cancel_button = True

                # Unlock button - ONLY for PM users when PO is in 'done' (locked) state
                if order.state == 'done':
                    order.ks_show_unlock_button = True

    # ===== Action Methods =====
    
    def button_confirm(self):
        """
        Override: 
        - PM users: Confirm immediately (standard flow)
        - Normal users: Show popup before sending to Pending Approval
        """
        # Handle single record for popup
        if len(self) == 1:
            order = self
            if order.state not in ['draft', 'sent']:
                return super().button_confirm()
            
            # Validate analytic distribution
            order.order_line._validate_analytic_distribution()
            order._add_supplier_to_product()
            
            # Check if approval config exists
            if not order._has_approval_config():
                # No config, use standard behavior
                return super().button_confirm()
            
            config = order._get_approval_config()
            is_pm = self.env.user in config.get_all_pm_users()
            
            if is_pm:
                # PM users can directly confirm - call original method
                if order._approval_allowed():
                    order.button_approve()
                else:
                    order.write({'state': 'to approve'})
                if order.partner_id not in order.message_partner_ids:
                    order.message_subscribe([order.partner_id.id])
                return True
            else:
                # Normal user - show popup before sending to Pending Approval
                return order._action_open_approval_confirmation_wizard()
        
        # Multiple records - process each
        for order in self:
            if order.state not in ['draft', 'sent']:
                continue
            
            # Validate analytic distribution
            order.order_line._validate_analytic_distribution()
            order._add_supplier_to_product()
            
            # Check if approval config exists
            if not order._has_approval_config():
                # No config, use standard behavior
                continue
            
            config = order._get_approval_config()
            is_pm = self.env.user in config.get_all_pm_users()
            
            if is_pm:
                # PM users can directly confirm
                if order._approval_allowed():
                    order.button_approve()
                else:
                    order.write({'state': 'to approve'})
                if order.partner_id not in order.message_partner_ids:
                    order.message_subscribe([order.partner_id.id])
            else:
                # For multiple records, normal users need to process one at a time
                # This is a limitation - popup only works for single record
                order._ks_send_to_pending_approval()
        
        return True

    def _ks_send_to_pending_approval(self):
        """Normal user sends PO to pending approval - called after popup confirmation"""
        self.ensure_one()
        if self.state not in ['draft', 'sent']:
            raise UserError(_("Can only request confirmation for Draft or Sent orders."))
        
        config = self._get_approval_config()
        pm1_name = config.ks_confirm_pm1_id.name if config.ks_confirm_pm1_id else 'PM1'
        pm2_name = config.ks_confirm_pm2_id.name if config.ks_confirm_pm2_id else 'PM2'
        
        self.write({
            'state': 'pending_approval',
            'ks_confirm_request_user_id': self.env.user.id,
            'ks_confirm_request_date': fields.Datetime.now(),
            'ks_confirm_pm1_approved': False,
            'ks_confirm_pm2_approved': False,
            'ks_confirm_pm1_reason': False,
            'ks_confirm_pm2_reason': False,
        })
        
        # Log in chatter with actual PM names
        self.message_post(
            body=_("Confirmation request submitted by %s. Waiting for approval from: PM1 - %s,  PM2 - %s.") % (
                self.env.user.name,
                pm1_name,
                pm2_name,
            ),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        # Subscribe PM users
        self.message_subscribe(partner_ids=[
            config.ks_confirm_pm1_id.partner_id.id,
            config.ks_confirm_pm2_id.partner_id.id,
        ])
        
        return True

    def ks_action_approve_confirmation(self):
        """PM approves confirmation request - opens wizard for reason"""
        self.ensure_one()
        if self.state != 'pending_approval':
            raise UserError(_("Can only approve orders in 'Pending Approval' state."))
        
        config = self._get_approval_config()
        current_user = self.env.user
        
        # Check authorization
        if current_user not in (config.ks_confirm_pm1_id | config.ks_confirm_pm2_id):
            raise UserError(_("You are not authorized to approve this confirmation request."))
        
        # Check if already approved
        if current_user == config.ks_confirm_pm1_id and self.ks_confirm_pm1_approved:
            raise UserError(_("You have already approved this confirmation request."))
        if current_user == config.ks_confirm_pm2_id and self.ks_confirm_pm2_approved:
            raise UserError(_("You have already approved this confirmation request."))
        
        # Open wizard for reason
        try:
            view_id = self.env.ref('ks_purchase_approval.ks_approve_confirmation_reason_wizard_form_view').id
        except ValueError:
            view_id = False
        return {
            'name': _('Approve Confirmation'),
            'type': 'ir.actions.act_window',
            'res_model': 'ks.approve.confirmation.reason.wizard',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'context': {
                'default_ks_purchase_order_id': self.id,
            },
        }

    def ks_do_approve_confirmation(self, reason):
        """Execute confirmation approval with reason"""
        self.ensure_one()
        if not reason:
            raise UserError(_("Reason for confirmation is required."))
        
        if self.state != 'pending_approval':
            raise UserError(_("Can only approve orders in 'Pending Approval' state."))
        
        config = self._get_approval_config()
        current_user = self.env.user
        
        if current_user == config.ks_confirm_pm1_id:
            if self.ks_confirm_pm1_approved:
                raise UserError(_("You have already approved this confirmation request."))
            self.write({
                'ks_confirm_pm1_approved': True,
                'ks_confirm_pm1_reason': reason,
            })
            self.message_post(
                body=_("%s approved the PO. Reason: %s") % (current_user.name, reason),
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
        elif current_user == config.ks_confirm_pm2_id:
            if self.ks_confirm_pm2_approved:
                raise UserError(_("You have already approved this confirmation request."))
            self.write({
                'ks_confirm_pm2_approved': True,
                'ks_confirm_pm2_reason': reason,
            })
            self.message_post(
                body=_("%s approved the PO. Reason: %s") % (current_user.name, reason),
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
        else:
            raise UserError(_("You are not authorized to approve this confirmation request."))
        
        # Check if both PMs have approved
        if self.ks_confirm_pm1_approved and self.ks_confirm_pm2_approved:
            # Both approved - confirm the PO using standard flow to ensure receipt creation
            # Ensure validation is done (should already be done, but ensure it)
            self.order_line._validate_analytic_distribution()
            self._add_supplier_to_product()
            
            # Set state to 'purchase' and date_approve (standard confirmation)
            self.write({
                'state': 'purchase',
                'date_approve': fields.Datetime.now(),
            })
            
            # Create stock pickings (receipts) if purchase_stock module is installed
            # This ensures receipts are created just like in standard Odoo flow
            if hasattr(self, '_create_picking'):
                self._create_picking()
            
            # Handle PO lock if configured
            if self.company_id.po_lock == 'lock':
                self.write({'state': 'done'})
            
            self.message_post(
                body=_("Purchase Order confirmed after both PM1 and PM2 approval."),
                message_type='notification',
                subtype_xmlid='mail.mt_comment',
            )
            
            if self.partner_id not in self.message_partner_ids:
                self.message_subscribe([self.partner_id.id])
        
        return True

    def ks_action_reject_confirmation(self):
        """PM rejects confirmation request - open wizard for reason"""
        self.ensure_one()
        if self.state != 'pending_approval':
            raise UserError(_("Can only reject orders in 'Pending Approval' state."))
        return self._action_open_reject_reason_wizard('confirm')

    def ks_do_reject_confirmation(self, reason):
        """Execute confirmation rejection"""
        self.ensure_one()
        if not reason:
            raise UserError(_("Rejection reason is required."))
        
        config = self._get_approval_config()
        current_user = self.env.user
        
        if current_user not in (config.ks_confirm_pm1_id | config.ks_confirm_pm2_id):
            raise UserError(_("You are not authorized to reject this confirmation request."))
        
        # Reset to draft state
        self.write({
            'state': 'draft',
            'ks_confirm_pm1_approved': False,
            'ks_confirm_pm2_approved': False,
            'ks_confirm_request_user_id': False,
            'ks_confirm_request_date': False,
        })
        
        self.message_post(
            body=_("Confirmation rejected by %s. Reason: %s") % (current_user.name, reason),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        return True

    # ===== Update Request Methods =====
    
    def ks_action_request_update(self):
        """Normal user requests update permission - opens wizard for reason"""
        self.ensure_one()
        if self.state != 'purchase':
            raise UserError(_("Can only request update for confirmed Purchase Orders."))
        if self.ks_update_approved:
            raise UserError(_("Update is already approved. Please complete your edits first."))
        return self._action_open_request_reason_wizard('update')

    def ks_do_request_update(self, reason):
        """Execute update request"""
        self.ensure_one()
        if not reason:
            raise UserError(_("Update request reason is required."))

        config = self._get_approval_config()
        pm1_name = config.ks_update_pm1_id.name if config.ks_update_pm1_id else 'PM1'
        pm2_name = config.ks_update_pm2_id.name if config.ks_update_pm2_id else 'PM2'

        self.write({
            'state': 'update_requested',
            'ks_update_request_reason': reason,
            'ks_update_request_user_id': self.env.user.id,
            'ks_update_request_date': fields.Datetime.now(),
            'ks_update_pm1_approved': False,
            'ks_update_pm2_approved': False,
            'ks_update_approved': False,
        })
        
        self.message_post(
            body=_("Update request submitted by %s. Waiting for approval from: PM1 - %s, PM2 - %s. Reason: %s") % (
                self.env.user.name,
                pm1_name,
                pm2_name,
                reason,
            ),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        # Subscribe PM users
        self.message_subscribe(partner_ids=[
            config.ks_update_pm1_id.partner_id.id,
            config.ks_update_pm2_id.partner_id.id,
        ])
        
        return True

    def ks_action_approve_update(self):
        """PM approves update request"""
        self.ensure_one()
        if self.state != 'update_requested':
            raise UserError(_("Can only approve update requests in 'Update Requested' state."))
        config = self._get_approval_config()
        current_user = self.env.user

        # Authorization / duplicate checks remain the same
        if current_user == config.ks_update_pm1_id and self.ks_update_pm1_approved:
            raise UserError(_("You have already approved this update request."))
        if current_user == config.ks_update_pm2_id and self.ks_update_pm2_approved:
            raise UserError(_("You have already approved this update request."))
        if current_user not in (config.ks_update_pm1_id | config.ks_update_pm2_id):
            raise UserError(_("You are not authorized to approve this update request."))

        # Open reason popup (wizard)
        try:
            view_id = self.env.ref('ks_purchase_approval.ks_approve_update_reason_wizard_form_view').id
        except ValueError:
            view_id = False
        return {
            'name': _('Approve Update'),
            'type': 'ir.actions.act_window',
            'res_model': 'ks.approve.update.reason.wizard',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'context': {
                'default_ks_purchase_order_id': self.id,
            },
        }

    def ks_do_approve_update(self, reason):
        """Execute update approval with reason (called from wizard)"""
        self.ensure_one()
        if not reason:
            raise UserError(_("Reason for approval is required."))
        if self.state != 'update_requested':
            raise UserError(_("Can only approve update requests in 'Update Requested' state."))

        config = self._get_approval_config()
        current_user = self.env.user

        if current_user == config.ks_update_pm1_id:
            if self.ks_update_pm1_approved:
                raise UserError(_("You have already approved this update request."))
            self.ks_update_pm1_approved = True
            self.message_post(
                body=_("Update approved by PM1: %s. Reason: %s") % (current_user.name, reason),
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
        elif current_user == config.ks_update_pm2_id:
            if self.ks_update_pm2_approved:
                raise UserError(_("You have already approved this update request."))
            self.ks_update_pm2_approved = True
            self.message_post(
                body=_("Update approved by PM2: %s. Reason: %s") % (current_user.name, reason),
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
        else:
            raise UserError(_("You are not authorized to approve this update request."))
        
        # Check if both PMs have approved
        if self.ks_update_pm1_approved and self.ks_update_pm2_approved:
            # Both approved - allow editing
            self.write({
                'state': 'purchase',
                'ks_update_approved': True,
            })
            
            self.message_post(
                body=_("Update approved by both PM1 and PM2. %s can now edit this PO.") % (
                    self.ks_update_request_user_id.name
                ),
                message_type='notification',
                subtype_xmlid='mail.mt_comment',
            )
        
        return True

    def ks_action_reject_update(self):
        """PM rejects update request - open wizard for reason"""
        self.ensure_one()
        if self.state != 'update_requested':
            raise UserError(_("Can only reject update requests in 'Update Requested' state."))
        return self._action_open_reject_reason_wizard('update')

    def ks_do_reject_update(self, reason):
        """Execute update rejection"""
        self.ensure_one()
        if not reason:
            raise UserError(_("Rejection reason is required."))
        
        config = self._get_approval_config()
        current_user = self.env.user
        
        if current_user not in (config.ks_update_pm1_id | config.ks_update_pm2_id):
            raise UserError(_("You are not authorized to reject this update request."))
        
        # Return to purchase state
        self.write({
            'state': 'purchase',
            'ks_update_pm1_approved': False,
            'ks_update_pm2_approved': False,
            'ks_update_request_reason': False,
            'ks_update_request_user_id': False,
            'ks_update_request_date': False,
            'ks_update_approved': False,
        })
        
        self.message_post(
            body=_("Update request rejected by %s. Reason: %s") % (current_user.name, reason),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        return True

    def ks_action_complete_update(self):
        """User completes editing after update approval - lock PO again"""
        self.ensure_one()
        if not self.ks_update_approved:
            raise UserError(_("No pending update to complete."))
        if self.ks_update_request_user_id != self.env.user:
            raise UserError(_("Only the user who requested the update can complete it."))
        
        self.write({
            'ks_update_approved': False,
            'ks_update_request_reason': False,
            'ks_update_request_user_id': False,
            'ks_update_request_date': False,
            'ks_update_pm1_approved': False,
            'ks_update_pm2_approved': False,
        })
        
        self.message_post(
            body=_("Update completed by %s. PO is now locked.") % self.env.user.name,
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        return True

    # ===== Cancel Request Methods =====
    
    def button_cancel(self):
        """Override: Normal users must request cancellation for confirmed POs, PMs can directly cancel"""
        for order in self:
            # Check if approval config exists
            if not order._has_approval_config():
                # No config, use standard behavior
                return super().button_cancel()
            
            config = order._get_approval_config()
            is_pm = self.env.user in config.get_all_pm_users()
            
            if is_pm:
                # PM users can directly cancel
                return super().button_cancel()
            else:
                # Normal user
                if order.state in ['draft', 'sent']:
                    # For draft/sent, allow direct cancellation
                    return super().button_cancel()
                elif order.state == 'purchase':
                    # For confirmed PO, need approval - open wizard
                    return order._action_open_request_reason_wizard('cancel')
                else:
                    raise UserError(_("Cannot cancel order in current state."))
        return True

    def ks_action_request_cancel(self):
        """Normal user requests cancellation - opens wizard for reason"""
        self.ensure_one()
        if self.state != 'purchase':
            raise UserError(_("Can only request cancellation for confirmed Purchase Orders."))
        return self._action_open_request_reason_wizard('cancel')

    def ks_do_request_cancel(self, reason):
        """Execute cancel request"""
        self.ensure_one()
        if not reason:
            raise UserError(_("Cancel request reason is required."))
        
        self.write({
            'state': 'cancel_requested',
            'ks_cancel_request_reason': reason,
            'ks_cancel_request_user_id': self.env.user.id,
            'ks_cancel_request_date': fields.Datetime.now(),
            'ks_cancel_pm1_approved': False,
            'ks_cancel_pm2_approved': False,
        })
        
        self.message_post(
            body=_("Cancellation request submitted by %s. \n\n Reason: %s") % (
                self.env.user.name, reason
            ),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        # Subscribe PM users
        config = self._get_approval_config()
        self.message_subscribe(partner_ids=[
            config.ks_cancel_pm1_id.partner_id.id,
            config.ks_cancel_pm2_id.partner_id.id,
        ])
        
        return True

    def ks_action_approve_cancel(self):
        """PM approves cancel request"""
        self.ensure_one()
        if self.state != 'cancel_requested':
            raise UserError(_("Can only approve cancel requests in 'Cancel Requested' state."))
        
        config = self._get_approval_config()
        current_user = self.env.user
        
        if current_user == config.ks_cancel_pm1_id:
            if self.ks_cancel_pm1_approved:
                raise UserError(_("You have already approved this cancel request."))
            self.ks_cancel_pm1_approved = True
            self.message_post(
                body=_("Cancellation approved by PM1: %s") % current_user.name,
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
        elif current_user == config.ks_cancel_pm2_id:
            if self.ks_cancel_pm2_approved:
                raise UserError(_("You have already approved this cancel request."))
            self.ks_cancel_pm2_approved = True
            self.message_post(
                body=_("Cancellation approved by PM2: %s") % current_user.name,
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
        else:
            raise UserError(_("You are not authorized to approve this cancel request."))
        
        # Check if both PMs have approved
        if self.ks_cancel_pm1_approved and self.ks_cancel_pm2_approved:
            # Both approved - cancel the PO
            self.write({
                'state': 'cancel',
                'mail_reminder_confirmed': False,
            })
            
            self.message_post(
                body=_("Purchase Order cancelled after both PM1 and PM2 approval."),
                message_type='notification',
                subtype_xmlid='mail.mt_comment',
            )
        
        return True

    def ks_action_reject_cancel(self):
        """PM rejects cancel request - open wizard for reason"""
        self.ensure_one()
        if self.state != 'cancel_requested':
            raise UserError(_("Can only reject cancel requests in 'Cancel Requested' state."))
        return self._action_open_reject_reason_wizard('cancel')

    def ks_do_reject_cancel(self, reason):
        """Execute cancel rejection"""
        self.ensure_one()
        if not reason:
            raise UserError(_("Rejection reason is required."))
        
        config = self._get_approval_config()
        current_user = self.env.user
        
        if current_user not in (config.ks_cancel_pm1_id | config.ks_cancel_pm2_id):
            raise UserError(_("You are not authorized to reject this cancel request."))
        
        # Return to purchase state
        self.write({
            'state': 'purchase',
            'ks_cancel_pm1_approved': False,
            'ks_cancel_pm2_approved': False,
            'ks_cancel_request_reason': False,
            'ks_cancel_request_user_id': False,
            'ks_cancel_request_date': False,
        })
        
        self.message_post(
            body=_("Cancellation request rejected by %s. Reason: %s") % (current_user.name, reason),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        return True

    # ===== Override Unlock (Only for PMs) =====
    
    def button_unlock(self):
        """Override: Only PM users can unlock, and reset update approval"""
        for order in self:
            if order._has_approval_config():
                config = order._get_approval_config()
                if self.env.user not in config.get_all_pm_users():
                    raise UserError(_("Only PM users can unlock Purchase Orders."))
            
            # Reset any pending update approval flags
            if order.ks_update_approved:
                order.write({
                    'ks_update_approved': False,
                    'ks_update_request_reason': False,
                    'ks_update_request_user_id': False,
                    'ks_update_request_date': False,
                    'ks_update_pm1_approved': False,
                    'ks_update_pm2_approved': False,
                })
        return super().button_unlock()

    # ===== Wizard Helpers =====
    
    def _action_open_request_reason_wizard(self, request_type):
        """Open wizard to enter reason for request"""
        self.ensure_one()
        return {
            'name': _('Enter Request Reason'),
            'type': 'ir.actions.act_window',
            'res_model': 'ks.request.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_ks_purchase_order_id': self.id,
                'default_ks_request_type': request_type,
            },
        }

    def _action_open_reject_reason_wizard(self, rejection_type):
        """Open wizard to enter reason for rejection"""
        self.ensure_one()
        return {
            'name': _('Enter Rejection Reason'),
            'type': 'ir.actions.act_window',
            'res_model': 'ks.reject.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_ks_purchase_order_id': self.id,
                'default_ks_rejection_type': rejection_type,
            },
        }

    def _action_open_approval_confirmation_wizard(self):
        """Open wizard to confirm sending approval request"""
        self.ensure_one()
        try:
            view_id = self.env.ref('ks_purchase_approval.ks_approval_confirmation_wizard_form_view').id
        except ValueError:
            view_id = False
        return {
            'name': _('Send for Approval'),
            'type': 'ir.actions.act_window',
            'res_model': 'ks.approval.confirmation.wizard',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'context': {
                'default_ks_purchase_order_id': self.id,
            },
        }

    # ===== WhatsApp Integration =====
    
    def action_rfq_send(self):
        """
        Override: Opens combined Email + WhatsApp wizard instead of just email compose.
        This allows sending both email and WhatsApp message together.
        """
        self.ensure_one()
        
        # Get the appropriate email template
        ir_model_data = self.env['ir.model.data']
        try:
            if self.env.context.get('send_rfq', False):
                template_id = ir_model_data._xmlid_lookup('purchase.email_template_edi_purchase')[1]
            else:
                template_id = ir_model_data._xmlid_lookup('purchase.email_template_edi_purchase_done')[1]
        except ValueError:
            template_id = False
        
        # Determine document type for window title
        if self.state in ['draft', 'sent']:
            title = _('Send Request for Quotation')
        else:
            title = _('Send Purchase Order')
        
        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'res_model': 'ks.rfq.send.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_purchase_order_id': self.id,
                'default_template_id': template_id,
            },
        }

    # ===== Override _is_readonly =====
    
    def _is_readonly(self):
        """Override to handle new states"""
        self.ensure_one()
        if self.state in ['pending_approval', 'update_requested', 'cancel_requested']:
            return True
        if self.state == 'purchase':
            # For normal users, confirmed PO is readonly unless update approved
            if not self.ks_is_pm_user and not self.ks_update_approved:
                return True
        return super()._is_readonly()
