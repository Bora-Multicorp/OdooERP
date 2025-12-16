# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""
PO Approval User Model

This model manages the list of users who can act as approvers
for Purchase Orders in the two-level approval workflow.

Users added to this model will appear in the PM1/PM2 selection
dropdowns on Purchase Orders.
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class POApprovalUser(models.Model):
    """
    Model to manage PO Approval Users (PM Approvers).
    
    This model allows administrators to configure which users
    can act as PM1 or PM2 approvers for Purchase Orders.
    """
    _name = 'po.approval.user'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'PO Approval User'
    _order = 'sequence, name'
    _rec_name = 'user_id'

    # =============================================
    # FIELDS DEFINITION
    # =============================================

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True,
        help="Display name of the approval user."
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Sequence for ordering approval users."
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        ondelete='cascade',
        help="The user who can act as an approver."
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help="If unchecked, the user will not appear in approval selection."
    )
    
    # User information (related fields for display)
    user_email = fields.Char(
        string='Email',
        related='user_id.email',
        readonly=True
    )
    
    user_phone = fields.Char(
        string='Phone',
        related='user_id.phone',
        readonly=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help="Company for which this approval user is configured."
    )
    
    # Approval role/level
    approval_level = fields.Selection([
        ('pm1', 'PM1 - First Level Approver'),
        ('pm2', 'PM2 - Second Level Approver'),
        ('both', 'Both PM1 and PM2'),
    ], string='Approval Level', default='both', required=True,
       help="Defines at which level this user can approve:\n"
            "- PM1: Can only approve as first level approver\n"
            "- PM2: Can only approve as second level approver\n"
            "- Both: Can approve at any level")
    
    # Statistics
    pending_approval_count = fields.Integer(
        string='Pending Approvals',
        compute='_compute_pending_approval_count',
        help="Number of POs pending approval from this user."
    )
    
    total_approved_count = fields.Integer(
        string='Total Approved',
        compute='_compute_approval_stats',
        help="Total number of POs approved by this user."
    )

    # =============================================
    # CONSTRAINTS
    # =============================================

    _sql_constraints = [
        ('user_company_unique', 
         'UNIQUE(user_id, company_id)', 
         'This user is already configured as an approval user for this company!')
    ]

    @api.constrains('user_id')
    def _check_user_has_pm_group(self):
        """
        Ensure the selected user belongs to the PM User group.
        """
        pm_group = self.env.ref('purchase_two_level_approval.group_po_pm_user', raise_if_not_found=False)
        for record in self:
            if pm_group and pm_group not in record.user_id.groups_id:
                raise ValidationError(_(
                    "User '%s' must belong to the 'PM User (Approver)' group to be added as an approval user.\n"
                    "Please add the user to the group first: Settings > Users > Groups > PO Approval > PM User (Approver)"
                ) % record.user_id.name)

    # =============================================
    # COMPUTE METHODS
    # =============================================

    @api.depends('user_id', 'user_id.name')
    def _compute_name(self):
        """Compute display name from user."""
        for record in self:
            record.name = record.user_id.name if record.user_id else ''

    def _compute_pending_approval_count(self):
        """Compute count of POs pending approval from this user."""
        PurchaseOrder = self.env['purchase.order']
        for record in self:
            # Count POs where this user is PM1 and hasn't approved
            pm1_pending = PurchaseOrder.search_count([
                ('state', '=', 'pending_pm_approval'),
                ('pm1_id', '=', record.user_id.id),
                ('pm1_approved', '=', False)
            ])
            # Count POs where this user is PM2 and hasn't approved
            pm2_pending = PurchaseOrder.search_count([
                ('state', '=', 'pending_pm_approval'),
                ('pm2_id', '=', record.user_id.id),
                ('pm2_approved', '=', False)
            ])
            record.pending_approval_count = pm1_pending + pm2_pending

    def _compute_approval_stats(self):
        """Compute total approved POs by this user."""
        PurchaseOrder = self.env['purchase.order']
        for record in self:
            # Count as PM1
            pm1_approved = PurchaseOrder.search_count([
                ('pm1_id', '=', record.user_id.id),
                ('pm1_approved', '=', True)
            ])
            # Count as PM2
            pm2_approved = PurchaseOrder.search_count([
                ('pm2_id', '=', record.user_id.id),
                ('pm2_approved', '=', True)
            ])
            record.total_approved_count = pm1_approved + pm2_approved

    # =============================================
    # ACTION METHODS
    # =============================================

    def action_view_pending_approvals(self):
        """Open list of POs pending approval from this user."""
        self.ensure_one()
        return {
            'name': _('Pending Approvals - %s') % self.user_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'domain': [
                ('state', '=', 'pending_pm_approval'),
                '|',
                '&', ('pm1_id', '=', self.user_id.id), ('pm1_approved', '=', False),
                '&', ('pm2_id', '=', self.user_id.id), ('pm2_approved', '=', False),
            ],
            'context': {'create': False},
        }

    def action_add_to_pm_group(self):
        """Add the user to PM User group if not already."""
        self.ensure_one()
        pm_group = self.env.ref('purchase_two_level_approval.group_po_pm_user', raise_if_not_found=False)
        if pm_group and pm_group not in self.user_id.groups_id:
            self.user_id.sudo().write({
                'groups_id': [(4, pm_group.id)]
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('User %s has been added to PM User group.') % self.user_id.name,
                    'type': 'success',
                }
            }

