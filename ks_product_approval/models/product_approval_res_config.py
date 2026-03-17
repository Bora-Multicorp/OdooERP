# -*- coding: utf-8 -*-
import random

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import random


class ProductApprovalConfig(models.Model):
    _name = "product.approval.config"
    _description = "Product Approval Settings"
    _rec_name = 'user_id'
    _order = 'sequence'

    sequence = fields.Integer(string='Sequence', readonly=True)
    user_id = fields.Many2one('res.users', string='User Name', required=True)
    approver_type = fields.Selection([
        ('approver1', 'Approver 1'),
        ('approver2', 'Approver 2'),
    ], string="Approver Type", required=True)
    color = fields.Integer(string="Color Index", readonly=True)

    existing_user_ids = fields.Many2many('res.users', compute='_compute_existing_user_ids')

    @api.depends('user_id')
    def _compute_existing_user_ids(self):
        # Get all existing users' IDs
        existing_user_ids_list = self.env['product.approval.config'].search([]).user_id.ids

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


    # Override create to handle the single approver rule
    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:

            # 1. select colors
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

        res_list = super(ProductApprovalConfig, self).create(vals_list)
        for res in res_list:
            res._update_draft_ks_product_approvals()
        return res_list

    # Override write
    def write(self, vals):
        res = super().write(vals)
        self._update_draft_ks_product_approvals()
        return res

    # @api.constrains('default_user', 'group')
    # def _check_unique_default_user_per_group(self):
    #     for record in self:
    #         if record.default_user:
    #             existing_default_users = self.search([
    #                 ('id', '!=', record.id),
    #                 ('group', '=', record.group),
    #                 ('default_user', '=', True)
    #             ])
    #             if existing_default_users:
    #                 # Reset the previous default user to False
    #                 existing_default_users.write({'default_user': False})

    # @api.onchange('default_user', 'group')
    # def _onchange_default_user(self):
    #     if self.default_user:
    #         existing_default_users = self.search([
    #             ('id', '!=', self._origin.id if self._origin else False),
    #             ('group', '=', self.group),
    #             ('default_user', '=', True)
    #         ])
    #         if existing_default_users:
    #             pass

    def unlink(self):
        # Step 1: Collect all affected product template
        affected_product = self.env['product.template']  # empty recordset

        for approver in self:
            # Find all products where this approver is linked
            products = self.env['product.template'].search([
                ('approval_users_ids.user_id', '=', approver.user_id.id)
            ])
            affected_product |= products  # accumulate affected products

            # Delete linked products approval users with empty state
            for product in products:
                records_to_delete = product.approval_users_ids.filtered(
                    lambda r: r.user_id == approver.user_id and not r.state
                )
                records_to_delete.unlink()

        # Step 2: Delete the approvers themselves
        result = super().unlink()

        # Step 3: Re-sequence all remaining approvers globally
        all_approvers = self.env['product.approval.config'].search([], order='sequence')
        for idx, record in enumerate(all_approvers, start=1):
            record.sequence = idx

        # Step 4: Re-sequence products approval users per product
        for product in affected_product:
            product_users = product.approval_users_ids.sorted(key='sequence')
            for idx, user in enumerate(product_users, start=1):
                user.sequence = idx

        # Step 5: Update draft product approval too 
        self._update_draft_ks_product_approvals()

        return result

    def _update_draft_ks_product_approvals(self):
        """Update approval_users_ids on draft product records."""
        ks_product_approvals = self.env['product.template'].search(
            [('state', '=', 'draft'), ('active', '=', False), ('is_hidden_for_approval', '=', True)])
        config_users = self.search([]).sorted(key=lambda r: r.sequence)

        for product in ks_product_approvals:
            approval_lines = [(5, 0, 0)]  # Clear existing first
            for config in config_users:
                approval_type = config.approver_type or 'approver1'
                approval_lines.append((0, 0, {
                    'sequence': config.sequence,
                    'user_id': config.user_id.id,
                    'approval_type': approval_type,
                }))
            product.write({'approval_users_ids': approval_lines})
