# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Override state field to add new states
    state = fields.Selection(
        selection_add=[
            ('pending_approval', 'Pending Approval'),
            ('cancel_pending', 'Cancel Pending'),
            ('edit_pending', 'Edit Approval Pending'),
            ('purchase',),  # This ensures proper ordering
        ],
        ondelete={
            'pending_approval': 'set default',
            'cancel_pending': 'set default',
            'edit_pending': 'set default',
        }
    )

    # ===== Simple Two-Level Approval Fields =====
    ks_approver_1_id = fields.Many2one(
        'res.users',
        string='Approver 1',
        copy=False,
        help='First approver for purchase order approval',
    )
    ks_approver_2_id = fields.Many2one(
        'res.users',
        string='Approver 2',
        copy=False,
        help='Second approver for purchase order approval',
    )
    ks_pm1_approved = fields.Boolean(
        string='Approver 1 Approved',
        default=False,
        copy=False,
        tracking=True,
    )
    ks_pm2_approved = fields.Boolean(
        string='Approver 2 Approved',
        default=False,
        copy=False,
        tracking=True,
    )
    ks_approval_request_user_id = fields.Many2one(
        'res.users',
        string='Approval Requested By',
        copy=False,
    )
    ks_approval_request_date = fields.Datetime(
        string='Approval Request Date',
        copy=False,
    )
    ks_pm1_reason = fields.Text(
        string='Approver 1 Reason',
        copy=False,
    )
    ks_pm2_reason = fields.Text(
        string='Approver 2 Reason',
        copy=False,
    )

    # ===== Cancel Approval Fields =====
    ks_cancel_pm1_id = fields.Many2one(
        'res.users',
        string='Selected Cancel Approver 1',
        copy=False,
        help='Selected approver from Approver 1 list for this cancel request',
    )
    ks_cancel_pm2_id = fields.Many2one(
        'res.users',
        string='Selected Cancel Approver 2',
        copy=False,
        help='Selected approver from Approver 2 list for this cancel request',
    )
    ks_cancel_pm1_approved = fields.Boolean(
        string='Approver 1 Cancel Approved',
        default=False,
        copy=False,
        tracking=True,
    )
    ks_cancel_pm2_approved = fields.Boolean(
        string='Approver 2 Cancel Approved',
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
        string='Selected Edit Approver 1',
        copy=False,
        help='Selected approver from Approver 1 list for this edit request',
    )
    ks_edit_pm2_id = fields.Many2one(
        'res.users',
        string='Selected Edit Approver 2',
        copy=False,
        help='Selected approver from Approver 2 list for this edit request',
    )
    ks_edit_pm1_approved = fields.Boolean(
        string='Approver 1 Edit Approved',
        default=False,
        copy=False,
        tracking=True,
    )
    ks_edit_pm2_approved = fields.Boolean(
        string='Approver 2 Edit Approved',
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
        help='When True, the original requester can edit the PO',
    )

    # ===== Sale Order Link Fields =====
    ks_linked_sale_order_ids = fields.Many2many(
        'sale.order',
        'purchase_sale_order_rel',
        'purchase_order_id',
        'sale_order_id',
        string='Linked Sale Orders',
        copy=False,
        help='Sale Orders linked to this Purchase Order',
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
    ks_show_request_approval_button = fields.Boolean(
        string='Show Request Approval Button',
        compute='_compute_ks_button_visibility',
    )
    ks_show_approve_button = fields.Boolean(
        string='Show Approve Button',
        compute='_compute_ks_button_visibility',
    )
    ks_show_reject_button = fields.Boolean(
        string='Show Reject Button',
        compute='_compute_ks_button_visibility',
    )
    ks_show_unlock_button = fields.Boolean(
        string='Show Unlock Button',
        compute='_compute_ks_button_visibility',
    )
    ks_show_request_cancel_button = fields.Boolean(
        string='Show Request Cancel Button',
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
    ks_show_request_edit_button = fields.Boolean(
        string='Show Request Edit Button',
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
    ks_show_complete_edit_button = fields.Boolean(
        string='Show Complete Edit Button',
        compute='_compute_ks_button_visibility',
    )

    # ===== Helper Methods =====
    def _get_approval_config(self):
        """Get the global approval configuration"""
        config = self.env['ks.purchase.approval.config'].get_config()
        if not config:
            raise UserError(_(
                "No active approval configuration found. "
                "Please configure approvers in Purchase > Configuration > Purchase Approval Configuration."
            ))
        return config

    def _has_approval_config(self):
        """Check if any approval config exists without raising error"""
        config = self.env['ks.purchase.approval.config'].get_config()
        return bool(config)

    def _get_available_approvers(self):
        """
        Get available approvers for purchase order approval
        Returns tuple: (approver_1_users, approver_2_users)
        """
        config = self.env['ks.purchase.approval.config'].get_config()
        if not config:
            return self.env['res.users'], self.env['res.users']
        approver_1_users = config.ks_approver_1_ids
        approver_2_users = config.ks_approver_2_ids
        return approver_1_users, approver_2_users

    @api.depends_context('uid')
    def _compute_ks_is_pm_user(self):
        """Check if current user is any of the approvers"""
        for order in self:
            if order._has_approval_config():
                config = order._get_approval_config()
                all_approvers = config.get_all_approvers()
                order.ks_is_pm_user = self.env.user in all_approvers
                order.ks_is_normal_user = self.env.user not in all_approvers
            else:
                order.ks_is_pm_user = False
                order.ks_is_normal_user = True

    @api.depends('state', 'ks_is_pm_user', 'ks_edit_approved', 'ks_edit_request_user_id')
    @api.depends_context('uid')
    def _compute_ks_can_edit(self):
        """
        Determine if current user can edit the PO
        
        Rules:
        - Draft/Sent: Everyone can edit
        - Pending Approval/Cancel Pending/Edit Pending: No one can edit (locked)
        - Purchase (Confirmed): 
            - PM users can edit
            - Normal users can edit if ks_edit_approved is True and they are the requester
        - Done (Locked): No one can edit
        """
        for order in self:
            if order.state in ['draft', 'sent']:
                # Draft and Sent - everyone can edit
                order.ks_can_edit = True
            elif order.state in ['pending_approval', 'cancel_pending', 'edit_pending']:
                # Pending states - locked for everyone
                order.ks_can_edit = False
            elif order.state == 'purchase':
                # Confirmed state - PM users can edit, or normal users if edit is approved
                if order.ks_is_pm_user:
                    order.ks_can_edit = True
                elif order.ks_edit_approved and order.ks_edit_request_user_id == self.env.user:
                    order.ks_can_edit = True
                else:
                    order.ks_can_edit = False
            elif order.state == 'done':
                # Locked state
                order.ks_can_edit = False
            else:
                order.ks_can_edit = False

    @api.depends('state', 'ks_is_pm_user', 'ks_is_normal_user',
                 'ks_pm1_approved', 'ks_pm2_approved',
                 'ks_approver_1_id', 'ks_approver_2_id',
                 'ks_cancel_pm1_id', 'ks_cancel_pm2_id',
                 'ks_cancel_pm1_approved', 'ks_cancel_pm2_approved',
                 'ks_edit_pm1_id', 'ks_edit_pm2_id',
                 'ks_edit_pm1_approved', 'ks_edit_pm2_approved',
                 'ks_edit_approved')
    @api.depends_context('uid')
    def _compute_ks_button_visibility(self):
        """Compute visibility of all action buttons"""
        for order in self:
            # Reset all
            order.ks_show_request_approval_button = False
            order.ks_show_approve_button = False
            order.ks_show_reject_button = False
            order.ks_show_unlock_button = False
            order.ks_show_request_cancel_button = False
            order.ks_show_approve_cancel_button = False
            order.ks_show_reject_cancel_button = False
            order.ks_show_request_edit_button = False
            order.ks_show_approve_edit_button = False
            order.ks_show_reject_edit_button = False
            order.ks_show_complete_edit_button = False

            if not order._has_approval_config():
                continue

            current_user = self.env.user
            is_pm = order.ks_is_pm_user
            is_normal = order.ks_is_normal_user

            # === NORMAL USER BUTTONS ===
            if is_normal:
                # Request Approval button - only when PO is in draft/sent state
                if order.state in ['draft', 'sent']:
                    order.ks_show_request_approval_button = True
                
                # Request Cancel button - only when PO is in purchase (confirmed) state
                if order.state == 'purchase':
                    order.ks_show_request_cancel_button = True
                
                # Request Edit button - only when PO is in purchase (confirmed) state and not already approved for edit
                if order.state == 'purchase' and not order.ks_edit_approved:
                    order.ks_show_request_edit_button = True
                
                # Complete Edit button - only when edit is approved and user is the requester
                if order.state == 'purchase' and order.ks_edit_approved and order.ks_edit_request_user_id == current_user:
                    order.ks_show_complete_edit_button = True

            # === APPROVER BUTTONS ===
            if is_pm:
                # Approval buttons - only when PO is pending approval
                if order.state == 'pending_approval' and order.ks_approver_1_id:
                    # Check if this approver can still approve (hasn't approved yet)
                    can_approve = False
                    if current_user == order.ks_approver_1_id and not order.ks_pm1_approved:
                        can_approve = True
                    elif order.ks_approver_2_id and current_user == order.ks_approver_2_id and not order.ks_pm2_approved:
                        # Sequential: Approver 2 can only approve if Approver 1 has approved
                        if order.ks_pm1_approved:
                            can_approve = True
                    
                    if can_approve:
                        order.ks_show_approve_button = True
                        order.ks_show_reject_button = True
                
                # Cancel approval buttons - only when PO is in cancel_pending state
                if order.state == 'cancel_pending' and order.ks_cancel_pm1_id:
                    can_approve_cancel = False
                    if current_user == order.ks_cancel_pm1_id and not order.ks_cancel_pm1_approved:
                        can_approve_cancel = True
                    elif order.ks_cancel_pm2_id and current_user == order.ks_cancel_pm2_id and not order.ks_cancel_pm2_approved:
                        # Sequential: Approver 2 can only approve if Approver 1 has approved
                        if order.ks_cancel_pm1_approved:
                            can_approve_cancel = True
                    
                    if can_approve_cancel:
                        order.ks_show_approve_cancel_button = True
                        order.ks_show_reject_cancel_button = True
                
                # Edit approval buttons - only when PO is in edit_pending state
                if order.state == 'edit_pending' and order.ks_edit_pm1_id:
                    can_approve_edit = False
                    if current_user == order.ks_edit_pm1_id and not order.ks_edit_pm1_approved:
                        can_approve_edit = True
                    elif order.ks_edit_pm2_id and current_user == order.ks_edit_pm2_id and not order.ks_edit_pm2_approved:
                        # Sequential: Approver 2 can only approve if Approver 1 has approved
                        if order.ks_edit_pm1_approved:
                            can_approve_edit = True
                    
                    if can_approve_edit:
                        order.ks_show_approve_edit_button = True
                        order.ks_show_reject_edit_button = True

                # Unlock button - ONLY for approver users when PO is in 'done' (locked) state
                if order.state == 'done':
                    order.ks_show_unlock_button = True

    # ===== Action Methods =====
    
    def button_confirm(self):
        """
        Override: 
        - PM users: Confirm immediately (standard flow)
        - Normal users: Show popup before sending to Pending Approval
        """
        # Update linked sale orders before confirmation
        for po in self:
            if po.ks_linked_sale_order_ids:
                po._update_linked_sale_orders()
        
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
            all_approvers = config.get_all_approvers()
            is_pm = self.env.user in all_approvers
            
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
            all_approvers = config.get_all_approvers()
            is_pm = self.env.user in all_approvers
            
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
                # Skip for now - user needs to process individually
                pass
        
        return True

    def _ks_send_to_pending_approval(self, approver_1_id, approver_2_id):
        """Normal user sends PO to pending approval - called after popup confirmation with selected approvers"""
        self.ensure_one()
        if self.state not in ['draft', 'sent']:
            raise UserError(_("Can only request approval for Draft or Sent orders."))
        
        if not approver_1_id:
            raise UserError(_("Approver 1 is required."))
        
        # Check approval mode
        config = self._get_approval_config()
        is_two_way = config.is_two_way_approval()
        
        if is_two_way and not approver_2_id:
            raise UserError(_("Approver 2 is required for Two Level Approval mode."))
        
        approver_1 = self.env['res.users'].browse(approver_1_id)
        approver_2 = self.env['res.users'].browse(approver_2_id) if approver_2_id else False
        
        self.write({
            'state': 'pending_approval',
            'ks_approval_request_user_id': self.env.user.id,
            'ks_approval_request_date': fields.Datetime.now(),
            'ks_approver_1_id': approver_1_id,
            'ks_approver_2_id': approver_2_id,
            'ks_pm1_approved': False,
            'ks_pm2_approved': False,
            'ks_pm1_reason': False,
            'ks_pm2_reason': False,
        })
        
        # Log in chatter with actual approver names
        if is_two_way and approver_2:
            approval_msg = _("Approval request submitted by %s. Waiting for sequential approval from: Approver 1 - %s, Approver 2 - %s.") % (
                self.env.user.name,
                approver_1.name,
                approver_2.name,
            )
            partner_ids = [approver_1.partner_id.id, approver_2.partner_id.id]
        else:
            approval_msg = _("Approval request submitted by %s. Waiting for approval from: Approver 1 - %s.") % (
                self.env.user.name,
                approver_1.name,
            )
            partner_ids = [approver_1.partner_id.id]
        
        self.message_post(
            body=approval_msg,
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        # Subscribe approver users
        self.message_subscribe(partner_ids=partner_ids)
        
        # Create activity for Approver 1 to review approval request
        # This will trigger a notification popup: "A new approval task has been assigned to you."
        self._create_approval_activity(
            user_id=approver_1_id,
            summary=_('PO Approval Request for: %s') % self.name,
            note=_('Purchase Order %s has been submitted for approval by %s. Please review and approve or reject.') % (
                self.name, self.env.user.name
            ),
        )
        
        return True

    def ks_action_approve(self):
        """Approver approves request - opens wizard for reason"""
        self.ensure_one()
        if self.state != 'pending_approval':
            raise UserError(_("Can only approve orders in 'Pending Approval' state."))
        
        if not self.ks_approver_1_id:
            raise UserError(_("Approver 1 not selected for this approval request."))
        
        # Check approval mode
        config = self._get_approval_config()
        is_two_way = config.is_two_way_approval()
        
        if is_two_way and not self.ks_approver_2_id:
            raise UserError(_("Approver 2 is required for Two Level Approval mode."))
        
        current_user = self.env.user
        
        # Check authorization - user must be one of the selected approvers
        approvers = self.ks_approver_1_id
        if self.ks_approver_2_id:
            approvers |= self.ks_approver_2_id
        if current_user not in approvers:
            raise UserError(_("You are not authorized to approve this request."))
        
        # Sequential approval: Approver 1 must approve before Approver 2 (only if Approver 2 exists)
        if self.ks_approver_2_id and current_user == self.ks_approver_2_id and not self.ks_pm1_approved:
            raise UserError(_("Approver 1 must approve before Approver 2 can approve."))
        
        # Check if already approved
        if current_user == self.ks_approver_1_id and self.ks_pm1_approved:
            raise UserError(_("You have already approved this request."))
        if current_user == self.ks_approver_2_id and self.ks_pm2_approved:
            raise UserError(_("You have already approved this request."))
        
        # Open wizard for reason
        try:
            view_id = self.env.ref('ks_purchase_approval.ks_approve_reason_wizard_form_view').id
        except ValueError:
            view_id = False
        return {
            'name': _('Approve Purchase Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'ks.approve.reason.wizard',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'context': {
                'default_ks_purchase_order_id': self.id,
            },
        }

    def ks_do_approve(self, reason):
        """Execute approval with reason"""
        self.ensure_one()
        if not reason:
            raise UserError(_("Reason for approval is required."))
        
        if self.state != 'pending_approval':
            raise UserError(_("Can only approve orders in 'Pending Approval' state."))
        
        if not self.ks_approver_1_id:
            raise UserError(_("Approver 1 not selected for this approval request."))
        
        # Check approval mode
        config = self._get_approval_config()
        is_two_way = config.is_two_way_approval()
        
        if is_two_way and not self.ks_approver_2_id:
            raise UserError(_("Approver 2 is required for Two Level Approval mode."))
        
        current_user = self.env.user
        
        if current_user == self.ks_approver_1_id:
            if self.ks_pm1_approved:
                raise UserError(_("You have already approved this request."))
            self.write({
                'ks_pm1_approved': True,
                'ks_pm1_reason': reason,
            })
            self.message_post(
                body=_("Approver 1 (%s) approved the PO. Reason: %s") % (current_user.name, reason),
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
            
            # Mark PM1 activity as done
            self.env['mail.activity'].search([
                ('res_model', '=', self._name),
                ('res_id', '=', self.id),
                ('user_id', '=', self.ks_approver_1_id.id),
                ('summary', 'ilike', 'PO Approval Request'),
            ]).action_done()
            
            # Create activity for Approver 2 only in two-way mode
            if is_two_way and self.ks_approver_2_id:
                self._create_approval_activity(
                    user_id=self.ks_approver_2_id.id,
                    summary=_('PO Approval Request for: %s - Approver 1 Approved') % self.name,
                    note=_('Purchase Order %s has been approved by Approver 1 (%s). Please review and approve or reject. Reason: %s') % (
                        self.name, current_user.name, reason
                    ),
                )
        elif is_two_way and current_user == self.ks_approver_2_id:
            # Sequential: Check if Approver 1 has approved
            if not self.ks_pm1_approved:
                raise UserError(_("Approver 1 must approve before Approver 2 can approve."))
            if self.ks_pm2_approved:
                raise UserError(_("You have already approved this request."))
            self.write({
                'ks_pm2_approved': True,
                'ks_pm2_reason': reason,
            })
            self.message_post(
                body=_("Approver 2 (%s) approved the PO. Reason: %s") % (current_user.name, reason),
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
            
            # Mark PM2 activity as done
            self.env['mail.activity'].search([
                ('res_model', '=', self._name),
                ('res_id', '=', self.id),
                ('user_id', '=', self.ks_approver_2_id.id),
                ('summary', 'ilike', 'PO Approval Request'),
            ]).action_done()
        else:
            raise UserError(_("You are not authorized to approve this request."))
        
        # Check if approval is complete based on approval mode
        approval_complete = False
        if is_two_way:
            # Two-way: Both approvers must approve
            approval_complete = self.ks_pm1_approved and self.ks_pm2_approved
        else:
            # Single level: Only Approver 1 needs to approve
            approval_complete = self.ks_pm1_approved
        
        if approval_complete:
            # Approval complete - confirm the PO using standard flow to ensure receipt creation
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
            
            # Post confirmation message based on approval mode
            if is_two_way:
                self.message_post(
                    body=_("Purchase Order confirmed after both Approver 1 and Approver 2 approval."),
                    message_type='notification',
                    subtype_xmlid='mail.mt_comment',
                )
            else:
                self.message_post(
                    body=_("Purchase Order confirmed after Approver 1 approval."),
                    message_type='notification',
                    subtype_xmlid='mail.mt_comment',
                )
            
            if self.partner_id not in self.message_partner_ids:
                self.message_subscribe([self.partner_id.id])
            
            # Create activity for requester to notify approval is complete
            if self.ks_approval_request_user_id:
                self._create_approval_activity(
                    user_id=self.ks_approval_request_user_id.id,
                    summary=_('PO Approved: %s') % self.name,
                    note=_('Purchase Order %s has been confirmed after approval from both Approver 1 and Approver 2.') % self.name,
                )
        
        return True

    def ks_action_reject(self):
        """PM rejects approval request - open wizard for reason"""
        self.ensure_one()
        if self.state != 'pending_approval':
            raise UserError(_("Can only reject orders in 'Pending Approval' state."))
        return self._action_open_reject_reason_wizard()

    def ks_do_reject(self, reason):
        """Execute rejection"""
        self.ensure_one()
        if not reason:
            raise UserError(_("Rejection reason is required."))
        
        if not self.ks_approver_1_id:
            raise UserError(_("Approver 1 not selected for this approval request."))
        
        # Check approval mode
        config = self._get_approval_config()
        is_two_way = config.is_two_way_approval()
        
        if is_two_way and not self.ks_approver_2_id:
            raise UserError(_("Approver 2 is required for Two Level Approval mode."))
        
        current_user = self.env.user
        
        # Build list of approvers based on mode
        approvers = self.ks_approver_1_id
        if is_two_way and self.ks_approver_2_id:
            approvers |= self.ks_approver_2_id
        
        if current_user not in approvers:
            raise UserError(_("You are not authorized to reject this request."))
        
        # Reset to draft state
        self.write({
            'state': 'draft',
            'ks_pm1_approved': False,
            'ks_pm2_approved': False,
            'ks_approval_request_user_id': False,
            'ks_approval_request_date': False,
            'ks_approver_1_id': False,
            'ks_approver_2_id': False,
            'ks_pm1_reason': False,
            'ks_pm2_reason': False,
        })
        
        self.message_post(
            body=_("Approval request rejected by %s. Reason: %s") % (current_user.name, reason),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        # Mark approver activities as done
        approver_user_ids = [self.ks_approver_1_id.id]
        if self.ks_approver_2_id:
            approver_user_ids.append(self.ks_approver_2_id.id)
        
        self.env['mail.activity'].search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('user_id', 'in', approver_user_ids),
            ('summary', 'ilike', 'PO Approval Request'),
        ]).action_done()
        
        # Create activity for requester to notify rejection
        if self.ks_approval_request_user_id:
            self._create_approval_activity(
                user_id=self.ks_approval_request_user_id.id,
                summary=_('PO Approval Request Rejected: %s') % self.name,
                note=_('Purchase Order %s approval request has been rejected by %s. Reason: %s') % (
                    self.name, current_user.name, reason
                ),
            )
        
        return True

    def ks_action_request_approval(self):
        """Normal user requests approval - opens wizard to select approvers"""
        self.ensure_one()
        if self.state not in ['draft', 'sent']:
            raise UserError(_("Can only request approval for Draft or Sent orders."))
        return self._action_open_approval_confirmation_wizard()

    # ===== Cancel Request Methods =====
    
    def action_cancel(self):
        """Override: Normal users must request cancellation for confirmed POs, Approvers can directly cancel"""
        for order in self:
            # Check if approval config exists
            if not order._has_approval_config():
                # No config, use standard behavior
                return super().action_cancel()
            
            config = order._get_approval_config()
            all_approvers = config.get_all_approvers()
            is_pm = self.env.user in all_approvers
            
            if is_pm:
                # Approver users can directly cancel
                return super().action_cancel()
            else:
                # Normal user
                if order.state in ['draft', 'sent']:
                    # For draft/sent, allow direct cancellation
                    return super().action_cancel()
                elif order.state == 'purchase':
                    # For confirmed PO, need approval - open wizard
                    return order._action_open_cancel_request_wizard()
                elif order.state == 'pending_approval':
                    # Allow cancelling approval pending - reset to draft
                    return order._ks_cancel_approval_request()
                else:
                    raise UserError(_("Cannot cancel order in current state."))
        return True

    def _ks_cancel_approval_request(self):
        """Cancel an approval request and reset to draft"""
        self.ensure_one()
        if self.state != 'pending_approval':
            raise UserError(_("Can only cancel approval requests in 'Pending Approval' state."))
        
        self.write({
            'state': 'draft',
            'ks_pm1_approved': False,
            'ks_pm2_approved': False,
            'ks_approval_request_user_id': False,
            'ks_approval_request_date': False,
            'ks_approver_1_id': False,
            'ks_approver_2_id': False,
            'ks_pm1_reason': False,
            'ks_pm2_reason': False,
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
            'name': _('Request Cancellation'),
            'type': 'ir.actions.act_window',
            'res_model': 'ks.purchase.cancel.approval.request.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_ks_purchase_order_id': self.id,
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
        is_two_way = config.is_two_way_approval()
        
        if is_two_way and not self.ks_cancel_pm2_id:
            raise UserError(_("Approver 2 must be selected for Two Level Approval mode."))
        
        self.write({
            'state': 'cancel_pending',
            'ks_cancel_request_reason': reason,
            'ks_cancel_request_user_id': self.env.user.id,
            'ks_cancel_request_date': fields.Datetime.now(),
            'ks_cancel_pm1_approved': False,
            'ks_cancel_pm2_approved': False,
        })
        
        # Determine approval message based on mode
        if is_two_way:
            pm1_name = self.ks_cancel_pm1_id.name if self.ks_cancel_pm1_id else ''
            pm2_name = self.ks_cancel_pm2_id.name if self.ks_cancel_pm2_id else ''
            approval_msg = _("Cancellation request submitted by %s. Waiting for approval from %s (Approver 1) and %s (Approver 2).\nReason: %s") % (
                self.env.user.name, pm1_name, pm2_name, reason
            )
        else:
            pm1_name = self.ks_cancel_pm1_id.name if self.ks_cancel_pm1_id else ''
            approval_msg = _("Cancellation request submitted by %s. Waiting for approval from %s (Approver 1).\nReason: %s") % (
                self.env.user.name, pm1_name, reason
            )
        
        self.message_post(
            body=approval_msg,
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        # Subscribe selected approver users
        partner_ids = []
        if self.ks_cancel_pm1_id:
            partner_ids.append(self.ks_cancel_pm1_id.partner_id.id)
        if self.ks_cancel_pm2_id:
            partner_ids.append(self.ks_cancel_pm2_id.partner_id.id)
        if partner_ids:
            self.message_subscribe(partner_ids=partner_ids)
        
        return True

    def ks_action_approve_cancel(self):
        """Approver approves cancel request - open wizard for reason"""
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
        is_two_way = config.is_two_way_approval()
        
        # Check which approver is approving
        approver_role = None
        if self.ks_cancel_pm1_id and current_user == self.ks_cancel_pm1_id:
            if self.ks_cancel_pm1_approved:
                raise UserError(_("You have already approved this cancel request."))
            self.ks_cancel_pm1_approved = True
            approver_role = 'Approver 1 - %s' % self.ks_cancel_pm1_id.name
        elif self.ks_cancel_pm2_id and current_user == self.ks_cancel_pm2_id:
            # Sequential approval: Approver 2 can only approve if Approver 1 has already approved
            if not self.ks_cancel_pm1_approved:
                raise UserError(_("Approver 1 must approve first before Approver 2 can approve this cancel request."))
            if self.ks_cancel_pm2_approved:
                raise UserError(_("You have already approved this cancel request."))
            self.ks_cancel_pm2_approved = True
            approver_role = 'Approver 2 - %s' % self.ks_cancel_pm2_id.name
        else:
            raise UserError(_("You are not authorized to approve this cancel request."))
        
        # Post message in chatter with reason
        self.message_post(
            body=_(
                "✅ Cancellation Approved\n"
                "Approved by: %s\n"
                "Action: Approved\n"
                "Reason: %s"
            ) % (approver_role, reason),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        # Check if approval is complete based on mode
        approval_complete = False
        if is_two_way:
            # Both approvers must approve
            if self.ks_cancel_pm1_approved and self.ks_cancel_pm2_approved:
                approval_complete = True
        else:
            # Single level approval - Approver 1 approval is enough
            if self.ks_cancel_pm1_approved:
                approval_complete = True
        
        if approval_complete:
            # Cancel the PO
            self.write({'state': 'cancel'})
            
            if is_two_way:
                pm1_name = self.ks_cancel_pm1_id.name if self.ks_cancel_pm1_id else ''
                pm2_name = self.ks_cancel_pm2_id.name if self.ks_cancel_pm2_id else ''
                self.message_post(
                    body=_("Purchase Order cancelled after both %s (Approver 1) and %s (Approver 2) approval.") % (pm1_name, pm2_name),
                    message_type='notification',
                    subtype_xmlid='mail.mt_comment',
                )
            else:
                pm1_name = self.ks_cancel_pm1_id.name if self.ks_cancel_pm1_id else ''
                self.message_post(
                    body=_("Purchase Order cancelled after %s (Approver 1) approval.") % pm1_name,
                    message_type='notification',
                    subtype_xmlid='mail.mt_comment',
                )
        
        return True

    def ks_action_reject_cancel(self):
        """Approver rejects cancel request - open wizard for reason"""
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
        
        # Sequential approval: Approver 2 can only reject if Approver 1 has already approved
        if self.ks_cancel_pm2_id and current_user == self.ks_cancel_pm2_id:
            if not self.ks_cancel_pm1_approved:
                raise UserError(_("Approver 1 must approve first before Approver 2 can reject this cancel request."))
        
        # Determine approver role
        approver_role = None
        if self.ks_cancel_pm1_id and current_user == self.ks_cancel_pm1_id:
            approver_role = 'Approver 1 - %s' % self.ks_cancel_pm1_id.name
        elif self.ks_cancel_pm2_id and current_user == self.ks_cancel_pm2_id:
            approver_role = 'Approver 2 - %s' % self.ks_cancel_pm2_id.name
        
        # Return to purchase state
        self.write({
            'state': 'purchase',
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
            ) % (approver_role or current_user.name, reason),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        return True

    # ===== Edit Request Methods =====
    
    def ks_action_request_edit(self):
        """Normal user requests edit permission - opens wizard for reason"""
        self.ensure_one()
        if self.state != 'purchase':
            raise UserError(_("Can only request edit for confirmed Purchase Orders."))
        if self.ks_edit_approved:
            raise UserError(_("Edit is already approved. Please complete your edits first."))
        return self._action_open_edit_request_wizard()

    def _action_open_edit_request_wizard(self):
        """Open wizard to select approvers for edit request"""
        self.ensure_one()
        config = self._get_approval_config() if self._has_approval_config() else False
        return {
            'name': _('Request Edit Access'),
            'type': 'ir.actions.act_window',
            'res_model': 'ks.purchase.edit.approval.request.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_ks_purchase_order_id': self.id,
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
        is_two_way = config.is_two_way_approval()
        
        if is_two_way and not self.ks_edit_pm2_id:
            raise UserError(_("Approver 2 must be selected for Two Level Approval mode."))
        
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
        if is_two_way:
            pm1_name = self.ks_edit_pm1_id.name if self.ks_edit_pm1_id else ''
            pm2_name = self.ks_edit_pm2_id.name if self.ks_edit_pm2_id else ''
            approval_msg = _("Edit request submitted by %s. Waiting for approval from %s (Approver 1) and %s (Approver 2).\nReason: %s") % (
                self.env.user.name, pm1_name, pm2_name, reason
            )
        else:
            pm1_name = self.ks_edit_pm1_id.name if self.ks_edit_pm1_id else ''
            approval_msg = _("Edit request submitted by %s. Waiting for approval from %s (Approver 1).\nReason: %s") % (
                self.env.user.name, pm1_name, reason
            )
        
        self.message_post(
            body=approval_msg,
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        # Subscribe selected approver users
        partner_ids = []
        if self.ks_edit_pm1_id:
            partner_ids.append(self.ks_edit_pm1_id.partner_id.id)
        if self.ks_edit_pm2_id:
            partner_ids.append(self.ks_edit_pm2_id.partner_id.id)
        if partner_ids:
            self.message_subscribe(partner_ids=partner_ids)
        
        return True

    def ks_action_approve_edit(self):
        """Approver approves edit request - open wizard for reason"""
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
        is_two_way = config.is_two_way_approval()
        
        # Check which approver is approving
        approver_role = None
        if self.ks_edit_pm1_id and current_user == self.ks_edit_pm1_id:
            if self.ks_edit_pm1_approved:
                raise UserError(_("You have already approved this edit request."))
            self.ks_edit_pm1_approved = True
            approver_role = 'Approver 1 - %s' % self.ks_edit_pm1_id.name
        elif self.ks_edit_pm2_id and current_user == self.ks_edit_pm2_id:
            # Sequential approval: Approver 2 can only approve if Approver 1 has already approved
            if not self.ks_edit_pm1_approved:
                raise UserError(_("Approver 1 must approve first before Approver 2 can approve this edit request."))
            if self.ks_edit_pm2_approved:
                raise UserError(_("You have already approved this edit request."))
            self.ks_edit_pm2_approved = True
            approver_role = 'Approver 2 - %s' % self.ks_edit_pm2_id.name
        else:
            raise UserError(_("You are not authorized to approve this edit request."))
        
        # Post message in chatter with reason
        self.message_post(
            body=_(
                "✅ Edit Approved\n"
                "Approved by: %s\n"
                "Action: Approved\n"
                "Reason: %s"
            ) % (approver_role, reason),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        # Check if approval is complete based on mode
        approval_complete = False
        if is_two_way:
            # Both approvers must approve
            if self.ks_edit_pm1_approved and self.ks_edit_pm2_approved:
                approval_complete = True
        else:
            # Single level approval - Approver 1 approval is enough
            if self.ks_edit_pm1_approved:
                approval_complete = True
        
        if approval_complete:
            # Both approved - allow editing
            self.write({
                'state': 'purchase',
                'ks_edit_approved': True,
            })
            
            if is_two_way:
                pm1_name = self.ks_edit_pm1_id.name if self.ks_edit_pm1_id else ''
                pm2_name = self.ks_edit_pm2_id.name if self.ks_edit_pm2_id else ''
                self.message_post(
                    body=_("Edit approved by both %s (Approver 1) and %s (Approver 2). %s can now edit this Purchase Order.") % (
                        pm1_name, pm2_name, self.ks_edit_request_user_id.name
                    ),
                    message_type='notification',
                    subtype_xmlid='mail.mt_comment',
                )
            else:
                pm1_name = self.ks_edit_pm1_id.name if self.ks_edit_pm1_id else ''
                self.message_post(
                    body=_("Edit approved by %s (Approver 1). %s can now edit this Purchase Order.") % (
                        pm1_name, self.ks_edit_request_user_id.name
                    ),
                    message_type='notification',
                    subtype_xmlid='mail.mt_comment',
                )
        
        return True

    def ks_action_reject_edit(self):
        """Approver rejects edit request - open wizard for reason"""
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
        
        # Sequential approval: Approver 2 can only reject if Approver 1 has already approved
        if self.ks_edit_pm2_id and current_user == self.ks_edit_pm2_id:
            if not self.ks_edit_pm1_approved:
                raise UserError(_("Approver 1 must approve first before Approver 2 can reject this edit request."))
        
        # Determine approver role
        approver_role = None
        if self.ks_edit_pm1_id and current_user == self.ks_edit_pm1_id:
            approver_role = 'Approver 1 - %s' % self.ks_edit_pm1_id.name
        elif self.ks_edit_pm2_id and current_user == self.ks_edit_pm2_id:
            approver_role = 'Approver 2 - %s' % self.ks_edit_pm2_id.name
        
        # Return to purchase state
        self.write({
            'state': 'purchase',
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
            ) % (approver_role or current_user.name, reason),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        return True

    def ks_action_complete_edit(self):
        """User completes editing after edit approval - lock PO again"""
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
        
        self.message_post(
            body=_("Edit completed by %s. Purchase Order is now locked.") % self.env.user.name,
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        return True

    # ===== Override Unlock (Only for PMs) =====
    
    def button_unlock(self):
        """Override: Only approver users can unlock"""
        for order in self:
            if order._has_approval_config():
                all_approvers = self.env['ks.purchase.approval.config'].search([('active', '=', True)]).mapped('user_id')
                if self.env.user not in all_approvers:
                    raise UserError(_("Only approver users can unlock Purchase Orders."))
        return super().button_unlock()

    # ===== Sale Order Link Methods =====
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to automatically update linked Sale Orders"""
        pos = super().create(vals_list)
        
        # Update linked sale orders for each PO that has linked_sale_order_ids
        for po in pos:
            if po.ks_linked_sale_order_ids:
                po._update_linked_sale_orders()
        
        return pos
    
    def write(self, vals):
        """Override write to automatically update linked Sale Orders"""
        result = super().write(vals)
        
        # If linked_sale_order_ids is being updated, update the reverse relation
        if 'ks_linked_sale_order_ids' in vals:
            self._update_linked_sale_orders()
        
        return result
    
    def _update_linked_sale_orders(self):
        """Update the reverse Many2one field in linked Sale Orders"""
        for po in self:
            # Get current linked sale orders
            current_linked_sos = po.ks_linked_sale_order_ids
            
            # Find sale orders that were previously linked to this PO but are no longer linked
            previously_linked_sos = self.env['sale.order'].search([
                ('ks_linked_purchase_order_id', '=', po.id),
                ('id', 'not in', current_linked_sos.ids)
            ])
            
            # Remove link from sale orders that are no longer in the Many2many
            previously_linked_sos.write({'ks_linked_purchase_order_id': False})
            
            # Update link in current sale orders
            # Only update if they don't already have a different PO linked
            for so in current_linked_sos:
                if not so.ks_linked_purchase_order_id or so.ks_linked_purchase_order_id.id == po.id:
                    so.write({'ks_linked_purchase_order_id': po.id})
                else:
                    # If SO already has a different PO linked, show warning
                    raise ValidationError(_(
                        "Sale Order %s is already linked to Purchase Order %s. "
                        "Please unlink it first before linking to this PO."
                    ) % (so.name, so.ks_linked_purchase_order_id.name))
    
    def action_confirm(self):
        """Override action_confirm to ensure links are saved on confirmation"""
        # Update linked sale orders before confirmation
        for po in self:
            if po.ks_linked_sale_order_ids:
                po._update_linked_sale_orders()
        
        return super().action_confirm()

    # ===== Mail Activity Helpers =====
    
    def _create_approval_activity(self, user_id, summary, note='', date_deadline=None, activity_type_xmlid='mail.mail_activity_data_todo'):
        """
        Helper method to create mail.activity records for approval workflow operations.
        Uses activity_schedule to ensure proper notification handling.
        Prevents duplicate activities by checking existing activities first.
        
        :param user_id: User ID to assign the activity to
        :param summary: Activity summary text
        :param note: Activity note (HTML content)
        :param date_deadline: Due date for the activity (defaults to today)
        :param activity_type_xmlid: XML ID of activity type (defaults to 'To Do')
        :return: Created activity record or False if duplicate found
        """
        self.ensure_one()
        
        # Prevent duplicate activities - check if similar activity already exists
        if not date_deadline:
            date_deadline = fields.Date.today()
        
        existing_activity = self.env['mail.activity'].search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('user_id', '=', user_id),
            ('summary', '=', summary),
            ('date_deadline', '=', date_deadline),
        ], limit=1)
        
        if existing_activity:
            # Activity already exists, don't create duplicate
            return existing_activity
        
        # Use activity_schedule which automatically handles notifications
        # This ensures the popup notification appears like "A new approval task has been assigned to you."
        try:
            activity = self.activity_schedule(
                act_type_xmlid=activity_type_xmlid,
                summary=summary,
                note=note or '',
                user_id=user_id,
                date_deadline=date_deadline,
            )
            return activity
        except Exception:
            # Fallback if activity_schedule fails
            return False
    
    # ===== Wizard Helpers =====
    
    def _action_open_reject_reason_wizard(self):
        """Open wizard to enter reason for rejection"""
        self.ensure_one()
        return {
            'name': _('Enter Rejection Reason'),
            'type': 'ir.actions.act_window',
            'res_model': 'ks.purchase.approval.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_ks_purchase_order_id': self.id,
                'default_ks_action_type': 'reject_confirm',
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

    def _action_open_approval_reason_wizard(self, action_type):
        """Open wizard to enter reason for approval/rejection"""
        self.ensure_one()
        return {
            'name': _('Enter Reason'),
            'type': 'ir.actions.act_window',
            'res_model': 'ks.purchase.approval.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_ks_purchase_order_id': self.id,
                'default_ks_action_type': action_type,
            },
        }

    # ===== Override _is_readonly =====
    
    def _is_readonly(self):
        """Override to handle new states"""
        self.ensure_one()
        if self.state == 'pending_approval':
            return True
        if self.state == 'purchase':
            # For normal users, confirmed PO is readonly
            if not self.ks_is_pm_user:
                return True
        return super()._is_readonly()
