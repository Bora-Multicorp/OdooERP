# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""
Purchase Order Two-Level Approval Module

This module extends the standard Purchase Order model to implement
a two-level PM approval workflow.

Key Features:
- New state: 'pending_pm_approval' for POs awaiting approval
- Two PM approvers (PM1 and PM2) with individual approval tracking
- PO locking for normal users when pending approval
- Direct confirm capability for PM users and A/C Head
- Notification system for approval requests
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError


# Extended state selection for Purchase Order
PURCHASE_ORDER_STATE = [
    ('draft', 'RFQ'),
    ('sent', 'RFQ Sent'),
    ('pending_pm_approval', 'Pending PM Approval'),  # New state for two-level approval
    ('to approve', 'To Approve'),
    ('purchase', 'Purchase Order'),
    ('done', 'Locked'),
    ('cancel', 'Cancelled')
]


class PurchaseOrder(models.Model):
    """
    Extended Purchase Order model with two-level PM approval workflow.
    
    This model adds:
    - PM1 and PM2 assignment fields
    - Individual approval status tracking for each PM
    - Methods for PM approval and direct confirmation
    - PO locking logic based on user roles
    """
    _inherit = 'purchase.order'

    # =============================================
    # FIELDS DEFINITION
    # =============================================

    # Override state field to include new 'pending_pm_approval' state
    state = fields.Selection(
        selection=PURCHASE_ORDER_STATE,
        string='Status',
        readonly=True,
        index=True,
        copy=False,
        default='draft',
        tracking=True
    )

    # PM1 Assignment and Approval Status
    # Domain is set dynamically via fields_get override to filter PM users
    pm1_id = fields.Many2one(
        'res.users',
        string='PM 1 (First Approver)',
        tracking=True,
        help="First Project Manager who needs to approve this Purchase Order."
    )
    pm1_approved = fields.Boolean(
        string='PM1 Approved',
        default=False,
        copy=False,
        tracking=True,
        help="Indicates whether PM1 has approved this Purchase Order."
    )
    pm1_approved_date = fields.Datetime(
        string='PM1 Approval Date',
        readonly=True,
        copy=False,
        help="Date and time when PM1 approved this Purchase Order."
    )

    # PM2 Assignment and Approval Status
    # Domain is set dynamically via fields_get override to filter PM users
    pm2_id = fields.Many2one(
        'res.users',
        string='PM 2 (Second Approver)',
        tracking=True,
        help="Second Project Manager who needs to approve this Purchase Order."
    )
    pm2_approved = fields.Boolean(
        string='PM2 Approved',
        default=False,
        copy=False,
        tracking=True,
        help="Indicates whether PM2 has approved this Purchase Order."
    )
    pm2_approved_date = fields.Datetime(
        string='PM2 Approval Date',
        readonly=True,
        copy=False,
        help="Date and time when PM2 approved this Purchase Order."
    )

    # Computed field to check if current user is PM or A/C Head
    is_pm_or_ac_head = fields.Boolean(
        string='Is PM or A/C Head',
        compute='_compute_is_pm_or_ac_head',
        help="Technical field to determine if current user has PM or A/C Head permissions."
    )

    # Computed field to check if current user can approve as PM1
    can_approve_as_pm1 = fields.Boolean(
        string='Can Approve as PM1',
        compute='_compute_can_approve_as_pm',
        help="Technical field to show/hide PM1 approval button."
    )

    # Computed field to check if current user can approve as PM2
    can_approve_as_pm2 = fields.Boolean(
        string='Can Approve as PM2',
        compute='_compute_can_approve_as_pm',
        help="Technical field to show/hide PM2 approval button."
    )

    # Computed field for overall approval status
    approval_status = fields.Selection([
        ('not_submitted', 'Not Submitted'),
        ('pending', 'Pending Approval'),
        ('partial', 'Partially Approved'),
        ('approved', 'Fully Approved'),
    ], string='Approval Status', compute='_compute_approval_status', store=True)

    # Field to track if PO is locked for normal user
    is_locked_for_user = fields.Boolean(
        string='Locked for Current User',
        compute='_compute_is_locked_for_user',
        help="Indicates if the PO is locked (read-only) for the current user."
    )

    # =============================================
    # FIELDS_GET OVERRIDE FOR DYNAMIC DOMAIN
    # =============================================

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """
        Override fields_get to dynamically set domain for PM user fields.
        This filters the PM1 and PM2 dropdown to show only users configured
        in the PO Approval Users model.
        """
        res = super().fields_get(allfields, attributes)
        
        # Get user IDs from po.approval.user model
        approval_users = self.env['po.approval.user'].search([('active', '=', True)])
        
        if approval_users:
            # Get users configured for PM1 (pm1 or both)
            pm1_user_ids = approval_users.filtered(
                lambda u: u.approval_level in ('pm1', 'both')
            ).mapped('user_id').ids
            
            # Get users configured for PM2 (pm2 or both)
            pm2_user_ids = approval_users.filtered(
                lambda u: u.approval_level in ('pm2', 'both')
            ).mapped('user_id').ids
            
            # Set domain for pm1_id field
            if 'pm1_id' in res and pm1_user_ids:
                res['pm1_id']['domain'] = [('id', 'in', pm1_user_ids)]
            
            # Set domain for pm2_id field
            if 'pm2_id' in res and pm2_user_ids:
                res['pm2_id']['domain'] = [('id', 'in', pm2_user_ids)]
        else:
            # Fallback: If no approval users configured, show users in PM group
            pm_group = self.env.ref('purchase_two_level_approval.group_po_pm_user', raise_if_not_found=False)
            if pm_group:
                pm_domain = [('groups_id', 'in', [pm_group.id])]
                if 'pm1_id' in res:
                    res['pm1_id']['domain'] = pm_domain
                if 'pm2_id' in res:
                    res['pm2_id']['domain'] = pm_domain
        
        return res

    # =============================================
    # COMPUTE METHODS
    # =============================================

    @api.depends_context('uid')
    def _compute_is_pm_or_ac_head(self):
        """
        Compute if the current user belongs to PM User or A/C Head group.
        This determines UI visibility and action permissions.
        """
        is_pm = self.env.user.has_group('purchase_two_level_approval.group_po_pm_user')
        is_ac_head = self.env.user.has_group('purchase_two_level_approval.group_po_ac_head')
        for order in self:
            order.is_pm_or_ac_head = is_pm or is_ac_head

    @api.depends('pm1_id', 'pm2_id', 'pm1_approved', 'pm2_approved', 'state')
    @api.depends_context('uid')
    def _compute_can_approve_as_pm(self):
        """
        Compute if current user can approve as PM1 or PM2.
        User can approve if:
        - They are the assigned PM for that slot
        - OR they are an A/C Head (can approve any)
        - AND the PO is in pending_pm_approval state
        - AND they haven't already approved
        """
        is_ac_head = self.env.user.has_group('purchase_two_level_approval.group_po_ac_head')
        current_user = self.env.user

        for order in self:
            # Check PM1 approval capability
            order.can_approve_as_pm1 = (
                order.state == 'pending_pm_approval'
                and not order.pm1_approved
                and (order.pm1_id == current_user or is_ac_head)
            )

            # Check PM2 approval capability
            order.can_approve_as_pm2 = (
                order.state == 'pending_pm_approval'
                and not order.pm2_approved
                and (order.pm2_id == current_user or is_ac_head)
            )

    @api.depends('state', 'pm1_approved', 'pm2_approved')
    def _compute_approval_status(self):
        """
        Compute the overall approval status based on PM approvals.
        """
        for order in self:
            if order.state != 'pending_pm_approval':
                if order.state in ['draft', 'sent']:
                    order.approval_status = 'not_submitted'
                else:
                    order.approval_status = 'approved'
            elif order.pm1_approved and order.pm2_approved:
                order.approval_status = 'approved'
            elif order.pm1_approved or order.pm2_approved:
                order.approval_status = 'partial'
            else:
                order.approval_status = 'pending'

    @api.depends('state')
    @api.depends_context('uid')
    def _compute_is_locked_for_user(self):
        """
        Compute if the PO is locked for the current user.
        PO is locked for normal users when in 'pending_pm_approval' state.
        PM users and A/C Head can always edit.
        """
        is_pm_or_higher = (
            self.env.user.has_group('purchase_two_level_approval.group_po_pm_user')
            or self.env.user.has_group('purchase_two_level_approval.group_po_ac_head')
        )
        for order in self:
            if is_pm_or_higher:
                order.is_locked_for_user = False
            else:
                order.is_locked_for_user = order.state == 'pending_pm_approval'

    # =============================================
    # CRUD OVERRIDE METHODS
    # =============================================

    def write(self, vals):
        """
        Override write to enforce PO locking rules.
        Normal users cannot edit POs in 'pending_pm_approval' state.
        """
        # Check if user is trying to edit a locked PO
        for order in self:
            if order.state == 'pending_pm_approval':
                # Allow state changes and approval-related fields
                allowed_fields = {
                    'state', 'pm1_approved', 'pm2_approved', 
                    'pm1_approved_date', 'pm2_approved_date',
                    'message_follower_ids', 'message_ids', 'activity_ids'
                }
                changing_other_fields = set(vals.keys()) - allowed_fields
                
                if changing_other_fields:
                    is_pm_or_higher = (
                        self.env.user.has_group('purchase_two_level_approval.group_po_pm_user')
                        or self.env.user.has_group('purchase_two_level_approval.group_po_ac_head')
                    )
                    if not is_pm_or_higher:
                        raise AccessError(_(
                            "You cannot edit this Purchase Order while it is pending PM approval. "
                            "Please contact a PM or A/C Head to make changes."
                        ))
        
        return super().write(vals)

    # =============================================
    # BUTTON CONFIRM OVERRIDE
    # =============================================

    def button_confirm(self):
        """
        Override the standard confirm button behavior.
        
        For Normal Users:
        - Submits PO for PM approval (state: 'pending_pm_approval')
        - Sends notification to assigned PMs
        - PO becomes locked for normal user
        
        For PM Users / A/C Head:
        - Standard Odoo behavior (calls parent method)
        
        Returns:
            bool: True if successful
        """
        for order in self:
            if order.state not in ['draft', 'sent']:
                continue
            
            # Validate analytic distribution
            order.order_line._validate_analytic_distribution()
            
            # Check if user is PM or A/C Head
            is_pm_or_higher = (
                self.env.user.has_group('purchase_two_level_approval.group_po_pm_user')
                or self.env.user.has_group('purchase_two_level_approval.group_po_ac_head')
            )
            
            if is_pm_or_higher:
                # PM/A/C Head can confirm directly using standard flow
                order._add_supplier_to_product()
                if order._approval_allowed():
                    order.button_approve()
                else:
                    order.write({'state': 'to approve'})
            else:
                # Normal user - submit for PM approval
                if not order.pm1_id and not order.pm2_id:
                    raise UserError(_(
                        "Please assign at least one PM (PM1 or PM2) before submitting for approval."
                    ))
                
                # Move to pending PM approval state
                order.write({
                    'state': 'pending_pm_approval',
                    'pm1_approved': False,
                    'pm2_approved': False,
                    'pm1_approved_date': False,
                    'pm2_approved_date': False,
                })
                
                # Subscribe partner to the PO if not already
                if order.partner_id not in order.message_partner_ids:
                    order.message_subscribe([order.partner_id.id])
                
                # Send notification to PMs
                order._send_pm_approval_notification()
                
                # Log message
                order.message_post(
                    body=_("Purchase Order submitted for PM approval by %s.") % self.env.user.name,
                    subtype_xmlid='mail.mt_note'
                )
        
        return True

    # =============================================
    # PM APPROVAL METHODS
    # =============================================

    def action_approve_as_pm1(self):
        """
        Action for PM1 to approve the Purchase Order.
        
        Validates:
        - User is PM1 or A/C Head
        - PO is in pending_pm_approval state
        - PM1 hasn't already approved
        
        After approval:
        - Sets pm1_approved = True
        - Records approval datetime
        - Checks if both PMs have approved
        - If both approved, moves to confirmed state
        """
        self.ensure_one()
        
        # Validate permission
        is_ac_head = self.env.user.has_group('purchase_two_level_approval.group_po_ac_head')
        if self.pm1_id != self.env.user and not is_ac_head:
            raise UserError(_("Only the assigned PM1 or A/C Head can approve as PM1."))
        
        if self.state != 'pending_pm_approval':
            raise UserError(_("This Purchase Order is not pending PM approval."))
        
        if self.pm1_approved:
            raise UserError(_("PM1 has already approved this Purchase Order."))
        
        # Record approval
        self.write({
            'pm1_approved': True,
            'pm1_approved_date': fields.Datetime.now(),
        })
        
        # Log approval message
        self.message_post(
            body=_("PM1 Approval: %s has approved this Purchase Order.") % self.env.user.name,
            subtype_xmlid='mail.mt_comment'
        )
        
        # Check if both PMs approved
        self._check_full_approval()
        
        return True

    def action_approve_as_pm2(self):
        """
        Action for PM2 to approve the Purchase Order.
        
        Similar to action_approve_as_pm1 but for PM2.
        """
        self.ensure_one()
        
        # Validate permission
        is_ac_head = self.env.user.has_group('purchase_two_level_approval.group_po_ac_head')
        if self.pm2_id != self.env.user and not is_ac_head:
            raise UserError(_("Only the assigned PM2 or A/C Head can approve as PM2."))
        
        if self.state != 'pending_pm_approval':
            raise UserError(_("This Purchase Order is not pending PM approval."))
        
        if self.pm2_approved:
            raise UserError(_("PM2 has already approved this Purchase Order."))
        
        # Record approval
        self.write({
            'pm2_approved': True,
            'pm2_approved_date': fields.Datetime.now(),
        })
        
        # Log approval message
        self.message_post(
            body=_("PM2 Approval: %s has approved this Purchase Order.") % self.env.user.name,
            subtype_xmlid='mail.mt_comment'
        )
        
        # Check if both PMs approved
        self._check_full_approval()
        
        return True

    def _check_full_approval(self):
        """
        Check if all required approvals are complete and confirm the PO.
        
        Logic:
        - If both PM1 and PM2 are assigned, both must approve
        - If only PM1 is assigned, PM1 approval is sufficient
        - If only PM2 is assigned, PM2 approval is sufficient
        """
        self.ensure_one()
        
        # Determine required approvals
        pm1_required = bool(self.pm1_id)
        pm2_required = bool(self.pm2_id)
        
        # Check if all required approvals are received
        all_approved = True
        if pm1_required and not self.pm1_approved:
            all_approved = False
        if pm2_required and not self.pm2_approved:
            all_approved = False
        
        if all_approved:
            # Both (or all assigned) PMs have approved - confirm the PO
            self._add_supplier_to_product()
            self.button_approve()
            self.message_post(
                body=_("Purchase Order has been fully approved and confirmed."),
                subtype_xmlid='mail.mt_comment'
            )

    def action_confirm_as_pm(self):
        """
        Direct confirm action for PM users and A/C Head.
        
        This allows PM/A/C Head to bypass the two-level approval
        and directly confirm the Purchase Order.
        
        This is useful when:
        - Urgent orders need immediate processing
        - PM has authority to approve without second approval
        """
        self.ensure_one()
        
        # Validate permission
        is_pm = self.env.user.has_group('purchase_two_level_approval.group_po_pm_user')
        is_ac_head = self.env.user.has_group('purchase_two_level_approval.group_po_ac_head')
        
        if not is_pm and not is_ac_head:
            raise UserError(_(
                "Only PM users or A/C Head can use the direct confirm feature."
            ))
        
        if self.state not in ['draft', 'sent', 'pending_pm_approval']:
            raise UserError(_("This Purchase Order cannot be confirmed in its current state."))
        
        # Validate analytic distribution
        self.order_line._validate_analytic_distribution()
        
        # Add supplier to product
        self._add_supplier_to_product()
        
        # Set both approvals as complete (by PM action)
        self.write({
            'pm1_approved': True,
            'pm2_approved': True,
            'pm1_approved_date': fields.Datetime.now() if not self.pm1_approved_date else self.pm1_approved_date,
            'pm2_approved_date': fields.Datetime.now() if not self.pm2_approved_date else self.pm2_approved_date,
        })
        
        # Confirm the order
        if self._approval_allowed():
            self.button_approve()
        else:
            self.write({'state': 'to approve'})
        
        # Subscribe partner
        if self.partner_id not in self.message_partner_ids:
            self.message_subscribe([self.partner_id.id])
        
        # Log the direct confirmation
        self.message_post(
            body=_("Purchase Order directly confirmed by PM/A/C Head: %s") % self.env.user.name,
            subtype_xmlid='mail.mt_comment'
        )
        
        return True

    # =============================================
    # NOTIFICATION METHODS
    # =============================================

    def _send_pm_approval_notification(self):
        """
        Send notification to assigned PMs requesting approval.
        Creates activities for PM1 and PM2 to approve the PO.
        """
        self.ensure_one()
        
        # Get activity type for approval
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not activity_type:
            return
        
        # Create activity for PM1
        if self.pm1_id:
            self.activity_schedule(
                activity_type_id=activity_type.id,
                summary=_("PO Approval Required (PM1)"),
                note=_("Please review and approve this Purchase Order as PM1."),
                user_id=self.pm1_id.id,
            )
        
        # Create activity for PM2
        if self.pm2_id:
            self.activity_schedule(
                activity_type_id=activity_type.id,
                summary=_("PO Approval Required (PM2)"),
                note=_("Please review and approve this Purchase Order as PM2."),
                user_id=self.pm2_id.id,
            )

    # =============================================
    # ACTION METHODS
    # =============================================

    def button_draft(self):
        """
        Override to reset approval fields when moving back to draft.
        """
        res = super().button_draft()
        self.write({
            'pm1_approved': False,
            'pm2_approved': False,
            'pm1_approved_date': False,
            'pm2_approved_date': False,
        })
        return res

    def button_cancel(self):
        """
        Override to allow cancellation from pending_pm_approval state.
        """
        # Check for POs with invoices (standard check)
        purchase_orders_with_invoices = self.filtered(
            lambda po: any(i.state not in ('cancel', 'draft') for i in po.invoice_ids)
        )
        if purchase_orders_with_invoices:
            from odoo.tools import format_list
            raise UserError(_(
                "Unable to cancel purchase order(s): %s. You must first cancel their related vendor bills.",
                format_list(self.env, purchase_orders_with_invoices.mapped('display_name'))
            ))
        
        # Reset approval fields on cancel
        self.write({
            'state': 'cancel',
            'mail_reminder_confirmed': False,
            'pm1_approved': False,
            'pm2_approved': False,
            'pm1_approved_date': False,
            'pm2_approved_date': False,
        })

    def action_reject_approval(self):
        """
        Action for PM users to reject the PO and send it back to draft.
        Only available when PO is in pending_pm_approval state.
        """
        self.ensure_one()
        
        # Validate permission
        is_pm = self.env.user.has_group('purchase_two_level_approval.group_po_pm_user')
        is_ac_head = self.env.user.has_group('purchase_two_level_approval.group_po_ac_head')
        
        if not is_pm and not is_ac_head:
            raise UserError(_("Only PM users or A/C Head can reject Purchase Orders."))
        
        if self.state != 'pending_pm_approval':
            raise UserError(_("This Purchase Order is not pending PM approval."))
        
        # Move back to draft and reset approvals
        self.write({
            'state': 'draft',
            'pm1_approved': False,
            'pm2_approved': False,
            'pm1_approved_date': False,
            'pm2_approved_date': False,
        })
        
        # Log rejection
        self.message_post(
            body=_("Purchase Order rejected and sent back to draft by %s.") % self.env.user.name,
            subtype_xmlid='mail.mt_comment'
        )
        
        # Mark existing approval activities as done
        self.activity_ids.filtered(
            lambda a: 'PO Approval Required' in (a.summary or '')
        ).action_done()
        
        return True

    # =============================================
    # HELPER METHODS
    # =============================================

    def _is_readonly(self):
        """
        Override to make PO read-only for normal users in pending_pm_approval state.
        
        Returns:
            bool: True if the PO should be read-only for the current user
        """
        self.ensure_one()
        
        # Standard cancel state is always read-only
        if self.state == 'cancel':
            return True
        
        # Check if locked for normal user
        if self.state == 'pending_pm_approval':
            is_pm_or_higher = (
                self.env.user.has_group('purchase_two_level_approval.group_po_pm_user')
                or self.env.user.has_group('purchase_two_level_approval.group_po_ac_head')
            )
            if not is_pm_or_higher:
                return True
        
        return False

