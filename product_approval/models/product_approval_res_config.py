# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import random

class ProductApprovalConfig(models.Model):
    _name = "product.approval.config"
    _description = "Product Approval Settings"
    _rec_name = 'user_id'
    _order = 'sequence'

    sequence = fields.Integer(string='Sequence', readonly=True)
    user_id = fields.Many2one('res.users', string='Approval User', required=True)
    default_user = fields.Boolean(string="Default")
    group = fields.Selection([
        ('group1', 'Group 1'),
        ('group2', 'Group 2'),
    ], string="Groups", required=True) 
    color = fields.Integer(string="Color Index", readonly=True) 

    _sql_constraints = [
        ('unique_user_id', 'unique(user_id)', 'Each approval user must be unique.')
    ]

    def _validate_unique_user(self, user_id, exclude_ids=None):
        domain = [('user_id', '=', user_id)]
        if exclude_ids:
            domain.append(('id', 'not in', exclude_ids))
        if self.search_count(domain):
            raise ValidationError(_("This user is already added to the approval list."))

    # generate sequence
    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        group_id = defaults.get('group')
        if group_id:
            max_sequence = self.search([('group', '=', group_id)], order="sequence desc", limit=1).sequence
            defaults['sequence'] = (max_sequence or 0) + 1
        else:
            # If no group is present (e.g., from a form view), find the highest global sequence.
            max_sequence = self.search([], order="sequence desc", limit=1).sequence
            defaults['sequence'] = (max_sequence or 0) + 1
        
        return defaults


    @api.constrains('default_user', 'group')
    def _check_unique_default_user_per_group(self):
        for record in self:
            if record.default_user:
                existing_default_users = self.search([
                    ('id', '!=', record.id),
                    ('group', '=', record.group),
                    ('default_user', '=', True)
                ])
                if existing_default_users:
                    # Reset the previous default user to False
                    existing_default_users.write({'default_user': False})


    @api.onchange('default_user', 'group')
    def _onchange_default_user(self):
        if self.default_user:
            existing_default_users = self.search([
                ('id', '!=', self._origin.id if self._origin else False),
                ('group', '=', self.group),
                ('default_user', '=', True)
            ])
            if existing_default_users:
                pass
    

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

            for vals in vals_list:
                self._validate_unique_user(vals.get('user_id'))


        res_list = super(ProductApprovalConfig, self).create(vals_list)
        for res in res_list:
            res._update_draft_product_approvals()
        return res_list


    def write(self, vals):
        for rec in self:
            if 'user_id' in vals:
                rec._validate_unique_user(vals['user_id'], exclude_ids=rec.ids)

        res = super().write(vals)
        self._update_draft_product_approvals()
        return res


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
        self._update_draft_product_approvals()

        return result


    def unlink(self):
        res = super().unlink()
        self._update_draft_product_approvals()
        return res


    def _update_draft_product_approvals(self):
        """Update approval_users_ids on draft product records."""
        product_approvals = self.env['product.template'].search([('state', '=', 'draft'),('active', '=', False),('is_hidden_for_approval', '=', True)])
        config_users = self.search([]).sorted(key=lambda r: r.sequence)

        for product in product_approvals:
            approval_lines = [(5, 0, 0)]  # Clear existing first
            for config in config_users:
                approval_lines.append((0, 0, {
                    'sequence': config.sequence,
                    'user_id': config.user_id.id,
                }))
            product.write({'approval_users_ids': approval_lines})
