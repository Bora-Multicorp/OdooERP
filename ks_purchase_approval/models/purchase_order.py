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
    ks_confirm_approver_1_id = fields.Many2one(
        'res.users',
        string='Confirmation Approver 1',
        copy=False,
        help='First approver selected for confirmation approval',
    )
    ks_confirm_approver_2_id = fields.Many2one(
        'res.users',
        string='Confirmation Approver 2',
        copy=False,
        help='Second approver selected for confirmation approval',
    )
    ks_confirm_pm1_approved = fields.Boolean(
        string='Approver 1 Confirmation Approved',
        default=False,
        copy=False,
        tracking=True,
    )
    ks_confirm_pm2_approved = fields.Boolean(
        string='Approver 2 Confirmation Approved',
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
        string='Approver 1 Confirmation Reason',
        copy=False,
    )
    ks_confirm_pm2_reason = fields.Text(
        string='Approver 2 Confirmation Reason',
        copy=False,
    )

    # ===== Update Approval Fields =====
    ks_update_approver_1_id = fields.Many2one(
        'res.users',
        string='Update Approver 1',
        copy=False,
        help='First approver selected for update approval',
    )
    ks_update_approver_2_id = fields.Many2one(
        'res.users',
        string='Update Approver 2',
        copy=False,
        help='Second approver selected for update approval',
    )
    ks_update_pm1_approved = fields.Boolean(
        string='Approver 1 Update Approved',
        default=False,
        copy=False,
        tracking=True,
    )
    ks_update_pm2_approved = fields.Boolean(
        string='Approver 2 Update Approved',
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
    ks_cancel_approver_1_id = fields.Many2one(
        'res.users',
        string='Cancel Approver 1',
        copy=False,
        help='First approver selected for cancel approval',
    )
    ks_cancel_approver_2_id = fields.Many2one(
        'res.users',
        string='Cancel Approver 2',
        copy=False,
        help='Second approver selected for cancel approval',
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
    def _get_approval_configs(self):
        """Get all approval configurations"""
        return self.env['ks.purchase.approval.config'].search([('active', '=', True)])

    def _has_approval_config(self):
        """Check if any approval config exists without raising error"""
        configs = self._get_approval_configs()
        return bool(configs)

    def _get_available_approvers(self, approval_type):
        """
        Get available approvers for a given approval type (confirm, update, cancel)
        Returns list of user_ids who are configured as Approver 1 or Approver 2 for this type
        """
        configs = self._get_approval_configs()
        approver_type_field = {
            'confirm': 'ks_confirm_approver_type',
            'update': 'ks_update_approver_type',
            'cancel': 'ks_cancel_approver_type',
        }.get(approval_type)
        
        if not approver_type_field:
            return self.env['res.users']
        
        approver_1_users = configs.filtered(lambda c: getattr(c, approver_type_field) == 'approver_1').mapped('user_id')
        approver_2_users = configs.filtered(lambda c: getattr(c, approver_type_field) == 'approver_2').mapped('user_id')
        
        return approver_1_users | approver_2_users

    @api.depends_context('uid')
    def _compute_ks_is_pm_user(self):
        """Check if current user is any of the approvers"""
        for order in self:
            if order._has_approval_config():
                all_approvers = self.env['ks.purchase.approval.config'].search([('active', '=', True)]).mapped('user_id')
                order.ks_is_pm_user = self.env.user in all_approvers
                order.ks_is_normal_user = self.env.user not in all_approvers
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

            # === APPROVER BUTTONS ===
            if is_pm:
                # Confirmation approval buttons
                if order.state == 'pending_approval' and order.ks_confirm_approver_1_id and order.ks_confirm_approver_2_id:
                    # Check if this approver can still approve (hasn't approved yet)
                    can_approve = False
                    if current_user == order.ks_confirm_approver_1_id and not order.ks_confirm_pm1_approved:
                        can_approve = True
                    elif current_user == order.ks_confirm_approver_2_id and not order.ks_confirm_pm2_approved:
                        # Sequential: Approver 2 can only approve if Approver 1 has approved
                        if order.ks_confirm_pm1_approved:
                            can_approve = True
                    
                    if can_approve:
                        order.ks_show_approve_confirm_button = True
                        order.ks_show_reject_confirm_button = True

                # Update approval buttons
                if order.state == 'update_requested' and order.ks_update_approver_1_id and order.ks_update_approver_2_id:
                    can_approve = False
                    if current_user == order.ks_update_approver_1_id and not order.ks_update_pm1_approved:
                        can_approve = True
                    elif current_user == order.ks_update_approver_2_id and not order.ks_update_pm2_approved:
                        # Sequential: Approver 2 can only approve if Approver 1 has approved
                        if order.ks_update_pm1_approved:
                            can_approve = True
                    
                    if can_approve:
                        order.ks_show_approve_update_button = True
                        order.ks_show_reject_update_button = True

                # Cancel approval buttons
                if order.state == 'cancel_requested' and order.ks_cancel_approver_1_id and order.ks_cancel_approver_2_id:
                    can_approve = False
                    if current_user == order.ks_cancel_approver_1_id and not order.ks_cancel_pm1_approved:
                        can_approve = True
                    elif current_user == order.ks_cancel_approver_2_id and not order.ks_cancel_pm2_approved:
                        # Sequential: Approver 2 can only approve if Approver 1 has approved
                        if order.ks_cancel_pm1_approved:
                            can_approve = True
                    
                    if can_approve:
                        order.ks_show_approve_cancel_button = True
                        order.ks_show_reject_cancel_button = True

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
            
            configs = order._get_approval_configs()
            all_approvers = configs.mapped('user_id')
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
            
            configs = order._get_approval_configs()
            all_approvers = configs.mapped('user_id')
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
            raise UserError(_("Can only request confirmation for Draft or Sent orders."))
        
        if not approver_1_id or not approver_2_id:
            raise UserError(_("Both Approver 1 and Approver 2 are required."))
        
        approver_1 = self.env['res.users'].browse(approver_1_id)
        approver_2 = self.env['res.users'].browse(approver_2_id)
        
        self.write({
            'state': 'pending_approval',
            'ks_confirm_request_user_id': self.env.user.id,
            'ks_confirm_request_date': fields.Datetime.now(),
            'ks_confirm_approver_1_id': approver_1_id,
            'ks_confirm_approver_2_id': approver_2_id,
            'ks_confirm_pm1_approved': False,
            'ks_confirm_pm2_approved': False,
            'ks_confirm_pm1_reason': False,
            'ks_confirm_pm2_reason': False,
        })
        
        # Log in chatter with actual approver names
        self.message_post(
            body=_("Confirmation request submitted by %s. Waiting for sequential approval from: Approver 1 - %s, Approver 2 - %s.") % (
                self.env.user.name,
                approver_1.name,
                approver_2.name,
            ),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        # Subscribe approver users
        self.message_subscribe(partner_ids=[
            approver_1.partner_id.id,
            approver_2.partner_id.id,
        ])
        
        # Create activity for Approver 1 (PM1) to review confirmation request
        # This will trigger a notification popup: "A new approval task has been assigned to you."
        self._create_approval_activity(
            user_id=approver_1_id,
            summary=_('PO Confirmation Approval for: %s') % self.name,
            note=_('Purchase Order %s has been submitted for confirmation approval by %s. Please review and approve or reject.') % (
                self.name, self.env.user.name
            ),
        )
        
        return True

    def ks_action_approve_confirmation(self):
        """Approver approves confirmation request - opens wizard for reason"""
        self.ensure_one()
        if self.state != 'pending_approval':
            raise UserError(_("Can only approve orders in 'Pending Approval' state."))
        
        if not self.ks_confirm_approver_1_id or not self.ks_confirm_approver_2_id:
            raise UserError(_("Approvers not selected for this confirmation request."))
        
        current_user = self.env.user
        
        # Check authorization - user must be one of the selected approvers
        if current_user not in (self.ks_confirm_approver_1_id | self.ks_confirm_approver_2_id):
            raise UserError(_("You are not authorized to approve this confirmation request."))
        
        # Sequential approval: Approver 1 must approve before Approver 2
        if current_user == self.ks_confirm_approver_2_id and not self.ks_confirm_pm1_approved:
            raise UserError(_("Approver 1 must approve before Approver 2 can approve."))
        
        # Check if already approved
        if current_user == self.ks_confirm_approver_1_id and self.ks_confirm_pm1_approved:
            raise UserError(_("You have already approved this confirmation request."))
        if current_user == self.ks_confirm_approver_2_id and self.ks_confirm_pm2_approved:
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
        
        if not self.ks_confirm_approver_1_id or not self.ks_confirm_approver_2_id:
            raise UserError(_("Approvers not selected for this confirmation request."))
        
        current_user = self.env.user
        
        if current_user == self.ks_confirm_approver_1_id:
            if self.ks_confirm_pm1_approved:
                raise UserError(_("You have already approved this confirmation request."))
            self.write({
                'ks_confirm_pm1_approved': True,
                'ks_confirm_pm1_reason': reason,
            })
            self.message_post(
                body=_("Approver 1 (%s) approved the PO. Reason: %s") % (current_user.name, reason),
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
            
            # Mark PM1 activity as done and create activity for PM2
            self.env['mail.activity'].search([
                ('res_model', '=', self._name),
                ('res_id', '=', self.id),
                ('user_id', '=', self.ks_confirm_approver_1_id.id),
                ('summary', 'ilike', 'PO Confirmation Approval'),
            ]).action_done()
            
            # Create activity for Approver 2 (PM2) to review confirmation request
            # This will trigger a notification popup: "A new approval task has been assigned to you."
            self._create_approval_activity(
                user_id=self.ks_confirm_approver_2_id.id,
                summary=_('PO Confirmation Approval for: %s - PM1 Approved') % self.name,
                note=_('Purchase Order %s confirmation has been approved by PM1 (%s). Please review and approve or reject. Reason: %s') % (
                    self.name, current_user.name, reason
                ),
            )
        elif current_user == self.ks_confirm_approver_2_id:
            # Sequential: Check if Approver 1 has approved
            if not self.ks_confirm_pm1_approved:
                raise UserError(_("Approver 1 must approve before Approver 2 can approve."))
            if self.ks_confirm_pm2_approved:
                raise UserError(_("You have already approved this confirmation request."))
            self.write({
                'ks_confirm_pm2_approved': True,
                'ks_confirm_pm2_reason': reason,
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
                ('user_id', '=', self.ks_confirm_approver_2_id.id),
                ('summary', 'ilike', 'PO Confirmation Approval'),
            ]).action_done()
        else:
            raise UserError(_("You are not authorized to approve this confirmation request."))
        
        # Check if both approvers have approved
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
                body=_("Purchase Order confirmed after both Approver 1 and Approver 2 approval."),
                message_type='notification',
                subtype_xmlid='mail.mt_comment',
            )
            
            if self.partner_id not in self.message_partner_ids:
                self.message_subscribe([self.partner_id.id])
            
            # Create activity for requester to notify confirmation is complete
            if self.ks_confirm_request_user_id:
                self._create_approval_activity(
                    user_id=self.ks_confirm_request_user_id.id,
                    summary=_('PO Confirmed: %s') % self.name,
                    note=_('Purchase Order %s has been confirmed after approval from both Approver 1 and Approver 2.') % self.name,
                )
        
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
        
        if not self.ks_confirm_approver_1_id or not self.ks_confirm_approver_2_id:
            raise UserError(_("Approvers not selected for this confirmation request."))
        
        current_user = self.env.user
        
        if current_user not in (self.ks_confirm_approver_1_id | self.ks_confirm_approver_2_id):
            raise UserError(_("You are not authorized to reject this confirmation request."))
        
        # Reset to draft state
        self.write({
            'state': 'draft',
            'ks_confirm_pm1_approved': False,
            'ks_confirm_pm2_approved': False,
            'ks_confirm_request_user_id': False,
            'ks_confirm_request_date': False,
            'ks_confirm_approver_1_id': False,
            'ks_confirm_approver_2_id': False,
        })
        
        self.message_post(
            body=_("Confirmation rejected by %s. Reason: %s") % (current_user.name, reason),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        # Mark approver activities as done
        self.env['mail.activity'].search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('user_id', 'in', [self.ks_confirm_approver_1_id.id, self.ks_confirm_approver_2_id.id]),
            ('summary', 'ilike', 'PO Confirmation Approval'),
        ]).action_done()
        
        # Create activity for requester to notify rejection
        if self.ks_confirm_request_user_id:
            self._create_approval_activity(
                user_id=self.ks_confirm_request_user_id.id,
                summary=_('PO Confirmation Rejected: %s') % self.name,
                note=_('Purchase Order %s confirmation request has been rejected by %s. Reason: %s') % (
                    self.name, current_user.name, reason
                ),
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

    def ks_do_request_update(self, reason, approver_1_id, approver_2_id):
        """Execute update request with selected approvers"""
        self.ensure_one()
        if not reason:
            raise UserError(_("Update request reason is required."))
        
        if not approver_1_id or not approver_2_id:
            raise UserError(_("Both Approver 1 and Approver 2 are required."))
        
        approver_1 = self.env['res.users'].browse(approver_1_id)
        approver_2 = self.env['res.users'].browse(approver_2_id)
        
        self.write({
            'state': 'update_requested',
            'ks_update_request_reason': reason,
            'ks_update_request_user_id': self.env.user.id,
            'ks_update_request_date': fields.Datetime.now(),
            'ks_update_approver_1_id': approver_1_id,
            'ks_update_approver_2_id': approver_2_id,
            'ks_update_pm1_approved': False,
            'ks_update_pm2_approved': False,
            'ks_update_approved': False,
        })
        
        self.message_post(
            body=_("Update request submitted by %s. Waiting for sequential approval from: Approver 1 - %s, Approver 2 - %s. Reason: %s") % (
                self.env.user.name,
                approver_1.name,
                approver_2.name,
                reason,
            ),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        # Subscribe approver users
        self.message_subscribe(partner_ids=[
            approver_1.partner_id.id,
            approver_2.partner_id.id,
        ])
        
        # Create activity for Approver 1 (PM1) to review update request
        # This will trigger a notification popup: "A new approval task has been assigned to you."
        self._create_approval_activity(
            user_id=approver_1_id,
            summary=_('PO Update Approval for: %s') % self.name,
            note=_('Purchase Order %s has been submitted for update approval by %s. Reason: %s') % (
                self.name, self.env.user.name, reason
            ),
        )
        
        return True

    def ks_action_approve_update(self):
        """Approver approves update request"""
        self.ensure_one()
        if self.state != 'update_requested':
            raise UserError(_("Can only approve update requests in 'Update Requested' state."))
        
        if not self.ks_update_approver_1_id or not self.ks_update_approver_2_id:
            raise UserError(_("Approvers not selected for this update request."))
        
        current_user = self.env.user
        
        # Check authorization - user must be one of the selected approvers
        if current_user not in (self.ks_update_approver_1_id | self.ks_update_approver_2_id):
            raise UserError(_("You are not authorized to approve this update request."))
        
        # Sequential approval: Approver 1 must approve before Approver 2
        if current_user == self.ks_update_approver_2_id and not self.ks_update_pm1_approved:
            raise UserError(_("Approver 1 must approve before Approver 2 can approve."))
        
        # Check if already approved
        if current_user == self.ks_update_approver_1_id and self.ks_update_pm1_approved:
            raise UserError(_("You have already approved this update request."))
        if current_user == self.ks_update_approver_2_id and self.ks_update_pm2_approved:
            raise UserError(_("You have already approved this update request."))

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

        if not self.ks_update_approver_1_id or not self.ks_update_approver_2_id:
            raise UserError(_("Approvers not selected for this update request."))
        
        current_user = self.env.user

        if current_user == self.ks_update_approver_1_id:
            if self.ks_update_pm1_approved:
                raise UserError(_("You have already approved this update request."))
            self.ks_update_pm1_approved = True
            self.message_post(
                body=_("Update approved by Approver 1 (%s). Reason: %s") % (current_user.name, reason),
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
            
            # Mark PM1 activity as done and create activity for PM2
            self.env['mail.activity'].search([
                ('res_model', '=', self._name),
                ('res_id', '=', self.id),
                ('user_id', '=', self.ks_update_approver_1_id.id),
                ('summary', 'ilike', 'PO Update Approval'),
            ]).action_done()
            
            # Create activity for Approver 2 (PM2) to review update request
            # This will trigger a notification popup: "A new approval task has been assigned to you."
            self._create_approval_activity(
                user_id=self.ks_update_approver_2_id.id,
                summary=_('PO Update Approval for: %s - PM1 Approved') % self.name,
                note=_('Purchase Order %s update request has been approved by PM1 (%s). Please review and approve or reject. Reason: %s') % (
                    self.name, current_user.name, reason
                ),
            )
        elif current_user == self.ks_update_approver_2_id:
            # Sequential: Check if Approver 1 has approved
            if not self.ks_update_pm1_approved:
                raise UserError(_("Approver 1 must approve before Approver 2 can approve."))
            if self.ks_update_pm2_approved:
                raise UserError(_("You have already approved this update request."))
            self.ks_update_pm2_approved = True
            self.message_post(
                body=_("Update approved by Approver 2 (%s). Reason: %s") % (current_user.name, reason),
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
            
            # Mark PM2 activity as done
            self.env['mail.activity'].search([
                ('res_model', '=', self._name),
                ('res_id', '=', self.id),
                ('user_id', '=', self.ks_update_approver_2_id.id),
                ('summary', 'ilike', 'PO Update Approval'),
            ]).action_done()
        else:
            raise UserError(_("You are not authorized to approve this update request."))
        
        # Check if both approvers have approved
        if self.ks_update_pm1_approved and self.ks_update_pm2_approved:
            # Both approved - allow editing
            self.write({
                'state': 'purchase',
                'ks_update_approved': True,
            })
            
            self.message_post(
                body=_("Update approved by both Approver 1 and Approver 2. %s can now edit this PO.") % (
                    self.ks_update_request_user_id.name
                ),
                message_type='notification',
                subtype_xmlid='mail.mt_comment',
            )
            
            # Create activity for requester to notify update is approved and they can edit
            if self.ks_update_request_user_id:
                self._create_approval_activity(
                    user_id=self.ks_update_request_user_id.id,
                    summary=_('PO Update Approved: %s - Ready to Edit') % self.name,
                    note=_('Purchase Order %s update request has been approved by both Approver 1 and Approver 2. You can now edit this PO.') % self.name,
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
        
        if not self.ks_update_approver_1_id or not self.ks_update_approver_2_id:
            raise UserError(_("Approvers not selected for this update request."))
        
        current_user = self.env.user
        
        if current_user not in (self.ks_update_approver_1_id | self.ks_update_approver_2_id):
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
            'ks_update_approver_1_id': False,
            'ks_update_approver_2_id': False,
        })
        
        self.message_post(
            body=_("Update request rejected by %s. Reason: %s") % (current_user.name, reason),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        # Mark approver activities as done
        self.env['mail.activity'].search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('user_id', 'in', [self.ks_update_approver_1_id.id, self.ks_update_approver_2_id.id]),
            ('summary', 'ilike', 'PO Update Approval'),
        ]).action_done()
        
        # Create activity for requester to notify rejection
        if self.ks_update_request_user_id:
            self._create_approval_activity(
                user_id=self.ks_update_request_user_id.id,
                summary=_('PO Update Request Rejected: %s') % self.name,
                note=_('Purchase Order %s update request has been rejected by %s. Reason: %s') % (
                    self.name, current_user.name, reason
                ),
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
            'ks_update_approver_1_id': False,
            'ks_update_approver_2_id': False,
        })
        
        self.message_post(
            body=_("Update completed by %s. PO is now locked.") % self.env.user.name,
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        # Mark update completion activity as done
        self.env['mail.activity'].search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('user_id', '=', self.env.user.id),
            ('summary', 'ilike', 'PO Update Approved'),
        ]).action_done()
        
        return True

    # ===== Cancel Request Methods =====
    
    def button_cancel(self):
        """Override: Normal users must request cancellation for confirmed POs, PMs can directly cancel"""
        for order in self:
            # Check if approval config exists
            if not order._has_approval_config():
                # No config, use standard behavior
                return super().button_cancel()
            
            configs = order._get_approval_configs()
            all_approvers = configs.mapped('user_id')
            is_pm = self.env.user in all_approvers
            
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

    def ks_do_request_cancel(self, reason, approver_1_id, approver_2_id):
        """Execute cancel request with selected approvers"""
        self.ensure_one()
        if not reason:
            raise UserError(_("Cancel request reason is required."))
        
        if not approver_1_id or not approver_2_id:
            raise UserError(_("Both Approver 1 and Approver 2 are required."))
        
        approver_1 = self.env['res.users'].browse(approver_1_id)
        approver_2 = self.env['res.users'].browse(approver_2_id)
        
        self.write({
            'state': 'cancel_requested',
            'ks_cancel_request_reason': reason,
            'ks_cancel_request_user_id': self.env.user.id,
            'ks_cancel_request_date': fields.Datetime.now(),
            'ks_cancel_approver_1_id': approver_1_id,
            'ks_cancel_approver_2_id': approver_2_id,
            'ks_cancel_pm1_approved': False,
            'ks_cancel_pm2_approved': False,
        })
        
        self.message_post(
            body=_("Cancellation request submitted by %s. Waiting for sequential approval from: Approver 1 - %s, Approver 2 - %s. \n\n Reason: %s") % (
                self.env.user.name,
                approver_1.name,
                approver_2.name,
                reason
            ),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        # Subscribe approver users
        self.message_subscribe(partner_ids=[
            approver_1.partner_id.id,
            approver_2.partner_id.id,
        ])
        
        # Create activity for Approver 1 (PM1) to review cancel request
        # This will trigger a notification popup: "A new approval task has been assigned to you."
        self._create_approval_activity(
            user_id=approver_1_id,
            summary=_('PO Cancellation Approval for: %s') % self.name,
            note=_('Purchase Order %s has been submitted for cancellation approval by %s. Reason: %s') % (
                self.name, self.env.user.name, reason
            ),
        )
        
        return True

    def ks_action_approve_cancel(self):
        """Approver approves cancel request"""
        self.ensure_one()
        if self.state != 'cancel_requested':
            raise UserError(_("Can only approve cancel requests in 'Cancel Requested' state."))
        
        if not self.ks_cancel_approver_1_id or not self.ks_cancel_approver_2_id:
            raise UserError(_("Approvers not selected for this cancel request."))
        
        current_user = self.env.user
        
        # Check authorization - user must be one of the selected approvers
        if current_user not in (self.ks_cancel_approver_1_id | self.ks_cancel_approver_2_id):
            raise UserError(_("You are not authorized to approve this cancel request."))
        
        # Sequential approval: Approver 1 must approve before Approver 2
        if current_user == self.ks_cancel_approver_2_id and not self.ks_cancel_pm1_approved:
            raise UserError(_("Approver 1 must approve before Approver 2 can approve."))
        
        # Check if already approved
        if current_user == self.ks_cancel_approver_1_id:
            if self.ks_cancel_pm1_approved:
                raise UserError(_("You have already approved this cancel request."))
            self.ks_cancel_pm1_approved = True
            self.message_post(
                body=_("Cancellation approved by Approver 1: %s") % current_user.name,
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
            
            # Mark PM1 activity as done and create activity for PM2
            self.env['mail.activity'].search([
                ('res_model', '=', self._name),
                ('res_id', '=', self.id),
                ('user_id', '=', self.ks_cancel_approver_1_id.id),
                ('summary', 'ilike', 'PO Cancellation Approval'),
            ]).action_done()
            
            # Create activity for Approver 2 (PM2) to review cancel request
            # This will trigger a notification popup: "A new approval task has been assigned to you."
            self._create_approval_activity(
                user_id=self.ks_cancel_approver_2_id.id,
                summary=_('PO Cancellation Approval for: %s - PM1 Approved') % self.name,
                note=_('Purchase Order %s cancellation request has been approved by PM1 (%s). Please review and approve or reject.') % (
                    self.name, current_user.name
                ),
            )
        elif current_user == self.ks_cancel_approver_2_id:
            if self.ks_cancel_pm2_approved:
                raise UserError(_("You have already approved this cancel request."))
            self.ks_cancel_pm2_approved = True
            self.message_post(
                body=_("Cancellation approved by Approver 2: %s") % current_user.name,
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
            
            # Mark PM2 activity as done
            self.env['mail.activity'].search([
                ('res_model', '=', self._name),
                ('res_id', '=', self.id),
                ('user_id', '=', self.ks_cancel_approver_2_id.id),
                ('summary', 'ilike', 'PO Cancellation Approval'),
            ]).action_done()
        else:
            raise UserError(_("You are not authorized to approve this cancel request."))
        
        # Check if both approvers have approved
        if self.ks_cancel_pm1_approved and self.ks_cancel_pm2_approved:
            # Both approved - cancel the PO
            self.write({
                'state': 'cancel',
                'mail_reminder_confirmed': False,
            })
            
            self.message_post(
                body=_("Purchase Order cancelled after both Approver 1 and Approver 2 approval."),
                message_type='notification',
                subtype_xmlid='mail.mt_comment',
            )
            
            # Create activity for requester to notify cancellation is complete
            if self.ks_cancel_request_user_id:
                self._create_approval_activity(
                    user_id=self.ks_cancel_request_user_id.id,
                    summary=_('PO Cancelled: %s') % self.name,
                    note=_('Purchase Order %s has been cancelled after approval from both Approver 1 and Approver 2.') % self.name,
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
        
        if not self.ks_cancel_approver_1_id or not self.ks_cancel_approver_2_id:
            raise UserError(_("Approvers not selected for this cancel request."))
        
        current_user = self.env.user
        
        if current_user not in (self.ks_cancel_approver_1_id | self.ks_cancel_approver_2_id):
            raise UserError(_("You are not authorized to reject this cancel request."))
        
        # Return to purchase state
        self.write({
            'state': 'purchase',
            'ks_cancel_pm1_approved': False,
            'ks_cancel_pm2_approved': False,
            'ks_cancel_request_reason': False,
            'ks_cancel_request_user_id': False,
            'ks_cancel_request_date': False,
            'ks_cancel_approver_1_id': False,
            'ks_cancel_approver_2_id': False,
        })
        
        self.message_post(
            body=_("Cancellation request rejected by %s. Reason: %s") % (current_user.name, reason),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        # Mark approver activities as done
        self.env['mail.activity'].search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('user_id', 'in', [self.ks_cancel_approver_1_id.id, self.ks_cancel_approver_2_id.id]),
            ('summary', 'ilike', 'PO Cancellation Approval'),
        ]).action_done()
        
        # Create activity for requester to notify rejection
        if self.ks_cancel_request_user_id:
            self._create_approval_activity(
                user_id=self.ks_cancel_request_user_id.id,
                summary=_('PO Cancellation Request Rejected: %s') % self.name,
                note=_('Purchase Order %s cancellation request has been rejected by %s. Reason: %s') % (
                    self.name, current_user.name, reason
                ),
            )
        
        return True

    # ===== Override Unlock (Only for PMs) =====
    
    def button_unlock(self):
        """Override: Only approver users can unlock, and reset update approval"""
        for order in self:
            if order._has_approval_config():
                all_approvers = self.env['ks.purchase.approval.config'].search([('active', '=', True)]).mapped('user_id')
                if self.env.user not in all_approvers:
                    raise UserError(_("Only approver users can unlock Purchase Orders."))
            
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
