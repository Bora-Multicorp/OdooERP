# -*- coding: utf-8 -*-
import random

from odoo import models, fields, api


class VendorApprovalConfig(models.Model):
    _name = "vendor.approval.config"
    _description = "Vendor Approval Settings"
    _rec_name = 'user_id'

    sequence = fields.Integer(string='Sequence', index=True, tracking=True)
    user_id = fields.Many2one('res.users', string='User', required=True, tracking=True)
    default_user = fields.Boolean(string="Default")
    default_approver = fields.Selection([
        ('approver1', 'Approver 1'),
        ('approver2', 'Approver 2'),
    ], string="Default")
    color = fields.Integer(string="Color Index", readonly=True)

    _sql_constraints = [
        ('unique_user_id', 'unique(user_id)', 'Each approver member must be unique.')
    ]

    existing_user_ids = fields.Many2many('res.users', compute='_compute_existing_user_ids')

    @api.depends('user_id')
    def _compute_existing_user_ids(self):
        # Get all existing users' IDs
        existing_user_ids_list = self.env['vendor.approval.config'].search([]).user_id.ids

        # Convert the list to a set for efficient removal
        existing_user_ids_set = set(existing_user_ids_list)

        for record in self:
            # If the current record has a user_id, remove it from the set
            # The discard() method will not raise an error if the item is not found
            if record.user_id:
                existing_user_ids_set.discard(record.user_id.id)

            # Assign the remaining IDs back to the field
            record.existing_user_ids = [(6, 0, list(existing_user_ids_set))]

    # generate sequence
    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if 'sequence' in fields_list:
            max_sequence = self.search([], order="sequence desc", limit=1).sequence or 0
            defaults['sequence'] = max_sequence + 1
        return defaults

    @api.model
    def create(self, vals):

        # 1. to make sure there will be only one approver and only one approver2
        if vals.get('default_approver'):
            # Find the old approver of the same type and reset them
            self.search([
                ('default_approver', '=', vals['default_approver'])
            ]).write({'default_approver': False})

        # 2. Assign color code
        if not vals.get('color'):
            # Get all used colors
            used_colors = set(self.search([]).mapped('color'))
            all_colors = set(range(1, 12))  # Odoo has 11 tag colors (1..11)

            # Find available colors
            available_colors = list(all_colors - used_colors)

            if not available_colors:
                # If all colors are used, reset and pick randomly
                available_colors = list(all_colors)

            vals['color'] = random.choice(available_colors)

        return super().create(vals)

    # Override write to handle the single approver rule
    def write(self, vals):
        # To make sure there will be only one approver and only one approver2
        if vals.get('default_approver'):
            # Find the old approver of the same type and reset them
            self.search([
                ('id', '!=', self.id),
                ('default_approver', '=', vals['default_approver'])
            ]).write({'default_approver': False})

        return super().write(vals)

    def unlink(self):
        # Step 1: Collect all affected purchase orders
        affected_kyc = self.env['res.partner.kyc.approval']  # empty recordset

        for approver in self:
            # Find all POs where this approver is linked
            kycs = self.env['res.partner.kyc.approval'].search([
                ('approval_users_ids.user_id', '=', approver.user_id.id)
            ])
            affected_kyc |= kycs  # accumulate affected POs

            for kyc in kycs:
                records_to_delete = kyc.approval_users_ids.filtered(
                    lambda r: r.user_id == approver.user_id and not r.state
                )
                records_to_delete.unlink()

        # Step 2: Delete the approvers themselves
        result = super().unlink()

        # Step 3: Re-sequence all remaining approvers globally
        all_approvers = self.env['vendor.approval.config'].search([], order='sequence')
        for idx, record in enumerate(all_approvers, start=1):
            record.sequence = idx

        # Step 4: Re-sequence PO approval users per purchase order
        for kyc in affected_kyc:
            kyc_users = kyc.approval_users_ids.sorted(key='sequence')
            for idx, user in enumerate(kyc_users, start=1):
                user.sequence = idx

        return result
